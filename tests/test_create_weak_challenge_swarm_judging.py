import itertools
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_weak_challenge_swarm_judging import (
    CONDITIONS,
    CRITICAL_FLAGS,
    DIMENSIONS,
    create_judge_records,
    validate_judge_payload,
)
from create_weak_challenge_swarm_workspace import ROLES, create_workspace, load_records
from run_open_decision_debate_experiment import expected_challenge_ids, response_status


BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"


def final_payload(label):
    return {
        "recommendation": f"Choose {label}.",
        "accepted_claims": ["A supplied fact supports a bounded step."],
        "rejected_claims": ["An unsupported claim is rejected."],
        "residual_dissent": ["Material uncertainty remains."],
        "decision_owner": "Named owner",
        "next_action": "Run the bounded step.",
        "stop_conditions": ["Stop if the threshold fails."],
        "rollback_or_revision_path": "Return to the prior state.",
        "change_evidence": ["New measured evidence."],
        "known_facts": ["A supplied fact."],
        "inferences": ["A bounded inference."],
        "uncertainties": ["Outcome size."],
    }


def challenge_payload(role):
    return {
        "role": role,
        "challenges": [
            {
                "question_or_challenge": f"{role} question",
                "why_material": "It may alter the safe choice.",
                "case_fact_refs": ["facts[0]"],
                "failure_if_ignored": "A constraint may be missed.",
                "disconfirming_evidence": "Evidence that the constraint is met.",
                "severity": "high",
            }
        ],
        "coverage_limitations": ["No external evidence."],
    }


def judge_payload(record):
    evaluations = []
    for label in record["candidate_labels"]:
        must_cover = [
            {
                "item_id": item_id,
                "covered": True,
                "explanation": "The decision explicitly covers this requirement.",
            }
            for item_id in record["checklist_item_ids"]["must_cover"]
        ]
        closure = [
            {
                "item_id": item_id,
                "satisfied": True,
                "explanation": "The decision explicitly closes this requirement.",
            }
            for item_id in record["checklist_item_ids"]["closure"]
        ]
        fatal = [
            {
                "item_id": item_id,
                "present": False,
                "explanation": "The fatal condition is not present in the decision.",
            }
            for item_id in record["checklist_item_ids"]["fatal_errors"]
        ]
        scores = {dimension: 2 for dimension in DIMENSIONS}
        evaluations.append(
            {
                "label": label,
                "must_cover": must_cover,
                "closure": closure,
                "fatal_errors": fatal,
                "critical_flags": {flag: False for flag in CRITICAL_FLAGS},
                "critical_explanations": {
                    flag: "No critical issue." for flag in CRITICAL_FLAGS
                },
                "scores": scores,
                "total_score": 14,
                "summary": "Complete bounded decision.",
            }
        )
    pairs = [
        {
            "left_label": left,
            "right_label": right,
            "winner": "tie",
            "rationale": "Both satisfy the checklist.",
        }
        for left, right in itertools.combinations(record["candidate_labels"], 2)
    ]
    return {
        "case_id": record["case_id"],
        "evaluations": evaluations,
        "pairwise_preferences": pairs,
        "ranking": list(record["candidate_labels"]),
    }


class CreateWeakChallengeSwarmJudgingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        create_workspace(BANK, SKILL, self.workspace, seed=20260725)
        self.records = load_records(self.workspace)
        self.records_by_id = {record["call_id"]: record for record in self.records}
        self.manifest = json.loads(
            (self.workspace / "manifest.json").read_text(encoding="utf-8")
        )
        self.complete_generation()

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, record, payload):
        path = Path(record["output_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def complete_generation(self):
        for case_id in self.manifest["case_ids"]:
            case_records = [r for r in self.records if r["case_id"] == case_id]
            draft = next(r for r in case_records if r["condition"] == "A")
            self.write(draft, final_payload("A"))
            for role in ROLES:
                record = next(
                    r
                    for r in case_records
                    if r["kind"] == "challenge" and r["role"] == role
                )
                self.write(record, challenge_payload(role))
            for condition in ("B0", "B1", "C0", "C1"):
                record = next(r for r in case_records if r["condition"] == condition)
                ids = expected_challenge_ids(
                    record,
                    self.records_by_id,
                    self.manifest,
                )
                self.write(
                    record,
                    {
                        "challenge_dispositions": [
                            {
                                "challenge_id": item_id,
                                "disposition": "accepted",
                                "case_grounded_reason": "Material supplied constraint.",
                                "resulting_change": "Added a safeguard.",
                            }
                            for item_id in ids
                        ],
                        "final_decision": final_payload(condition),
                    },
                )

    def test_two_judges_per_case_use_distinct_five_way_mappings(self):
        records = create_judge_records(self.workspace)
        od13 = [record for record in records if record["case_id"] == "OD-13"]

        self.assertEqual(len(records), 24)
        self.assertEqual(len(od13), 2)
        self.assertNotEqual(
            od13[0]["label_to_condition"],
            od13[1]["label_to_condition"],
        )
        self.assertEqual(
            set(od13[0]["label_to_condition"].values()),
            set(CONDITIONS),
        )
        self.assertEqual(
            {(record["model"], record["reasoning_effort"]) for record in od13},
            {("gpt-5.6-sol", "medium"), ("gpt-5.6-terra", "high")},
        )

    def test_judge_prompt_contains_finals_and_hidden_card_only(self):
        record = create_judge_records(self.workspace)[0]
        prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")

        for forbidden in (
            "challenge_dispositions",
            "boundary_scout",
            "gpt-5.6",
            "Reality Slap",
            '"B0"',
            '"B1"',
            '"C0"',
            '"C1"',
        ):
            self.assertNotIn(forbidden, prompt)
        self.assertIn("must_cover", prompt)
        self.assertIn("fatal_errors", prompt)
        self.assertEqual(prompt.count('"final_decision"'), 5)

    def test_schema_and_semantics_require_exact_checklist_and_ten_pairs(self):
        record = create_judge_records(self.workspace)[0]
        payload = judge_payload(record)

        validate_judge_payload(record, payload)
        self.write(record, payload)
        self.assertEqual(response_status(record), "complete")

        payload["evaluations"][0]["must_cover"].pop()
        with self.assertRaisesRegex(ValueError, "must_cover"):
            validate_judge_payload(record, payload)
        self.write(record, payload)
        self.assertEqual(response_status(record), "invalid")

    def test_only_final_decision_is_extracted_from_revision(self):
        records = create_judge_records(self.workspace)
        record = next(item for item in records if item["case_id"] == "OD-13")
        prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Choose C1.", prompt)
        self.assertNotIn("Added a safeguard.", prompt)

    def test_incomplete_generation_fails_closed_before_judge_files(self):
        challenge = next(r for r in self.records if r["kind"] == "challenge")
        Path(challenge["output_path"]).unlink()

        with self.assertRaisesRegex(ValueError, "generation workspace is incomplete"):
            create_judge_records(self.workspace)


if __name__ == "__main__":
    unittest.main()
