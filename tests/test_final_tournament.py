import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_final_tournament_judging import PAIRS, create_judges
from create_final_tournament_workspace import create_workspace
from create_question_swarm_confirmation_workspace import load_records
from create_weak_challenge_swarm_judging import CRITICAL_FLAGS, DIMENSIONS
from run_open_decision_debate_experiment import render_prompt
from summarize_final_tournament import summarize


BANK = ROOT / "evals" / "final-tournament-bank-2026-07-23.json"
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


class FinalTournamentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "tournament"
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
                maximum = 4 if record["condition"] == "L2" else 8
                self._write(
                    record,
                    {
                        "lens": record["role"],
                        "questions": [
                            {
                                "target": f"target {index}",
                                "question": f"What fails at target {index}?",
                            }
                            for index in range(1, maximum + 1)
                        ],
                    },
                )
            elif record["kind"] == "revision":
                self._write(
                    record,
                    {
                        "challenge_dispositions": [],
                        "final_decision": final_payload(record["condition"]),
                    },
                )
            else:
                self._write(record, final_payload(record["condition"]))

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
                                "The decision supplies sufficient case evidence."
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
                            flag: "No evidence of this critical defect is present."
                            for flag in CRITICAL_FLAGS
                        },
                        "scores": {
                            dimension: 2 for dimension in DIMENSIONS
                        },
                        "total_score": 14,
                        "summary": (
                            "The decision is bounded, actionable, and calibrated."
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
                                "Both decisions contain equivalent controls."
                            ),
                        }
                    ],
                    "ranking": ["A", "B"],
                },
            )

    def test_generation_graph_and_skill_boundary(self):
        self.assertEqual(self.manifest["planned_generation_calls"], 84)
        self.assertEqual(self.manifest["planned_judge_calls"], 72)
        self.assertEqual(len(self.records), 84)
        self.assertEqual(
            sum(record["kind"] == "draft" for record in self.records), 12
        )
        self.assertEqual(
            sum(record["kind"] == "question" for record in self.records), 36
        )
        self.assertEqual(
            sum(record["kind"] in {"final", "revision"} for record in self.records),
            36,
        )
        for record in self.records:
            expected = (
                record["condition"] in {"DX", "L2", "T1"}
                and record["kind"] in {"final", "revision"}
            )
            self.assertEqual(record["uses_skill"], expected)

    def test_models_efforts_and_isolated_question_prompts(self):
        dx = next(
            record for record in self.records if record["condition"] == "DX"
        )
        self.assertEqual(dx["model"], "gpt-5.6-sol")
        self.assertEqual(dx["reasoning_effort"], "xhigh")
        for record in self.records:
            if record["kind"] != "question":
                continue
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertNotIn("FROZEN_REALITY_SLAP", prompt)
            self.assertIn("__SHARED_DRAFT_JSON__", prompt)
            if record["condition"] == "L2":
                self.assertEqual(record["model"], "gpt-5.6-luna")
                self.assertEqual(record["reasoning_effort"], "low")
            else:
                self.assertEqual(record["model"], "gpt-5.6-terra")
                self.assertEqual(record["reasoning_effort"], "high")

    def test_rendered_revision_has_shared_draft_and_questions(self):
        self._complete_generation()
        records_by_id = {record["call_id"]: record for record in self.records}
        record = next(
            item
            for item in self.records
            if item["case_id"] == "FT-01"
            and item["condition"] == "L2"
            and item["kind"] == "revision"
        )
        prompt = render_prompt(record, records_by_id, self.manifest)
        self.assertNotIn("__SHARED_DRAFT_JSON__", prompt)
        self.assertNotIn("__CHALLENGE_PACKET_JSON__", prompt)
        self.assertIn('"question_id": "Q-8"', prompt)
        self.assertNotIn("gpt-5.6-luna", prompt)

    def test_pair_judges_freeze_candidates_and_summary(self):
        self._complete_generation()
        judges = create_judges(self.workspace)
        self.assertEqual(len(judges), 72)
        self.assertEqual(
            {record["comparison"] for record in judges},
            {f"{left}-vs-{right}" for left, right in PAIRS},
        )
        for record in judges:
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertNotIn("gpt-5.6", prompt)
            self.assertNotIn("Reality Slap", prompt)
        self._complete_judges(judges)
        report = summarize(self.workspace, RATE_CARD)
        self.assertEqual(report["quality"]["agreement"], 1.0)
        self.assertTrue(report["quality"]["opponent_stability_passed"])
        self.assertEqual(report["selection"]["champion"], "DX")
        self.assertTrue(
            all(
                item["decision_differences"] == 0
                for item in report["opponent_context_drift"].values()
            )
        )
        self.assertIsNotNone(report["cost"]["judge_cost"])
        self.assertGreater(report["cost"]["judge_cost"]["total_credits"], 0)
        self.assertGreater(
            report["cost"]["end_to_end_credits"]["L2"],
            report["cost"]["end_to_end_credits"]["DX"],
        )


if __name__ == "__main__":
    unittest.main()
