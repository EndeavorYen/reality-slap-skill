import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from open_decision_case_bank import load_case_bank, select_cases, validate_case_bank


BANK = ROOT / "evals" / "open-decision-case-bank.json"


class OpenDecisionCaseBankTests(unittest.TestCase):
    def test_bank_freezes_twenty_four_balanced_cases(self):
        payload = load_case_bank(BANK)
        audit = validate_case_bank(payload)

        self.assertEqual(audit["case_count"], 24)
        self.assertEqual(len(audit["primary_ids"]), 12)
        self.assertEqual(len(audit["reserve_ids"]), 12)
        self.assertEqual(set(audit["primary_ids"]) & set(audit["reserve_ids"]), set())
        self.assertEqual(
            set(audit["domain_split_counts"].values()),
            {(("primary", 2), ("reserve", 2))},
        )

    def test_select_cases_returns_frozen_subset_in_id_order(self):
        payload = load_case_bank(BANK)

        primary = select_cases(payload, "primary")
        reserve = select_cases(payload, "reserve")

        self.assertEqual([case["case_id"] for case in primary], [f"OD-{n:02d}" for n in range(1, 13)])
        self.assertEqual([case["case_id"] for case in reserve], [f"OD-{n:02d}" for n in range(13, 25)])

    def test_case_requires_open_decision_and_hidden_card_fields(self):
        payload = load_case_bank(BANK)
        broken = copy.deepcopy(payload)
        del broken["cases"][0]["adjudication"]["fatal_errors"]

        with self.assertRaisesRegex(ValueError, "fatal_errors"):
            validate_case_bank(broken)

    def test_case_rejects_too_few_paths_constraints_failures_and_decision_families(self):
        payload = load_case_bank(BANK)
        mutations = (
            ("plausible_paths", ["one", "two"]),
            ("material_constraints", ["one", "two", "three"]),
            ("harmful_failure_paths", ["one"]),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                broken = copy.deepcopy(payload)
                broken["cases"][0]["public"][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    validate_case_bank(broken)

        broken = copy.deepcopy(payload)
        broken["cases"][0]["adjudication"]["acceptable_decision_families"] = ["one"]
        with self.assertRaisesRegex(ValueError, "acceptable_decision_families"):
            validate_case_bank(broken)

    def test_case_ids_and_split_assignments_are_immutable(self):
        payload = load_case_bank(BANK)
        duplicate = copy.deepcopy(payload)
        duplicate["cases"][1]["case_id"] = duplicate["cases"][0]["case_id"]
        with self.assertRaisesRegex(ValueError, "duplicate case_id"):
            validate_case_bank(duplicate)

        wrong_split = copy.deepcopy(payload)
        wrong_split["cases"][0]["subset"] = "reserve"
        with self.assertRaisesRegex(ValueError, "primary IDs"):
            validate_case_bank(wrong_split)

    def test_private_adjudication_text_cannot_be_copied_into_public_prompt(self):
        payload = load_case_bank(BANK)
        broken = copy.deepcopy(payload)
        leaked = broken["cases"][0]["adjudication"]["fatal_errors"][0]
        broken["cases"][0]["public"]["decision_request"] += f" Hidden answer: {leaked}"

        with self.assertRaisesRegex(ValueError, "leaks adjudication"):
            validate_case_bank(broken)

    def test_serialized_bank_is_valid_json(self):
        parsed = json.loads(BANK.read_text(encoding="utf-8"))
        self.assertEqual(parsed["experiment_id"], "open-decision-debate-20260724")


if __name__ == "__main__":
    unittest.main()
