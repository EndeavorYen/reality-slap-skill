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

from create_open_decision_debate_workspace import (
    CONDITIONS,
    DEPENDENCY_PACKET_MARKER,
    STAGE2_D,
    STAGE2_E,
    STAGE2_F,
    ROLES,
    create_stage2_records,
    create_workspace,
    load_records,
    validate_stage2_reused_candidates,
)


BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"


class CreateOpenDecisionDebateWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"

    def tearDown(self):
        self.temp_dir.cleanup()

    def create(self, subset="primary"):
        return create_workspace(
            bank_path=BANK,
            skill_path=SKILL,
            output_dir=self.workspace,
            subset=subset,
            seed=20260724,
        )

    def records(self):
        return load_records(self.workspace)

    def case_records(self, case_id, condition):
        return [
            record
            for record in self.records()
            if record["case_id"] == case_id and record["condition"] == condition
        ]

    def test_primary_stage_one_has_exact_call_budget(self):
        manifest = self.create()
        records = self.records()

        self.assertEqual(manifest["generation_call_count"], 180)
        self.assertEqual(manifest["planned_judge_call_count"], 24)
        self.assertEqual(manifest["planned_model_call_count"], 204)
        self.assertEqual(len(records), 180)
        self.assertEqual(
            collections.Counter(record["condition"] for record in records),
            {
                "direct-sol": 12,
                "matched-serial-review": 84,
                "heterogeneous-debate-rs-chair": 84,
            },
        )
        self.assertEqual(set(manifest["conditions"]), set(CONDITIONS))

    def test_b_and_c_match_five_sol_two_terra_per_case(self):
        self.create()

        for condition in (
            "matched-serial-review",
            "heterogeneous-debate-rs-chair",
        ):
            with self.subTest(condition=condition):
                calls = self.case_records("OD-01", condition)
                self.assertEqual(
                    collections.Counter(
                        (record["model"], record["reasoning_effort"]) for record in calls
                    ),
                    {
                        ("gpt-5.6-sol", "medium"): 5,
                        ("gpt-5.6-terra", "high"): 2,
                    },
                )

    def test_terra_role_rotates_four_times_per_role_in_each_subset(self):
        manifest = self.create()

        self.assertEqual(
            collections.Counter(manifest["terra_role_by_case"].values()),
            {role: 4 for role in ROLES},
        )

    def test_serial_critics_are_independent_and_final_depends_on_six_prior_calls(self):
        self.create()
        records = self.case_records("OD-01", "matched-serial-review")
        by_phase = {record["phase"]: record for record in records}

        draft_id = by_phase["draft"]["call_id"]
        self.assertEqual(by_phase["risk-audit"]["depends_on"], [draft_id])
        self.assertEqual(by_phase["alternative-audit"]["depends_on"], [draft_id])
        self.assertNotIn(
            by_phase["risk-audit"]["call_id"],
            by_phase["alternative-audit"]["depends_on"],
        )
        self.assertEqual(len(by_phase["final"]["depends_on"]), 6)
        self.assertEqual(set(by_phase), {
            "draft",
            "risk-audit",
            "alternative-audit",
            "revision",
            "adversarial-audit",
            "calibration-audit",
            "final",
        })

    def test_first_round_roles_are_sealed_and_never_receive_skill(self):
        self.create()
        records = self.case_records("OD-01", "heterogeneous-debate-rs-chair")
        first_round = [record for record in records if record["kind"] == "role"]

        self.assertEqual({record["role"] for record in first_round}, set(ROLES))
        for record in first_round:
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertEqual(record["depends_on"], [])
            self.assertNotIn(DEPENDENCY_PACKET_MARKER, prompt)
            self.assertNotIn("<FROZEN_REALITY_SLAP>", prompt)
            for peer in set(ROLES) - {record["role"]}:
                self.assertNotIn(f"Your search role: {peer}", prompt)

    def test_each_cross_exam_depends_on_three_first_rounds_and_keeps_role_model(self):
        self.create()
        records = self.case_records("OD-01", "heterogeneous-debate-rs-chair")
        first_by_role = {
            record["role"]: record for record in records if record["kind"] == "role"
        }
        cross_by_role = {
            record["role"]: record for record in records if record["kind"] == "cross_exam"
        }

        self.assertEqual(set(cross_by_role), set(ROLES))
        for role, record in cross_by_role.items():
            self.assertEqual(set(record["depends_on"]), {
                first_by_role[item]["call_id"] for item in ROLES
            })
            self.assertEqual(record["model"], first_by_role[role]["model"])
            self.assertEqual(record["reasoning_effort"], first_by_role[role]["reasoning_effort"])
            self.assertIn(
                DEPENDENCY_PACKET_MARKER,
                Path(record["prompt_path"]).read_text(encoding="utf-8"),
            )

    def test_chair_depends_on_six_role_records_and_is_the_only_skill_call(self):
        self.create()
        records = self.case_records("OD-01", "heterogeneous-debate-rs-chair")
        chair = next(record for record in records if record["kind"] == "chair")
        role_records = [
            record for record in records if record["kind"] in {"role", "cross_exam"}
        ]

        self.assertEqual(set(chair["depends_on"]), {record["call_id"] for record in role_records})
        self.assertEqual((chair["model"], chair["reasoning_effort"]), ("gpt-5.6-sol", "medium"))
        self.assertTrue(chair["uses_skill"])
        self.assertIn(
            "<FROZEN_REALITY_SLAP>",
            Path(chair["prompt_path"]).read_text(encoding="utf-8"),
        )
        self.assertFalse(any(record["uses_skill"] for record in role_records))

    def test_manifest_hashes_bank_skill_prompts_and_assignments(self):
        manifest = self.create()

        self.assertEqual(manifest["bank_sha256"], hashlib.sha256(BANK.read_bytes()).hexdigest())
        self.assertEqual(manifest["skill_sha256"], hashlib.sha256(SKILL.read_bytes()).hexdigest())
        self.assertEqual(len(manifest["prompt_sha256"]), 180)
        self.assertEqual(len(manifest["record_config_sha256"]), 180)
        self.assertEqual(manifest["subset"], "primary")
        self.assertEqual(manifest["seed"], 20260724)
        self.assertEqual(manifest["case_ids"], [f"OD-{n:02d}" for n in range(1, 13)])

    def test_workspace_is_deterministic_for_same_seed(self):
        first = self.create()
        first_records = [
            {
                key: record[key]
                for key in ("call_id", "model", "reasoning_effort", "depends_on")
            }
            for record in self.records()
        ]
        other = Path(self.temp_dir.name) / "other"
        second = create_workspace(BANK, SKILL, other, "primary", 20260724)
        second_records = [
            {
                key: record[key]
                for key in ("call_id", "model", "reasoning_effort", "depends_on")
            }
            for record in load_records(other)
        ]

        self.assertEqual(first["terra_role_by_case"], second["terra_role_by_case"])
        self.assertEqual(first["prompt_sha256"], second["prompt_sha256"])
        self.assertEqual(first_records, second_records)

    def create_stage2(self):
        self.create()
        for record in self.records():
            if (
                record["condition"] == "heterogeneous-debate-rs-chair"
                and record["kind"] == "chair"
            ):
                output = {
                    "recommendation": "Run a bounded pilot.",
                    "accepted_claims": ["The pilot is reversible."],
                    "rejected_claims": ["A full rollout is unsupported."],
                    "residual_dissent": ["The effect size remains uncertain."],
                    "decision_owner": "Named owner",
                    "next_action": "Start the pilot.",
                    "stop_conditions": ["Stop on threshold failure."],
                    "rollback_or_revision_path": "Return to the prior state.",
                    "change_evidence": ["Validated production evidence."],
                    "known_facts": ["The supplied constraint."],
                    "inferences": ["A bounded inference."],
                    "uncertainties": ["Outcome size."],
                }
                Path(record["output_path"]).write_text(
                    json.dumps(output) + "\n",
                    encoding="utf-8",
                )
        stage2 = Path(self.temp_dir.name) / "stage2"
        manifest = create_stage2_records(self.workspace, stage2)
        return stage2, manifest

    def test_stage_two_adds_exactly_276_calls_for_twelve_cases(self):
        stage2, manifest = self.create_stage2()
        records = load_records(stage2)

        self.assertEqual(manifest["new_generation_call_count"], 252)
        self.assertEqual(manifest["planned_judge_call_count"], 24)
        self.assertEqual(manifest["planned_model_call_count"], 276)
        self.assertEqual(
            collections.Counter(record["condition"] for record in records),
            {
                "heterogeneous-debate-rs-chair": 12,
                STAGE2_D: 84,
                STAGE2_E: 84,
                STAGE2_F: 84,
            },
        )

    def test_d_self_reviews_never_receive_peer_outputs(self):
        stage2, _ = self.create_stage2()
        records = load_records(stage2)

        for record in (
            item
            for item in records
            if item["condition"] == STAGE2_D and item["kind"] == "self_review"
        ):
            self.assertEqual(record["depends_on"], [record["own_first_round_call_id"]])

    def test_e_uses_normal_chair_without_reality_slap(self):
        stage2, _ = self.create_stage2()
        chair = next(
            record
            for record in load_records(stage2)
            if record["condition"] == STAGE2_E and record["kind"] == "chair"
        )

        self.assertFalse(chair["uses_skill"])
        self.assertNotIn(
            "<FROZEN_REALITY_SLAP>",
            Path(chair["prompt_path"]).read_text(encoding="utf-8"),
        )

    def test_f_is_homogeneous_sol_medium(self):
        stage2, _ = self.create_stage2()
        calls = [
            record
            for record in load_records(stage2)
            if record["condition"] == STAGE2_F
        ]

        self.assertEqual(
            {(record["model"], record["reasoning_effort"]) for record in calls},
            {("gpt-5.6-sol", "medium")},
        )

    def test_stage_two_reused_c_candidate_hash_is_enforced(self):
        stage2, _ = self.create_stage2()
        reused = next(
            record
            for record in load_records(stage2)
            if record["condition"] == "heterogeneous-debate-rs-chair"
        )
        Path(reused["output_path"]).write_text("{}\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "reused candidate hash mismatch"):
            validate_stage2_reused_candidates(stage2)


if __name__ == "__main__":
    unittest.main()
