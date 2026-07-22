import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_isolated_roleplay_workspace import ROLES, create_workspace as create_baseline, load_records
from create_precommitted_roleplay_workspace import (
    FORCED_STANCES,
    assign_stances,
    create_workspace,
)


BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
SKILL = ROOT / "SKILL.md"


def role_payload(role=None):
    payload = {
        "recommended_action": "Use a bounded path.",
        "stance_class": "bounded_alternative",
        "supporting_evidence": ["evidence"],
        "non_negotiable_boundaries": ["boundary"],
        "change_conditions": ["new evidence"],
        "confidence": 80,
    }
    return {"role": role, **payload} if role else payload


def chair_payload():
    return {
        "final_recommendation": "Use a bounded path.",
        "final_stance_class": "bounded_alternative",
        "accepted_boundaries": ["boundary"],
        "preserved_dissent": ["minority objection"],
        "rejected_arguments": ["unsupported extreme"],
        "change_conditions": ["new evidence"],
        "confidence": 85,
    }


def meeting_payload():
    return {
        "roles": [role_payload(role) for role in ROLES],
        "second_round": [
            {
                "role": role,
                "response_to_others": "Reviewed the competing hypotheses.",
                "revised_recommended_action": "Use a bounded path.",
                "revised_stance_class": "bounded_alternative",
                "remaining_dissent": "The assigned hypothesis remains conditional.",
            }
            for role in ROLES
        ],
        "chair": chair_payload(),
    }


class CreatePrecommittedRoleplayWorkspaceTests(unittest.TestCase):
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
        )
        self.baseline_records = load_records(self.baseline)
        for record in self.baseline_records:
            if record["kind"] == "meeting":
                payload = meeting_payload()
            elif record["kind"] == "role":
                payload = role_payload()
            else:
                payload = chair_payload()
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def create(self, scenario_ids=None):
        return create_workspace(
            baseline_workspace=self.baseline,
            bank_path=BANK,
            skill_path=SKILL,
            output_dir=self.workspace,
            seed=20260723,
            model="gpt-5.6-sol",
            reasoning_effort="medium",
            scenario_ids=scenario_ids or [],
        )

    def records(self):
        return load_records(self.workspace)

    def record(self, condition, kind, role=None):
        return next(
            record
            for record in self.records()
            if record["condition"] == condition
            and record["kind"] == kind
            and (role is None or record.get("role") == role)
        )

    def test_assignments_are_deterministic_and_cover_all_stances(self):
        first = assign_stances("SD-01", 20260723)
        second = assign_stances("SD-01", 20260723)

        self.assertEqual(first, second)
        self.assertEqual(set(first), set(ROLES))
        self.assertEqual(set(first.values()), set(FORCED_STANCES))

    def test_workspace_creates_exactly_120_new_generation_calls(self):
        manifest = self.create()

        self.assertEqual(manifest["new_generation_call_count"], 120)
        self.assertEqual(manifest["planned_judge_call_count"], 24)
        self.assertEqual(manifest["planned_new_model_call_count"], 144)
        self.assertEqual(len(self.records()), 120)
        self.assertEqual(len(manifest["baseline_snapshot_sha256"]), 48)

    def test_one_case_has_ten_new_generation_calls_and_four_snapshots(self):
        manifest = self.create(["SD-01"])

        self.assertEqual(manifest["new_generation_call_count"], 10)
        self.assertEqual(len(self.records()), 10)
        self.assertEqual(len(manifest["baseline_snapshot_sha256"]), 4)

    def test_isolated_role_sees_only_its_assignment(self):
        self.create(["SD-01"])
        record = self.record(
            "isolated-forced-control", "role", "evidence_reviewer"
        )
        prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")

        self.assertIn(f"Assigned stance: {record['assigned_stance']}", prompt)
        for peer in set(ROLES) - {"evidence_reviewer"}:
            self.assertNotIn(f"Functional role: {peer}", prompt)
        self.assertNotIn("peer assignment", prompt.lower())

    def test_same_assignment_is_reused_across_all_forced_conditions(self):
        self.create(["SD-01"])
        by_role = {}
        for record in self.records():
            if record["kind"] != "role":
                continue
            by_role.setdefault(record["role"], set()).add(record["assigned_stance"])

        self.assertEqual({role: 1 for role in ROLES}, {role: len(values) for role, values in by_role.items()})

    def test_baseline_metadata_mismatch_blocks_workspace(self):
        manifest_path = self.baseline / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["model"] = "wrong-model"
        manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "baseline metadata"):
            self.create(["SD-01"])

    def test_incomplete_baseline_blocks_workspace_without_snapshots(self):
        Path(self.baseline_records[0]["output_path"]).unlink()

        with self.assertRaisesRegex(ValueError, "baseline generation is incomplete"):
            self.create(["SD-01"])

        self.assertFalse((self.workspace / "baseline-snapshots").exists())

    def test_manifest_hashes_baseline_manifest_skill_and_prompts(self):
        manifest = self.create(["SD-01"])

        self.assertEqual(
            manifest["baseline_manifest_sha256"],
            hashlib.sha256((self.baseline / "manifest.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(manifest["skill_sha256"], hashlib.sha256(SKILL.read_bytes()).hexdigest())
        self.assertEqual(len(manifest["prompt_sha256"]), 10)


if __name__ == "__main__":
    unittest.main()
