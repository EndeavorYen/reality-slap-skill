import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_question_swarm_screening_judging import create_screening_judges
from create_question_swarm_screening_workspace import (
    create_screening_workspace,
    load_records,
)
from question_swarm_common import load_credit_rate_card
from summarize_question_swarm_screening import select_screening_arm


BANK = ROOT / "evals" / "open-decision-case-bank.json"


def final_payload():
    return {
        "recommendation": "Run a bounded pilot.",
        "accepted_claims": ["A reversible test is supported."],
        "rejected_claims": ["An irreversible rollout is unsupported."],
        "residual_dissent": ["The effect size is uncertain."],
        "decision_owner": "Named owner",
        "next_action": "Start the bounded pilot.",
        "stop_conditions": ["Stop if the threshold fails."],
        "rollback_or_revision_path": "Return to the previous state.",
        "change_evidence": ["Measured threshold evidence."],
        "known_facts": ["A supplied case fact."],
        "inferences": ["A bounded step limits downside."],
        "uncertainties": ["Outcome magnitude."],
    }


class QuestionSwarmScreeningTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "screen"
        self.manifest = create_screening_workspace(BANK, self.workspace)
        self.records = load_records(self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, record, payload):
        path = Path(record["output_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def test_workspace_has_exact_models_call_counts_and_question_caps(self):
        self.assertEqual(len(self.records), 32)
        drafts = [record for record in self.records if record["kind"] == "draft"]
        questions = [
            record for record in self.records if record["kind"] == "question"
        ]
        self.assertEqual(len(drafts), 4)
        self.assertEqual(
            {
                condition: sum(
                    record["condition"] == condition for record in questions
                )
                for condition in ("H", "S2", "S4")
            },
            {"H": 4, "S2": 8, "S4": 16},
        )
        for record in questions:
            self.assertEqual(len(record["depends_on"]), 1)
            self.assertFalse(record["uses_skill"])
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertNotIn("Reality Slap", prompt)
            schema = json.loads(
                Path(record["schema_path"]).read_text(encoding="utf-8")
            )
            maximum = schema["properties"]["questions"]["maxItems"]
            self.assertEqual(
                maximum,
                8 if record["condition"] == "H" else 4
                if record["condition"] == "S2"
                else 2,
            )

    def test_judge_packets_hide_models_arms_and_lenses(self):
        for record in self.records:
            if record["kind"] == "draft":
                self._write(record, final_payload())
            else:
                lens = record["role"]
                maximum = json.loads(
                    Path(record["schema_path"]).read_text(encoding="utf-8")
                )["properties"]["questions"]["maxItems"]
                self._write(
                    record,
                    {
                        "lens": lens,
                        "questions": [
                            {
                                "target": f"draft section {index}",
                                "question": f"What could fail in section {index}?",
                            }
                            for index in range(1, maximum + 1)
                        ],
                    },
                )

        judges = create_screening_judges(self.workspace)

        self.assertEqual(len(judges), 4)
        for record in judges:
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertNotIn("gpt-5.6", prompt)
            self.assertNotIn("S2", prompt)
            self.assertNotIn("S4", prompt)
            self.assertNotIn("assumption_and_causality", prompt)
            self.assertEqual(
                set(record["packet_label_to_condition"].values()),
                {"H", "S2", "S4"},
            )

    def test_selection_prefers_cheaper_quality_eligible_arm(self):
        usage_h = {
            "complete": True,
            "input_tokens": 1000,
            "cached_input_tokens": 0,
            "output_tokens": 100,
            "reasoning_output_tokens": 100,
        }
        usage_s2 = {
            "complete": True,
            "input_tokens": 1600,
            "cached_input_tokens": 0,
            "output_tokens": 100,
            "reasoning_output_tokens": 100,
        }
        usage_s4 = {
            "complete": True,
            "input_tokens": 2200,
            "cached_input_tokens": 0,
            "output_tokens": 100,
            "reasoning_output_tokens": 100,
        }
        metrics = {
            "H": {
                "unique_hidden_item_coverage": 10,
                "_fatal": {("case", "FE-1")},
                "usage": usage_h,
            },
            "S2": {
                "unique_hidden_item_coverage": 9,
                "_fatal": {("case", "FE-1")},
                "usage": usage_s2,
            },
            "S4": {
                "unique_hidden_item_coverage": 10,
                "_fatal": {("case", "FE-1")},
                "usage": usage_s4,
            },
        }

        result = select_screening_arm(
            metrics,
            luna_to_terra_price_ratio=0.2,
        )

        self.assertEqual(result["verdict"], "screening-pass")
        self.assertEqual(result["selected_arm"], "S2")

        official = select_screening_arm(
            metrics,
            rate_card=load_credit_rate_card(
                ROOT / "evals" / "openai-codex-rate-card-2026-07-23.json"
            ),
        )
        self.assertEqual(
            official["arms"]["S2"]["challenger_cost_ratio_vs_h"],
            0.55,
        )
        self.assertEqual(
            official["arms"]["S2"]["small_challenger_credits"],
            0.055,
        )


if __name__ == "__main__":
    unittest.main()
