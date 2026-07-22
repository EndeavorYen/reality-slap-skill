import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_isolated_roleplay_judging import create_judge_records
from create_isolated_roleplay_workspace import ROLES, create_workspace, load_records
from run_isolated_roleplay_experiment import validate_record_payload


BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
SKILL = ROOT / "SKILL.md"


def role_payload(role=None, action="bounded path"):
    payload = {
        "recommended_action": action,
        "stance_class": "bounded_alternative",
        "supporting_evidence": ["evidence"],
        "non_negotiable_boundaries": ["boundary"],
        "change_conditions": ["change condition"],
        "confidence": 80,
    }
    return {"role": role, **payload} if role else payload


def chair_payload():
    return {
        "final_recommendation": "Use the bounded path.",
        "final_stance_class": "bounded_alternative",
        "accepted_boundaries": ["boundary"],
        "preserved_dissent": ["minority objection"],
        "rejected_arguments": ["unsafe extreme"],
        "change_conditions": ["new evidence"],
        "confidence": 85,
    }


def meeting_payload():
    return {
        "roles": [role_payload(role) for role in ROLES],
        "second_round": [
            {
                "role": role,
                "response_to_others": "reviewed peers",
                "revised_recommended_action": "bounded path",
                "revised_stance_class": "bounded_alternative",
                "remaining_dissent": "minor concern remains",
            }
            for role in ROLES
        ],
        "chair": chair_payload(),
    }


class CreateIsolatedRoleplayJudgingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        create_workspace(
            bank_path=BANK,
            skill_path=SKILL,
            output_dir=self.workspace,
            seed=20260723,
            model="gpt-5.6-sol",
            reasoning_effort="medium",
            scenario_ids=["SD-01"],
        )
        self.records = load_records(self.workspace)
        self.complete_generation()

    def tearDown(self):
        self.temp_dir.cleanup()

    def complete_generation(self):
        for record in self.records:
            if record["kind"] == "meeting":
                payload = meeting_payload()
            elif record["kind"] == "role":
                payload = role_payload(action=f"{record['role']} bounded path")
            else:
                payload = chair_payload()
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def mappings(self):
        payload = json.loads((self.workspace / "judge-mappings.json").read_text(encoding="utf-8"))
        return payload["mappings"]

    def test_two_passes_create_two_requests_for_one_case_with_distinct_mappings(self):
        records = create_judge_records(self.workspace, passes=2)

        self.assertEqual(len(records), 2)
        self.assertEqual({record["pass_number"] for record in records}, {1, 2})
        mappings = self.mappings()
        self.assertNotEqual(mappings[0]["label_to_condition"], mappings[1]["label_to_condition"])

    def test_judge_prompt_hides_condition_skill_and_context_identity(self):
        records = create_judge_records(self.workspace, passes=2)

        for record in records:
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            for forbidden in (
                "shared-control",
                "shared-skill",
                "isolated-control",
                "isolated-skill",
                "Reality Slap",
                "second_round",
                "uses_skill",
                "context_mode",
            ):
                self.assertNotIn(forbidden, prompt)

    def test_judge_packet_normalizes_all_conditions_to_roles_and_chair(self):
        [record] = create_judge_records(self.workspace, passes=1)
        prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")

        self.assertEqual(prompt.count('"sealed_roles"'), 4)
        self.assertEqual(prompt.count('"chair_decision"'), 4)
        self.assertEqual(prompt.count('"label"'), 4)

    def test_missing_generation_output_prevents_packet_creation(self):
        missing = next(record for record in self.records if record["kind"] == "chair")
        Path(missing["output_path"]).unlink()

        with self.assertRaisesRegex(ValueError, "generation workspace is incomplete"):
            create_judge_records(self.workspace, passes=2)

        self.assertFalse((self.workspace / "judge-records.jsonl").exists())

    def test_public_judge_records_do_not_expose_mapping(self):
        [record] = create_judge_records(self.workspace, passes=1)

        self.assertNotIn("condition_mapping", record)
        self.assertNotIn("mapping_path", record)
        prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
        self.assertNotIn("label_to_condition", prompt)

    def test_judge_schema_is_strict_and_requires_four_evaluations(self):
        create_judge_records(self.workspace, passes=1)
        schema = json.loads((self.workspace / "schemas" / "judge.json").read_text(encoding="utf-8"))
        evaluations = schema["properties"]["evaluations"]

        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(evaluations["minItems"], 4)
        self.assertEqual(evaluations["maxItems"], 4)
        self.assertEqual(
            evaluations["items"]["properties"]["quality_score"]["maximum"],
            14,
        )

    def test_judge_validation_rejects_duplicate_opaque_labels(self):
        [record] = create_judge_records(self.workspace, passes=1)
        evaluation = {
            "label": "A",
            "normalized_role_stances": [
                {"role": role, "stance_class": "bounded_alternative"}
                for role in ROLES
            ],
            "substantive_dissent": False,
            "gold_final_stance_correct": True,
            "complete_critical_boundaries": 2,
            "quality_score": 13,
            "dissent_preserved": True,
            "false_unanimity": False,
            "harmful_compromise": False,
            "critical_failure_mode": "none",
            "notes": "Complete bounded decision.",
        }
        payload = {
            "scenario_id": "SD-01",
            "evaluations": [
                evaluation,
                evaluation,
                {**evaluation, "label": "C"},
                {**evaluation, "label": "D"},
            ],
        }

        with self.assertRaisesRegex(ValueError, "each opaque label exactly once"):
            validate_record_payload(record, payload)


if __name__ == "__main__":
    unittest.main()
