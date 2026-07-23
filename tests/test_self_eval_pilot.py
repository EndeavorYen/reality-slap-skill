import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_question_swarm_confirmation_workspace import load_records
from create_self_eval_pilot_judging import create_judges
from create_self_eval_pilot_workspace import create_workspace
from create_weak_challenge_swarm_judging import CRITICAL_FLAGS, DIMENSIONS
from run_open_decision_debate_experiment import render_prompt
from summarize_self_eval_pilot import summarize


BANK = ROOT / "evals" / "self-eval-pilot-bank-2026-07-23.json"
RATE_CARD = ROOT / "evals" / "openai-codex-rate-card-2026-07-23.json"
SKILL = ROOT / "SKILL.md"


def final_payload(label):
    return {
        "recommendation": f"Run the bounded {label} path.",
        "accepted_claims": ["A reversible pilot is supported."],
        "rejected_claims": ["An unbounded rollout is unsupported."],
        "residual_dissent": ["The effect size remains uncertain."],
        "decision_owner": "Named owner",
        "next_action": "Run the bounded pilot.",
        "stop_conditions": ["Stop if the threshold fails."],
        "rollback_or_revision_path": "Return to the previous state.",
        "change_evidence": ["Measured threshold evidence."],
        "known_facts": ["A supplied case fact."],
        "inferences": ["A bounded pilot limits downside."],
        "uncertainties": ["Outcome magnitude."],
    }


class SelfEvalPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "pilot"
        self.manifest = create_workspace(BANK, SKILL, self.workspace)
        self.records = load_records(self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, record, payload, usage=None):
        output = Path(record["output_path"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        metadata = Path(record["metadata_path"])
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(
            json.dumps(
                {
                    "attempts": [
                        {
                            "usage": usage
                            or {
                                "input_tokens": 100,
                                "cached_input_tokens": 0,
                                "output_tokens": 50,
                                "reasoning_output_tokens": 20,
                            }
                        }
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def _complete_generation(self):
        for record in self.records:
            if record["kind"] == "question":
                self._write(
                    record,
                    {
                        "lens": record["role"],
                        "questions": [
                            {
                                "target": f"target {index}",
                                "question": f"What could fail at target {index}?",
                            }
                            for index in range(1, 5)
                        ],
                    },
                )
            else:
                self._write(
                    record,
                    final_payload(record["condition"]),
                )

    def _complete_judges(self, judges):
        for record in judges:
            evaluations = []
            for label in record["candidate_labels"]:
                checklist = record["checklist_item_ids"]

                def items(field, decision, value):
                    return [
                        {
                            "item_id": item_id,
                            decision: value,
                            "explanation": (
                                "The candidate provides sufficient decision evidence."
                            ),
                        }
                        for item_id in checklist[field]
                    ]

                evaluations.append(
                    {
                        "label": label,
                        "must_cover": items("must_cover", "covered", True),
                        "closure": items("closure", "satisfied", True),
                        "fatal_errors": items(
                            "fatal_errors", "present", False
                        ),
                        "critical_flags": {
                            flag: False for flag in CRITICAL_FLAGS
                        },
                        "critical_explanations": {
                            flag: "No supporting evidence of this defect is present."
                            for flag in CRITICAL_FLAGS
                        },
                        "scores": {
                            dimension: 2 for dimension in DIMENSIONS
                        },
                        "total_score": 14,
                        "summary": (
                            "The candidate is bounded, actionable, and calibrated."
                        ),
                    }
                )
            self._write(
                record,
                {
                    "case_id": record["case_id"],
                    "evaluations": evaluations,
                    "pairwise_preferences": [
                        {
                            "left_label": "A",
                            "right_label": "B",
                            "winner": "tie",
                            "rationale": (
                                "Both candidates provide equivalent decision evidence."
                            ),
                        }
                    ],
                    "ranking": ["A", "B"],
                },
            )

    def test_fresh_call_graph_and_skill_boundary(self):
        self.assertEqual(self.manifest["planned_generation_calls"], 24)
        self.assertEqual(len(self.records), 24)
        self.assertEqual(
            sum(record["kind"] == "final" for record in self.records),
            16,
        )
        self.assertEqual(
            sum(record["kind"] == "question" for record in self.records),
            8,
        )
        for record in self.records:
            self.assertEqual(
                record["uses_skill"],
                record["kind"] == "final",
            )
        d_final = next(
            record
            for record in self.records
            if record["case_id"] == "SE-01"
            and record["condition"] == "D"
            and record["kind"] == "final"
        )
        self.assertEqual(len(d_final["depends_on"]), 2)
        self.assertEqual(d_final["reasoning_effort"], "medium")

    def test_prompts_isolate_simple_structured_and_premortem_variants(self):
        prompts = {}
        for condition in ("A", "B", "C", "D"):
            record = next(
                record
                for record in self.records
                if record["case_id"] == "SE-01"
                and record["condition"] == condition
                and record["kind"] == "final"
            )
            prompts[condition] = Path(record["prompt_path"]).read_text(
                encoding="utf-8"
            )
        self.assertNotIn("請自評", prompts["A"])
        self.assertIn("請自評", prompts["B"])
        self.assertNotIn("single most likely omitted", prompts["B"])
        self.assertIn("single most likely omitted", prompts["C"])
        self.assertIn("__CHALLENGE_PACKET_JSON__", prompts["D"])
        for record in self.records:
            if record["kind"] == "question":
                prompt = Path(record["prompt_path"]).read_text(
                    encoding="utf-8"
                )
                self.assertNotIn("FROZEN_REALITY_SLAP", prompt)
                self.assertNotIn("Frozen shared draft", prompt)

    def test_rendered_d_packet_contains_eight_anonymous_questions(self):
        self._complete_generation()
        records_by_id = {
            record["call_id"]: record for record in self.records
        }
        record = next(
            record
            for record in self.records
            if record["case_id"] == "SE-01"
            and record["condition"] == "D"
            and record["kind"] == "final"
        )

        prompt = render_prompt(record, records_by_id, self.manifest)

        self.assertNotIn("__CHALLENGE_PACKET_JSON__", prompt)
        self.assertIn('"question_id": "Q-1"', prompt)
        self.assertIn('"question_id": "Q-8"', prompt)
        self.assertNotIn('"question_id": "Q-9"', prompt)
        self.assertNotIn("gpt-5.6-luna", prompt)

    def test_pair_judges_and_fixture_summary(self):
        self._complete_generation()
        judges = create_judges(self.workspace)
        self.assertEqual(len(judges), 32)
        comparisons = {
            record["comparison"] for record in judges
        }
        self.assertEqual(
            comparisons,
            {"A-vs-B", "A-vs-C", "B-vs-C", "C-vs-D"},
        )
        for record in judges:
            self.assertEqual(
                set(record["label_to_condition"].values()),
                set(record["pair_conditions"]),
            )
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertNotIn("gpt-5.6", prompt)
            self.assertNotIn("self-eval", prompt.casefold())
        self._complete_judges(judges)

        report = summarize(self.workspace, RATE_CARD)

        self.assertEqual(report["quality"]["agreement"], 1.0)
        self.assertEqual(
            report["gate"]["self_eval_verdict"],
            "no-self-eval-signal",
        )
        self.assertEqual(report["process_leaks"]["A"]["count"], 0)
        self.assertGreater(
            report["cost"]["end_to_end_credits"]["D"],
            report["cost"]["end_to_end_credits"]["A"],
        )


if __name__ == "__main__":
    unittest.main()
