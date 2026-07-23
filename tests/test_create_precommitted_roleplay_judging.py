import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_isolated_roleplay_workspace import ROLES, create_workspace as create_baseline, load_records
from create_precommitted_roleplay_judging import ALL_CONDITIONS, create_judge_records
from create_precommitted_roleplay_workspace import create_workspace as create_extension
from run_isolated_roleplay_experiment import validate_record_payload


BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
SKILL = ROOT / "SKILL.md"


def role_payload(role=None, stance="bounded_alternative"):
    payload = {
        "recommended_action": f"Argue the {stance} hypothesis.",
        "stance_class": stance,
        "supporting_evidence": ["evidence"],
        "non_negotiable_boundaries": ["boundary"],
        "change_conditions": ["new evidence"],
        "confidence": 80,
    }
    return {"role": role, **payload} if role else payload


def chair_payload():
    return {
        "final_recommendation": "Use the bounded path.",
        "final_stance_class": "bounded_alternative",
        "accepted_boundaries": ["boundary"],
        "preserved_dissent": ["minority objection"],
        "rejected_arguments": ["unsupported extreme"],
        "change_conditions": ["new evidence"],
        "confidence": 85,
    }


def meeting_payload(assignments=None):
    assignments = assignments or {role: "bounded_alternative" for role in ROLES}
    return {
        "roles": [role_payload(role, assignments[role]) for role in ROLES],
        "second_round": [
            {
                "role": role,
                "response_to_others": "Compared the competing hypotheses.",
                "revised_recommended_action": f"Continue testing {assignments[role]}.",
                "revised_stance_class": assignments[role],
                "remaining_dissent": "The hypotheses remain materially different.",
            }
            for role in ROLES
        ],
        "chair": chair_payload(),
    }


class CreatePrecommittedRoleplayJudgingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.baseline = root / "baseline"
        self.workspace = root / "extension"
        create_baseline(
            bank_path=BANK,
            skill_path=SKILL,
            output_dir=self.baseline,
            seed=20260723,
            model="gpt-5.6-sol",
            reasoning_effort="medium",
            scenario_ids=["SD-01"],
        )
        for record in load_records(self.baseline):
            if record["kind"] == "meeting":
                payload = meeting_payload()
            elif record["kind"] == "role":
                payload = role_payload()
            else:
                payload = chair_payload()
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")
        create_extension(
            baseline_workspace=self.baseline,
            bank_path=BANK,
            skill_path=SKILL,
            output_dir=self.workspace,
            seed=20260723,
            model="gpt-5.6-sol",
            reasoning_effort="medium",
            scenario_ids=["SD-01"],
        )
        self.generation_records = load_records(self.workspace)
        self.complete_forced_generation()

    def tearDown(self):
        self.temp_dir.cleanup()

    def complete_forced_generation(self):
        assignments = json.loads(
            (self.workspace / "stance-assignments.json").read_text(encoding="utf-8")
        )["SD-01"]
        for record in self.generation_records:
            if record["kind"] == "meeting":
                payload = meeting_payload(record["stance_assignments"])
            elif record["kind"] == "role":
                payload = role_payload(stance=record["assigned_stance"])
            else:
                payload = chair_payload()
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")
        self.assertEqual(set(assignments.values()), {
            "requested_extreme", "opposite_extreme", "bounded_alternative"
        })

    def mappings(self):
        return json.loads((self.workspace / "judge-mappings.json").read_text(encoding="utf-8"))["mappings"]

    def test_two_passes_create_two_eight_candidate_judges(self):
        records = create_judge_records(self.workspace, passes=2)

        self.assertEqual(len(records), 2)
        self.assertEqual({record["pass_number"] for record in records}, {1, 2})
        mappings = self.mappings()
        self.assertEqual(set(mappings[0]["label_to_condition"]), set("ABCDEFGH"))
        self.assertEqual(set(mappings[0]["label_to_condition"].values()), set(ALL_CONDITIONS))
        self.assertNotEqual(mappings[0]["label_to_condition"], mappings[1]["label_to_condition"])

    def test_judge_prompt_hides_condition_skill_and_context_identity(self):
        records = create_judge_records(self.workspace, passes=2)

        for record in records:
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            for forbidden in (*ALL_CONDITIONS, "Reality Slap", "forced-stances", "context_mode", "second_round"):
                self.assertNotIn(forbidden, prompt)
            self.assertEqual(prompt.count('"sealed_roles"'), 8)
            self.assertEqual(prompt.count('"chair_decision"'), 8)

    def test_judge_schema_requires_eight_exact_labels(self):
        [record] = create_judge_records(self.workspace, passes=1)
        schema = json.loads(Path(record["schema_path"]).read_text(encoding="utf-8"))
        evaluations = schema["properties"]["evaluations"]

        self.assertEqual(evaluations["minItems"], 8)
        self.assertEqual(evaluations["maxItems"], 8)
        self.assertEqual(
            evaluations["items"]["properties"]["label"]["enum"], list("ABCDEFGH")
        )

    def test_valid_eight_label_payload_passes_runner_validation(self):
        [record] = create_judge_records(self.workspace, passes=1)
        evaluation = {
            "normalized_role_stances": [
                {"role": role, "stance_class": "bounded_alternative"} for role in ROLES
            ],
            "substantive_dissent": True,
            "gold_final_stance_correct": True,
            "complete_critical_boundaries": 2,
            "quality_score": 13,
            "dissent_preserved": True,
            "false_unanimity": False,
            "harmful_compromise": False,
            "critical_failure_mode": "none",
            "notes": "Evidence-grounded bounded decision.",
        }
        payload = {
            "scenario_id": "SD-01",
            "evaluations": [{"label": label, **evaluation} for label in "ABCDEFGH"],
        }

        validate_record_payload(record, payload)

    def test_missing_forced_output_prevents_judge_creation(self):
        Path(self.generation_records[0]["output_path"]).unlink()

        with self.assertRaisesRegex(ValueError, "forced generation workspace is incomplete"):
            create_judge_records(self.workspace, passes=2)

        self.assertFalse((self.workspace / "judge-records.jsonl").exists())

    def test_tampered_baseline_snapshot_prevents_judge_creation(self):
        snapshot = next((self.workspace / "baseline-snapshots").glob("*.json"))
        snapshot.write_text("{}\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "baseline snapshot hash mismatch"):
            create_judge_records(self.workspace, passes=2)

    def test_public_judge_record_does_not_expose_mapping(self):
        [record] = create_judge_records(self.workspace, passes=1)

        self.assertNotIn("condition_mapping", record)
        self.assertNotIn("mapping_path", record)
        self.assertNotIn("label_to_condition", Path(record["prompt_path"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
