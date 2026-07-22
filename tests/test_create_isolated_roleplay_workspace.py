import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_isolated_roleplay_workspace import create_workspace, load_records


BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
SKILL = ROOT / "SKILL.md"


class CreateIsolatedRoleplayWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"

    def tearDown(self):
        self.temp_dir.cleanup()

    def create(self, scenarios=None):
        return create_workspace(
            bank_path=BANK,
            skill_path=SKILL,
            output_dir=self.workspace,
            seed=20260723,
            model="gpt-5.6-sol",
            reasoning_effort="medium",
            scenario_ids=scenarios or [],
        )

    def records(self):
        return load_records(self.workspace)

    def record(self, condition, kind, role=None):
        for record in self.records():
            if record["condition"] != condition or record["kind"] != kind:
                continue
            if role is None or record.get("role") == role:
                return record
        self.fail(f"record not found: {condition} {kind} {role}")

    def test_workspace_has_balanced_frames_and_expected_call_inventory(self):
        manifest = self.create()

        self.assertEqual(manifest["scenario_count"], 12)
        self.assertEqual(manifest["generation_call_count"], 120)
        self.assertEqual(manifest["judge_call_count"], 24)
        self.assertEqual(manifest["planned_model_call_count"], 144)
        self.assertEqual(sorted(manifest["frame_counts"].values()), [6, 6])
        self.assertEqual(len(self.records()), 120)

    def test_one_case_has_two_shared_calls_six_roles_and_two_chairs(self):
        manifest = self.create(["SD-01"])
        records = self.records()

        self.assertEqual(manifest["generation_call_count"], 10)
        self.assertEqual(sum(record["kind"] == "meeting" for record in records), 2)
        self.assertEqual(sum(record["kind"] == "role" for record in records), 6)
        self.assertEqual(sum(record["kind"] == "chair" for record in records), 2)

    def test_isolated_role_prompt_has_no_peer_outputs(self):
        self.create(["SD-01"])
        record = self.record("isolated-control", "role", "evidence_reviewer")
        prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")

        self.assertNotIn("executive_sponsor output", prompt)
        self.assertNotIn("delivery_owner output", prompt)
        self.assertEqual(record["depends_on"], [])
        self.assertNotIn("peer_outputs", record)

    def test_chair_depends_on_exactly_three_same_condition_roles(self):
        self.create(["SD-01"])
        record = self.record("isolated-skill", "chair")

        self.assertEqual(len(record["depends_on"]), 3)
        self.assertTrue(all(call_id.startswith("SD-01:isolated-skill:role:") for call_id in record["depends_on"]))

    def test_skill_conditions_inline_exact_frozen_skill(self):
        manifest = self.create(["SD-01"])
        skill_prompt = Path(self.record("shared-skill", "meeting")["prompt_path"]).read_text(encoding="utf-8")
        control_prompt = Path(self.record("shared-control", "meeting")["prompt_path"]).read_text(encoding="utf-8")
        skill_text = SKILL.read_text(encoding="utf-8").strip()

        self.assertEqual(manifest["skill_sha256"], hashlib.sha256(SKILL.read_bytes()).hexdigest())
        self.assertIn(skill_text, skill_prompt)
        self.assertNotIn(skill_text, control_prompt)

    def test_manifest_locks_model_effort_seed_and_prompt_hashes(self):
        manifest = self.create(["SD-01"])

        self.assertEqual(manifest["model"], "gpt-5.6-sol")
        self.assertEqual(manifest["reasoning_effort"], "medium")
        self.assertEqual(manifest["seed"], 20260723)
        self.assertEqual(len(manifest["prompt_sha256"]), 10)
        self.assertTrue(all(len(digest) == 64 for digest in manifest["prompt_sha256"].values()))

    def test_output_schemas_are_strict_and_bound_confidence(self):
        self.create(["SD-01"])
        role_schema = json.loads((self.workspace / "schemas" / "role.json").read_text(encoding="utf-8"))
        meeting_schema = json.loads((self.workspace / "schemas" / "meeting.json").read_text(encoding="utf-8"))

        self.assertFalse(role_schema["additionalProperties"])
        self.assertEqual(role_schema["properties"]["confidence"]["minimum"], 0)
        self.assertEqual(role_schema["properties"]["confidence"]["maximum"], 100)
        self.assertEqual(meeting_schema["properties"]["roles"]["minItems"], 3)
        self.assertEqual(meeting_schema["properties"]["roles"]["maxItems"], 3)


if __name__ == "__main__":
    unittest.main()
