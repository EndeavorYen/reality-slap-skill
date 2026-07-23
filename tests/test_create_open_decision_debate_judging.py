import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_open_decision_debate_judging import (
    CRITICAL_FLAGS,
    DIMENSIONS,
    create_conflict_queue,
    create_judge_records,
    load_human_resolutions,
)
from create_open_decision_debate_workspace import (
    ROLES,
    create_workspace,
    load_records,
)
from run_open_decision_debate_experiment import response_status


BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"


def final_payload(_name):
    return {
        "recommendation": "Choose the bounded pilot.",
        "accepted_claims": ["Supported claim."],
        "rejected_claims": ["Unsupported claim."],
        "residual_dissent": ["Residual uncertainty remains."],
        "decision_owner": "Named owner",
        "next_action": "Run a bounded pilot.",
        "stop_conditions": ["Stop if the threshold fails."],
        "rollback_or_revision_path": "Return to the prior state.",
        "change_evidence": ["Material new evidence."],
        "known_facts": ["A supplied fact."],
        "inferences": ["A bounded inference."],
        "uncertainties": ["Outcome size is unknown."],
    }


def first_payload(role):
    return {
        "role": role,
        "recommendation": "Run a bounded pilot.",
        "claims": [
            {"claim": "Pilot first.", "evidence_refs": ["fact-1"], "confidence": 80},
            {"claim": "Rollback.", "evidence_refs": ["fact-2"], "confidence": 75},
        ],
        "constraints": ["constraint"],
        "failure_modes": ["failure"],
        "uncertainties": ["uncertainty"],
        "falsifiers": ["threshold miss"],
        "reversible_test": "pilot",
    }


def cross_payload(role):
    return {
        "role": role,
        "strongest_peer_point_accepted": "valid point",
        "strongest_unresolved_objection": "remaining objection",
        "unsupported_peer_claims": ["unsupported"],
        "update_type": "revised",
        "updated_recommendation": "smaller pilot",
        "update_reason": "peer evidence",
        "remaining_uncertainty": ["magnitude"],
    }


def serial_payload(phase):
    return {
        "phase": phase,
        "recommendation": "bounded pilot",
        "supported_claims": ["supported"],
        "criticisms_or_changes": ["change"],
        "constraints": ["constraint"],
        "uncertainties": ["uncertainty"],
        "next_decision": "decide pilot scope",
    }


def judge_payload(record, score_by_condition=None, winner_condition="heterogeneous-debate-rs-chair"):
    score_by_condition = score_by_condition or {
        "direct-sol": 14,
        "matched-serial-review": 15,
        "heterogeneous-debate-rs-chair": 18,
    }
    mapping = record["label_to_condition"]
    evaluations = []
    for label, condition in mapping.items():
        remaining = score_by_condition[condition]
        scores = {}
        for dimension in DIMENSIONS:
            value = min(3, remaining)
            scores[dimension] = value
            remaining -= value
        evaluations.append(
            {
                "label": label,
                "scores": scores,
                "total_score": score_by_condition[condition],
                "critical_flags": {flag: False for flag in CRITICAL_FLAGS},
                "critical_explanations": {flag: "No issue found." for flag in CRITICAL_FLAGS},
                "valid_novel_insights": ["A supported insight."],
                "summary": f"Assessment of {label}.",
            }
        )
    labels = list(mapping)
    pairs = []
    for left_index in range(len(labels)):
        for right_index in range(left_index + 1, len(labels)):
            left = labels[left_index]
            right = labels[right_index]
            left_condition = mapping[left]
            right_condition = mapping[right]
            if winner_condition in {left_condition, right_condition}:
                winner = left if left_condition == winner_condition else right
            else:
                winner = left if score_by_condition[left_condition] >= score_by_condition[right_condition] else right
            pairs.append(
                {
                    "left_label": left,
                    "right_label": right,
                    "winner": winner,
                    "rationale": "The winner is more complete and actionable.",
                }
            )
    ranking = sorted(labels, key=lambda label: score_by_condition[mapping[label]], reverse=True)
    return {
        "case_id": record["case_id"],
        "evaluations": evaluations,
        "pairwise_preferences": pairs,
        "ranking": ranking,
    }


class CreateOpenDecisionDebateJudgingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        create_workspace(BANK, SKILL, self.workspace, "primary", 20260724)
        self.complete_generation()

    def tearDown(self):
        self.temp_dir.cleanup()

    def complete_generation(self):
        for record in load_records(self.workspace):
            if record["kind"] in {"direct", "chair"} or (
                record["kind"] == "serial" and record["phase"] == "final"
            ):
                payload = final_payload(record["condition"])
            elif record["kind"] == "role":
                payload = first_payload(record["role"])
            elif record["kind"] == "cross_exam":
                payload = cross_payload(record["role"])
            else:
                payload = serial_payload(record["phase"])
            path = Path(record["output_path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def create(self):
        return create_judge_records(self.workspace, "stage1")

    def write_judges(self, winner_by_judge=None, score_shift=0):
        winner_by_judge = winner_by_judge or {
            "sol-medium": "heterogeneous-debate-rs-chair",
            "terra-high": "heterogeneous-debate-rs-chair",
        }
        records = self.create()
        for record in records:
            scores = {
                "direct-sol": 14,
                "matched-serial-review": 15,
                "heterogeneous-debate-rs-chair": 18,
            }
            if record["judge_id"] == "terra-high":
                scores["heterogeneous-debate-rs-chair"] += score_shift
            payload = judge_payload(
                record,
                score_by_condition=scores,
                winner_condition=winner_by_judge[record["judge_id"]],
            )
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return records

    def test_stage_one_creates_two_different_blind_mappings_per_case(self):
        records = self.create()
        od1 = [record for record in records if record["case_id"] == "OD-01"]

        self.assertEqual(len(records), 24)
        self.assertEqual({record["model"] for record in records}, {
            "gpt-5.6-sol",
            "gpt-5.6-terra",
        })
        self.assertEqual({record["reasoning_effort"] for record in records}, {"medium", "high"})
        self.assertNotEqual(od1[0]["label_to_condition"], od1[1]["label_to_condition"])

    def test_judge_prompt_contains_only_final_candidates(self):
        record = self.create()[0]
        prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")

        self.assertNotIn("first_round", prompt)
        self.assertNotIn("cross_exam", prompt)
        self.assertNotIn("gpt-5.6", prompt)
        self.assertNotIn("reasoning_effort", prompt)
        self.assertIn("must_cover_constraints", prompt)
        for condition in (
            "direct-sol",
            "matched-serial-review",
            "heterogeneous-debate-rs-chair",
        ):
            self.assertNotIn(condition, prompt)

    def test_equal_judgments_produce_no_conflict_queue(self):
        self.write_judges()

        queue = create_conflict_queue(self.workspace)

        self.assertEqual(queue["conflict_count"], 0)
        self.assertEqual(queue["conflicts"], [])

    def test_pairwise_disagreement_creates_blinded_human_conflict(self):
        self.write_judges(
            winner_by_judge={
                "sol-medium": "heterogeneous-debate-rs-chair",
                "terra-high": "matched-serial-review",
            }
        )

        queue = create_conflict_queue(self.workspace)

        self.assertGreater(queue["conflict_count"], 0)
        conflict = next(item for item in queue["conflicts"] if item["case_id"] == "OD-01")
        serialized = json.dumps(conflict)
        self.assertIn("judge_rationales", conflict)
        self.assertNotIn("heterogeneous-debate-rs-chair", serialized)
        self.assertNotIn("matched-serial-review", serialized)
        self.assertNotIn("gpt-5.6", serialized)

    def test_score_difference_above_three_creates_conflict(self):
        self.write_judges(score_shift=-4)

        queue = create_conflict_queue(self.workspace)

        self.assertTrue(any("score-gap" in item["reasons"] for item in queue["conflicts"]))

    def test_missing_required_human_resolution_is_rejected(self):
        self.write_judges(
            winner_by_judge={
                "sol-medium": "heterogeneous-debate-rs-chair",
                "terra-high": "matched-serial-review",
            }
        )
        queue = create_conflict_queue(self.workspace)

        with self.assertRaisesRegex(ValueError, "missing human adjudications"):
            load_human_resolutions(self.workspace, {
                item["conflict_id"] for item in queue["conflicts"]
            })

    def test_semantically_invalid_judge_total_is_not_complete(self):
        records = self.write_judges()
        record = records[0]
        output_path = Path(record["output_path"])
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        payload["evaluations"][0]["total_score"] -= 1
        output_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

        self.assertEqual(response_status(record), "invalid")


if __name__ == "__main__":
    unittest.main()
