import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from question_swarm_common import (
    LENSES,
    break_even_multiplier,
    credit_cost,
    load_credit_rate_card,
    load_holdout_bank,
    question_schema,
    usage_totals,
)


BANK = ROOT / "evals" / "question-swarm-holdout-bank.json"


class QuestionSwarmCommonTests(unittest.TestCase):
    def test_holdout_has_eight_balanced_valid_cases(self):
        cases = load_holdout_bank(BANK)

        self.assertEqual(
            [case["case_id"] for case in cases],
            [f"QS-{number:02d}" for number in range(1, 9)],
        )
        counts = {}
        for case in cases:
            counts[case["domain"]] = counts.get(case["domain"], 0) + 1
        self.assertEqual(
            counts,
            {
                "operations-incidents": 2,
                "organization-process": 2,
                "platform-architecture": 2,
                "product-launch": 2,
            },
        )

    def test_question_schema_keeps_small_models_to_questions_only(self):
        schema = question_schema((LENSES[0],), max_questions=2)
        properties = schema["properties"]
        item_properties = properties["questions"]["items"]["properties"]

        self.assertEqual(set(properties), {"lens", "questions"})
        self.assertEqual(set(item_properties), {"target", "question"})
        self.assertEqual(properties["questions"]["maxItems"], 2)

    def test_usage_totals_count_retries_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            metadata = Path(temp_dir) / "call.json"
            metadata.write_text(
                json.dumps(
                    {
                        "attempts": [
                            {
                                "usage": {
                                    "input_tokens": 10,
                                    "cached_input_tokens": 2,
                                    "output_tokens": 3,
                                    "reasoning_output_tokens": 1,
                                }
                            },
                            {
                                "usage": {
                                    "input_tokens": 12,
                                    "cached_input_tokens": 4,
                                    "output_tokens": 5,
                                    "reasoning_output_tokens": 2,
                                }
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            totals = usage_totals([{"metadata_path": str(metadata)}])
            self.assertTrue(totals["complete"])
            self.assertEqual(totals["input_tokens"], 22)
            self.assertEqual(totals["output_tokens"], 8)
            self.assertEqual(totals["reasoning_output_tokens"], 3)

            metadata.write_text(
                json.dumps({"attempts": [{"usage": None}]}),
                encoding="utf-8",
            )
            self.assertFalse(
                usage_totals([{"metadata_path": str(metadata)}])["complete"]
            )

    def test_break_even_multiplier_uses_uncached_input_and_output(self):
        small = {
            "complete": True,
            "input_tokens": 200,
            "cached_input_tokens": 50,
            "output_tokens": 40,
            "reasoning_output_tokens": 10,
        }
        high = {
            "complete": True,
            "input_tokens": 100,
            "cached_input_tokens": 0,
            "output_tokens": 20,
            "reasoning_output_tokens": 5,
        }

        result = break_even_multiplier(small, high, target_ratio=0.7)

        self.assertEqual(result["small_reference_units"], 240)
        self.assertEqual(result["high_reference_units"], 120)
        self.assertEqual(result["max_small_to_high_unit_price_ratio"], 0.35)

    def test_official_credit_cost_does_not_double_count_reasoning(self):
        usage = {
            "complete": True,
            "input_tokens": 200,
            "cached_input_tokens": 50,
            "output_tokens": 40,
            "reasoning_output_tokens": 10,
        }
        rates = {
            "input_tokens": 25,
            "cached_input_tokens": 2.5,
            "output_tokens": 150,
        }

        self.assertEqual(credit_cost(usage, rates), 0.009875)
        card = load_credit_rate_card(
            ROOT / "evals" / "openai-codex-rate-card-2026-07-23.json"
        )
        self.assertEqual(card["models"]["gpt-5.6-luna"], rates)


if __name__ == "__main__":
    unittest.main()
