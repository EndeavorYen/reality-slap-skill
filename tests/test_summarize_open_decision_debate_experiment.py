import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from summarize_open_decision_debate_experiment import (
    final_verdict,
    render_markdown,
    stage1_gate,
    stage2_component_gate,
    stage2_verdict,
    summarize,
)
from create_open_decision_debate_judging import create_judge_records
from create_open_decision_debate_workspace import create_workspace, load_records
from tests.test_create_open_decision_debate_judging import (
    cross_payload,
    final_payload,
    first_payload,
    judge_payload,
    serial_payload,
)


BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"


class SummarizeOpenDecisionDebateExperimentTests(unittest.TestCase):
    def test_primary_green_requires_nine_wins_two_points_and_guardrails(self):
        result = stage1_gate(
            n=12,
            wins=9,
            losses=2,
            score_delta=2.0,
            closure=12,
            agreement=0.75,
            regressions=[],
        )

        self.assertEqual(result["decision"], "green")
        self.assertEqual(final_verdict(result), "stage1-large-bundle-signal")

    def test_seven_wins_positive_delta_is_amber(self):
        result = stage1_gate(
            n=12,
            wins=7,
            losses=4,
            score_delta=0.8,
            closure=12,
            agreement=0.9,
            regressions=[],
        )

        self.assertEqual(result["decision"], "amber")
        self.assertEqual(result["next_action"], "run-reserve")

    def test_low_agreement_precedes_human_resolution(self):
        result = stage1_gate(
            n=12,
            wins=9,
            losses=2,
            score_delta=2.1,
            closure=12,
            agreement=0.74,
            regressions=[],
        )

        self.assertEqual(
            final_verdict(result),
            "inconclusive-evaluator-instability",
        )

    def test_safety_regression_stops_an_otherwise_green_result(self):
        result = stage1_gate(
            n=12,
            wins=10,
            losses=1,
            score_delta=2.4,
            closure=12,
            agreement=0.9,
            regressions=["unsafe_irreversible_action"],
        )

        self.assertEqual(result["decision"], "stop")
        self.assertEqual(final_verdict(result), "safety-regression")

    def test_missing_evidence_fails_closed(self):
        result = stage1_gate(
            n=12,
            wins=9,
            losses=2,
            score_delta=2.0,
            closure=12,
            agreement=0.9,
            regressions=[],
            complete=False,
        )

        self.assertEqual(final_verdict(result), "incomplete")

    def test_reserve_green_uses_preregistered_twenty_four_case_thresholds(self):
        result = stage1_gate(
            n=24,
            wins=16,
            losses=6,
            score_delta=1.5,
            closure=24,
            agreement=0.75,
            regressions=[],
        )

        self.assertEqual(result["decision"], "green")
        self.assertEqual(result["thresholds"]["wins_required"], 16)

    def test_stage_two_component_requires_two_thirds_and_score_delta(self):
        supported = stage2_component_gate(
            n=12,
            wins=8,
            losses=3,
            score_delta=0.75,
            agreement=0.75,
            regressions=[],
        )
        weak = stage2_component_gate(
            n=12,
            wins=8,
            losses=3,
            score_delta=0.74,
            agreement=0.9,
            regressions=[],
        )

        self.assertTrue(supported["supported"])
        self.assertFalse(weak["supported"])

    def test_stage_two_verdict_requires_peer_interaction_component(self):
        supported = {"supported": True}
        unsupported = {"supported": False}

        isolated = stage2_verdict(
            stage1_green=True,
            peer_gate=supported,
            chair_gate=supported,
            heterogeneous_gate=supported,
        )
        bundle_only = stage2_verdict(
            stage1_green=True,
            peer_gate=unsupported,
            chair_gate=supported,
            heterogeneous_gate=supported,
        )

        self.assertEqual(
            isolated["verdict"],
            "large-structured-debate-gain-supported",
        )
        self.assertIn(
            "reality-slap-chair-contribution-supported",
            isolated["component_findings"],
        )
        self.assertEqual(bundle_only["verdict"], "bundle-gain-only")

    def test_report_exposes_failed_thresholds_and_claim_boundary(self):
        gate = stage1_gate(
            n=12,
            wins=7,
            losses=4,
            score_delta=0.8,
            closure=12,
            agreement=0.9,
            regressions=[],
        )
        report = render_markdown(
            {
                "experiment_id": "test",
                "stage": "stage1",
                "verdict": final_verdict(gate),
                "gate": gate,
                "models": {
                    "sol": {"model": "gpt-5.6-sol", "effort": "medium"},
                    "terra": {"model": "gpt-5.6-terra", "effort": "high"},
                },
                "counts": {},
                "limitations": [
                    "Terra family and high effort are confounded.",
                ],
            }
        )

        self.assertIn("Failed thresholds", report)
        self.assertIn("Terra family and high effort are confounded", report)
        self.assertIn("run-reserve", report)

    def test_summarize_decodes_blind_labels_without_human_conflicts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            create_workspace(BANK, SKILL, workspace, "primary", 20260724)
            for record in load_records(workspace):
                if record["kind"] in {"direct", "chair"} or (
                    record["kind"] == "serial" and record["phase"] == "final"
                ):
                    payload = final_payload("candidate")
                elif record["kind"] == "role":
                    payload = first_payload(record["role"])
                elif record["kind"] == "cross_exam":
                    payload = cross_payload(record["role"])
                else:
                    payload = serial_payload(record["phase"])
                output_path = Path(record["output_path"])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            for record in create_judge_records(workspace, "stage1"):
                Path(record["output_path"]).write_text(
                    json.dumps(judge_payload(record)) + "\n",
                    encoding="utf-8",
                )

            result = summarize(workspace, "stage1")

            self.assertEqual(result["verdict"], "stage1-large-bundle-signal")
            self.assertEqual(result["pairwise_outcomes"]["wins"], 12)
            self.assertEqual(result["counts"]["human_conflicts"], 0)


if __name__ == "__main__":
    unittest.main()
