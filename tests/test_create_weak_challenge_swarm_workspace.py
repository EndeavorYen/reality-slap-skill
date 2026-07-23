import collections
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_weak_challenge_swarm_workspace import (
    CHALLENGE_PACKET_MARKER,
    CONDITIONS,
    DRAFT_MARKER,
    LUNA_MODEL,
    ROLES,
    TERRA_MODEL,
    create_workspace,
    load_records,
)


BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"


class CreateWeakChallengeSwarmWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"

    def tearDown(self):
        self.temp_dir.cleanup()

    def create(self, output=None):
        return create_workspace(
            BANK,
            SKILL,
            output or self.workspace,
            seed=20260725,
        )

    def records(self, workspace=None):
        return load_records(workspace or self.workspace)

    def case_records(self, case_id):
        return [r for r in self.records() if r["case_id"] == case_id]

    def test_workspace_has_exact_factorial_call_budget(self):
        manifest = self.create()
        records = self.records()

        self.assertEqual(manifest["generation_call_count"], 96)
        self.assertEqual(manifest["planned_judge_call_count"], 24)
        self.assertEqual(manifest["planned_model_call_count"], 120)
        self.assertEqual(len(records), 96)
        self.assertEqual(
            collections.Counter(record["kind"] for record in records),
            {"draft": 12, "challenge": 36, "revision": 48},
        )
        self.assertEqual(manifest["case_ids"], [f"OD-{n:02d}" for n in range(13, 25)])
        self.assertEqual(set(manifest["conditions"]), set(CONDITIONS))

    def test_role_model_rotation_is_balanced_and_deterministic(self):
        first = self.create()
        second_workspace = Path(self.temp_dir.name) / "second"
        second = self.create(second_workspace)

        self.assertEqual(
            collections.Counter(
                (item["role"], item["model"])
                for item in first["challenger_assignment"].values()
            ),
            {
                (role, model): 6
                for role in ROLES
                for model in (TERRA_MODEL, LUNA_MODEL)
            },
        )
        self.assertEqual(
            collections.Counter(
                item["model"] for item in first["challenger_assignment"].values()
            ),
            {TERRA_MODEL: 18, LUNA_MODEL: 18},
        )
        self.assertEqual(
            first["challenger_assignment"],
            second["challenger_assignment"],
        )

    def test_each_case_has_shared_draft_three_isolated_challenges_and_four_revisions(self):
        manifest = self.create()
        records = self.case_records("OD-13")
        by_condition = {record["condition"]: record for record in records if record["kind"] != "challenge"}
        draft = by_condition["A"]
        challenges = {record["role"]: record for record in records if record["kind"] == "challenge"}

        self.assertEqual(len(records), 8)
        self.assertEqual(set(challenges), set(ROLES))
        self.assertEqual(challenges["boundary_scout"]["depends_on"], [])
        self.assertEqual(
            challenges["adversarial_auditor"]["depends_on"],
            [draft["call_id"]],
        )
        self.assertEqual(
            challenges["operational_auditor"]["depends_on"],
            [draft["call_id"]],
        )
        self.assertEqual(by_condition["B0"]["depends_on"], [draft["call_id"]])
        self.assertEqual(by_condition["B1"]["depends_on"], [draft["call_id"]])
        expected = [draft["call_id"]] + [
            challenges[role]["call_id"]
            for role in manifest["challenge_order_by_case"]["OD-13"]
        ]
        self.assertEqual(by_condition["C0"]["depends_on"], expected)
        self.assertEqual(by_condition["C1"]["depends_on"], expected)
        self.assertEqual(
            by_condition["C0"]["dependency_order_key"],
            by_condition["C1"]["dependency_order_key"],
        )

    def test_prompt_visibility_and_skill_placement_are_exact(self):
        self.create()
        records = self.case_records("OD-13")

        for record in records:
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            if record.get("role") == "boundary_scout":
                self.assertNotIn(DRAFT_MARKER, prompt)
            elif record["kind"] in {"challenge", "revision"}:
                self.assertIn(DRAFT_MARKER, prompt)
            if record.get("condition") in {"C0", "C1"}:
                self.assertIn(CHALLENGE_PACKET_MARKER, prompt)
            else:
                self.assertNotIn(CHALLENGE_PACKET_MARKER, prompt)
            self.assertEqual(
                "<FROZEN_REALITY_SLAP>" in prompt,
                record.get("condition") in {"B1", "C1"},
            )
            self.assertEqual(
                record["uses_skill"],
                record.get("condition") in {"B1", "C1"},
            )

    def test_manifest_hashes_every_frozen_input(self):
        manifest = self.create()
        self.assertEqual(
            manifest["bank_sha256"],
            hashlib.sha256(BANK.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            manifest["skill_sha256"],
            hashlib.sha256(SKILL.read_bytes()).hexdigest(),
        )
        self.assertEqual(len(manifest["prompt_sha256"]), 96)
        self.assertEqual(len(manifest["record_config_sha256"]), 96)
        self.assertEqual(len(manifest["case_snapshot_sha256"]), 12)
        self.assertEqual(len(manifest["adjudication_snapshot_sha256"]), 12)
        persisted = json.loads(
            (self.workspace / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(persisted, manifest)

    def test_challenge_and_revision_schemas_are_strict(self):
        self.create()
        challenge = json.loads(
            (self.workspace / "schemas" / "challenge.json").read_text(encoding="utf-8")
        )
        revision = json.loads(
            (self.workspace / "schemas" / "revision.json").read_text(encoding="utf-8")
        )
        self.assertFalse(challenge["additionalProperties"])
        self.assertEqual(
            challenge["properties"]["challenges"]["maxItems"],
            3,
        )
        self.assertFalse(revision["additionalProperties"])
        self.assertEqual(
            revision["properties"]["challenge_dispositions"]["maxItems"],
            9,
        )


if __name__ == "__main__":
    unittest.main()
