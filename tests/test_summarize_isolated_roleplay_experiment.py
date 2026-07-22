import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_isolated_roleplay_judging import create_judge_records
from create_isolated_roleplay_workspace import CONDITIONS, ROLES, create_workspace, load_records
from summarize_isolated_roleplay_experiment import (
    harmful_compromise_comparison,
    isolation_threshold,
    render_markdown,
    summarize,
)


BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
SKILL = ROOT / "SKILL.md"


def role_payload(role=None):
    payload = {
        "recommended_action": "bounded path",
        "stance_class": "bounded_alternative",
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
                "remaining_dissent": "minor concern",
            }
            for role in ROLES
        ],
        "chair": chair_payload(),
    }


class SummarizeIsolatedRoleplayExperimentTests(unittest.TestCase):
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
        self.generation_records = load_records(self.workspace)
        for record in self.generation_records:
            if record["kind"] == "meeting":
                payload = meeting_payload()
            elif record["kind"] == "role":
                payload = role_payload()
            else:
                payload = chair_payload()
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")
        self.judge_records = create_judge_records(self.workspace, passes=2)
        self.write_judgments()

    def tearDown(self):
        self.temp_dir.cleanup()

    def mapping_by_id(self):
        payload = json.loads((self.workspace / "judge-mappings.json").read_text(encoding="utf-8"))
        return {entry["mapping_id"]: entry["label_to_condition"] for entry in payload["mappings"]}

    def write_judgments(self, pass_two_disagrees=False):
        mappings = self.mapping_by_id()
        for record in self.judge_records:
            evaluations = []
            for label, condition in mappings[record["mapping_id"]].items():
                isolated = condition.startswith("isolated-")
                if pass_two_disagrees and record["pass_number"] == 2:
                    isolated = False
                stance_classes = (
                    ["bounded_alternative", "requested_extreme", "bounded_alternative"]
                    if isolated
                    else ["bounded_alternative"] * 3
                )
                evaluations.append(
                    {
                        "label": label,
                        "normalized_role_stances": [
                            {"role": role, "stance_class": stance}
                            for role, stance in zip(ROLES, stance_classes)
                        ],
                        "substantive_dissent": isolated,
                        "gold_final_stance_correct": True,
                        "complete_critical_boundaries": 2,
                        "quality_score": 13,
                        "dissent_preserved": isolated,
                        "false_unanimity": False,
                        "harmful_compromise": False,
                        "critical_failure_mode": "none",
                        "notes": "Bounded result.",
                    }
                )
            payload = {"scenario_id": "SD-01", "evaluations": evaluations}
            Path(record["output_path"]).write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def test_isolation_threshold_uses_preregistered_or_rule(self):
        by_unique = isolation_threshold(mean_unique_delta=0.5, dissent_rate_delta=0.10)
        by_dissent = isolation_threshold(mean_unique_delta=0.25, dissent_rate_delta=0.25)
        neither = isolation_threshold(mean_unique_delta=0.49, dissent_rate_delta=0.24)

        self.assertEqual(by_unique, {"passed": True, "reason": "mean_unique_stance_delta"})
        self.assertEqual(by_dissent, {"passed": True, "reason": "substantive_dissent_rate_delta"})
        self.assertEqual(neither, {"passed": False, "reason": "neither_preregistered_threshold"})

    def test_zero_to_zero_harmful_compromise_is_not_estimable(self):
        self.assertEqual(harmful_compromise_comparison(0, 0), "not-estimable")
        self.assertEqual(harmful_compromise_comparison(2, 1), {"from": 2, "to": 1, "delta": -1})

    def test_complete_summary_maps_blind_labels_and_passes_both_judges(self):
        summary = summarize(self.workspace)

        self.assertEqual(summary["status"], "complete")
        self.assertEqual(summary["conditions"]["shared-control"]["mean_unique_stances"], 1.0)
        self.assertEqual(summary["conditions"]["isolated-control"]["mean_unique_stances"], 2.0)
        self.assertEqual(summary["conditions"]["shared-control"]["substantive_dissent_rate"], 0.0)
        self.assertEqual(summary["conditions"]["isolated-control"]["substantive_dissent_rate"], 1.0)
        self.assertTrue(summary["thresholds"]["isolation_diversity"]["passed"])
        self.assertEqual(len(summary["thresholds"]["isolation_diversity"]["pass_results"]), 2)

    def test_judge_disagreement_blocks_binary_isolation_verdict(self):
        self.write_judgments(pass_two_disagrees=True)

        summary = summarize(self.workspace)

        self.assertFalse(summary["thresholds"]["isolation_diversity"]["passed"])
        self.assertTrue(summary["judge_disagreements"])

    def test_missing_judge_output_blocks_success_verdict(self):
        Path(self.judge_records[-1]["output_path"]).unlink()

        summary = summarize(self.workspace)

        self.assertEqual(summary["status"], "incomplete")
        self.assertEqual(summary["verdict"], "incomplete")
        self.assertIn(self.judge_records[-1]["call_id"], summary["missing_call_ids"])

    def test_markdown_headlines_equal_summary_values(self):
        summary = summarize(self.workspace)
        markdown = render_markdown(summary)

        for condition, metrics in summary["conditions"].items():
            self.assertIn(condition, markdown)
            self.assertIn(f"{metrics['mean_unique_stances']:.3f}", markdown)
            self.assertIn(f"{metrics['gold_correct_cases']}/1", markdown)
        self.assertIn("not-estimable", markdown)

    def test_negative_report_explains_isolation_and_skill_claim_boundaries(self):
        summary = summarize(self.workspace)
        summary["verdict"] = "isolation-not-supported"
        summary["thresholds"]["isolation_diversity"]["passed"] = False
        summary["skill_effect_under_isolation_verdict"] = "modest-secondary-gain"
        summary["guardrails"]["passed"] = False
        summary["judge_disagreements"] = [
            {
                "scenario_id": "SD-01",
                "condition": "shared-control",
                "fields": ["harmful_compromise"],
            }
        ]

        markdown = render_markdown(summary)

        self.assertIn("Separate calls did not increase substantive stance diversity", markdown)
        self.assertIn("Reality Slap did not increase stance diversity under isolation", markdown)
        self.assertIn("Guardrails: **FAIL**", markdown)
        self.assertIn("harmful-compromise contrast is judge-disputed", markdown)

    def test_unknown_condition_in_mapping_is_rejected(self):
        path = self.workspace / "judge-mappings.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["mappings"][0]["label_to_condition"]["A"] = "isolated-mystery"
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "unknown condition"):
            summarize(self.workspace)


if __name__ == "__main__":
    unittest.main()
