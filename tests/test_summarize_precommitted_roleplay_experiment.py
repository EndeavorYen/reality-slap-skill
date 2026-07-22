import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_isolated_roleplay_workspace import ROLES, create_workspace as create_baseline, load_records
from create_precommitted_roleplay_judging import create_judge_records
from create_precommitted_roleplay_workspace import create_workspace as create_extension
from summarize_precommitted_roleplay_experiment import (
    interaction_threshold,
    manipulation_threshold,
    quality_threshold,
    render_markdown,
    summarize,
)


BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
SKILL = ROOT / "SKILL.md"


def role_payload(role=None, stance="bounded_alternative"):
    payload = {
        "recommended_action": f"Argue {stance}.",
        "stance_class": stance,
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


def meeting_payload(assignments=None):
    assignments = assignments or {role: "bounded_alternative" for role in ROLES}
    return {
        "roles": [role_payload(role, assignments[role]) for role in ROLES],
        "second_round": [
            {
                "role": role,
                "response_to_others": "Compared hypotheses.",
                "revised_recommended_action": f"Test {assignments[role]}.",
                "revised_stance_class": assignments[role],
                "remaining_dissent": "The hypotheses differ.",
            }
            for role in ROLES
        ],
        "chair": chair_payload(),
    }


class SummarizePrecommittedRoleplayExperimentTests(unittest.TestCase):
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
        self.complete_records(load_records(self.baseline), baseline=True)
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
        self.complete_records(self.generation_records, baseline=False)
        self.judge_records = create_judge_records(self.workspace, passes=2)
        self.write_judgments()

    def tearDown(self):
        self.temp_dir.cleanup()

    def complete_records(self, records, baseline):
        for record in records:
            if record["kind"] == "meeting":
                payload = meeting_payload(record.get("stance_assignments"))
            elif record["kind"] == "role":
                payload = role_payload(stance=record.get("assigned_stance", "bounded_alternative"))
            else:
                payload = chair_payload()
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def mappings(self):
        payload = json.loads((self.workspace / "judge-mappings.json").read_text(encoding="utf-8"))
        return {item["mapping_id"]: item["label_to_condition"] for item in payload["mappings"]}

    def write_judgments(
        self,
        isolated_forced_quality_by_pass=(11, 11),
        shared_forced_quality_by_pass=(10, 10),
        forced_unique_by_pass=(3, 3),
        harmful_by_pass=(False, False),
    ):
        mappings = self.mappings()
        for record in self.judge_records:
            pass_index = record["pass_number"] - 1
            evaluations = []
            for label, condition in mappings[record["mapping_id"]].items():
                forced = "forced" in condition
                if forced and condition.startswith("isolated-"):
                    quality = isolated_forced_quality_by_pass[pass_index]
                elif forced:
                    quality = shared_forced_quality_by_pass[pass_index]
                else:
                    quality = 10
                unique = forced_unique_by_pass[pass_index] if forced else 1
                stances = [
                    "requested_extreme", "opposite_extreme", "bounded_alternative"
                ][:unique]
                while len(stances) < 3:
                    stances.append(stances[-1])
                harmful = harmful_by_pass[pass_index] and condition.startswith("isolated-forced-")
                evaluations.append(
                    {
                        "label": label,
                        "normalized_role_stances": [
                            {"role": role, "stance_class": stance}
                            for role, stance in zip(ROLES, stances)
                        ],
                        "substantive_dissent": unique > 1,
                        "gold_final_stance_correct": True,
                        "complete_critical_boundaries": 2,
                        "quality_score": quality,
                        "dissent_preserved": unique > 1,
                        "false_unanimity": False,
                        "harmful_compromise": harmful,
                        "critical_failure_mode": "none",
                        "notes": "Evidence-grounded decision.",
                    }
                )
            Path(record["output_path"]).write_text(
                json.dumps({"scenario_id": "SD-01", "evaluations": evaluations}) + "\n",
                encoding="utf-8",
            )

    def test_manipulation_threshold_requires_both_checks_in_both_passes(self):
        passing = manipulation_threshold([
            {"mean_unique_stances": 2.5, "all_three_rate": 0.8},
            {"mean_unique_stances": 2.6, "all_three_rate": 1.0},
        ])
        failing = manipulation_threshold([
            {"mean_unique_stances": 2.6, "all_three_rate": 0.79},
            {"mean_unique_stances": 3.0, "all_three_rate": 1.0},
        ])

        self.assertTrue(passing["passed"])
        self.assertFalse(failing["passed"])

    def test_quality_threshold_requires_point_seven_five_and_cell_floor_in_both_passes(self):
        passing = quality_threshold([
            {"quality_delta": 0.75, "control_quality_delta": -0.25, "skill_quality_delta": 1.75},
            {"quality_delta": 1.0, "control_quality_delta": 1.0, "skill_quality_delta": 1.0},
        ])
        failing = quality_threshold([
            {"quality_delta": 0.75, "control_quality_delta": 0.75, "skill_quality_delta": 0.75},
            {"quality_delta": 0.74, "control_quality_delta": 0.74, "skill_quality_delta": 0.74},
        ])

        self.assertTrue(passing["passed"])
        self.assertFalse(failing["passed"])

    def test_interaction_threshold_requires_point_five_in_both_passes(self):
        self.assertTrue(interaction_threshold([0.5, 0.75])["passed"])
        self.assertFalse(interaction_threshold([0.5, 0.49])["passed"])

    def test_complete_summary_supports_isolated_precommitment(self):
        summary = summarize(self.workspace)

        self.assertEqual(summary["status"], "complete")
        self.assertEqual(summary["verdict"], "isolated-precommitment-supported")
        self.assertTrue(summary["thresholds"]["manipulation"]["passed"])
        self.assertTrue(summary["thresholds"]["quality_under_isolation"]["passed"])
        self.assertTrue(summary["thresholds"]["isolation_interaction"]["passed"])
        self.assertEqual(summary["pass_results"][0]["quality_under_isolation_delta"], 1.0)
        self.assertEqual(summary["pass_results"][0]["quality_interaction_delta"], 1.0)

    def test_precommitment_can_help_without_isolation_being_required(self):
        self.write_judgments(shared_forced_quality_by_pass=(11, 11))

        summary = summarize(self.workspace)

        self.assertEqual(summary["verdict"], "precommitment-supported-isolation-not-required")
        self.assertFalse(summary["thresholds"]["isolation_interaction"]["passed"])

    def test_diversity_only_when_quality_threshold_fails(self):
        self.write_judgments(isolated_forced_quality_by_pass=(10, 10))

        summary = summarize(self.workspace)

        self.assertEqual(summary["verdict"], "diversity-only")

    def test_manipulation_failure_has_distinct_verdict(self):
        self.write_judgments(forced_unique_by_pass=(2, 2))

        summary = summarize(self.workspace)

        self.assertEqual(summary["verdict"], "manipulation-failed")

    def test_guardrail_regression_precedes_supported_verdict(self):
        self.write_judgments(harmful_by_pass=(True, True))

        summary = summarize(self.workspace)

        self.assertEqual(summary["verdict"], "harmful")

    def test_disputed_safety_flag_is_inconclusive(self):
        self.write_judgments(harmful_by_pass=(True, False))

        summary = summarize(self.workspace)

        self.assertEqual(summary["verdict"], "inconclusive")
        self.assertTrue(summary["guardrails"]["disputed_safety"])

    def test_missing_judge_output_is_incomplete(self):
        Path(self.judge_records[-1]["output_path"]).unlink()

        summary = summarize(self.workspace)

        self.assertEqual(summary["verdict"], "incomplete")
        self.assertIn(self.judge_records[-1]["call_id"], summary["missing_call_ids"])

    def test_markdown_uses_exact_summary_headlines_and_claim_boundary(self):
        summary = summarize(self.workspace)
        markdown = render_markdown(summary)

        self.assertIn(f"`{summary['verdict']}`", markdown)
        self.assertIn(
            f"{summary['primary_effect']['quality_delta_mean']:+.3f}", markdown
        )
        self.assertIn(
            f"{summary['isolation_interaction']['quality_delta_mean']:+.3f}", markdown
        )
        self.assertIn("does not establish human-like independence", markdown)

    def test_inconclusive_report_still_states_failed_manipulation_quality_and_interaction(self):
        self.write_judgments(
            isolated_forced_quality_by_pass=(10, 10),
            forced_unique_by_pass=(2, 2),
            harmful_by_pass=(True, False),
        )
        summary = summarize(self.workspace)

        markdown = render_markdown(summary)

        self.assertEqual(summary["verdict"], "inconclusive")
        self.assertIn("did not clear the preregistered manipulation check", markdown)
        self.assertIn("did not clear the preregistered quality threshold", markdown)
        self.assertIn("did not clear the preregistered isolation interaction", markdown)


if __name__ == "__main__":
    unittest.main()
