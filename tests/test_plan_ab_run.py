import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKSPACE = ROOT / "scripts" / "create_ab_workspace.py"
PLANNER = ROOT / "scripts" / "plan_ab_run.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class PlanAbRunTests(unittest.TestCase):
    def create_workspace(self, workspace):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKSPACE),
                "--input",
                str(BANK),
                "--output-dir",
                str(workspace),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_script(self, workspace, *args):
        return subprocess.run(
            [sys.executable, str(PLANNER), "--workspace", str(workspace), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_recommends_first_missing_suite_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_script(workspace, "--limit", "20")

        plan = json.loads(result.stdout)
        self.assertEqual(plan["next_action"], "run-live-output-batch")
        self.assertEqual(plan["next_suite"], "stance-drift")
        self.assertEqual(plan["outputs"]["missing"], 24)
        self.assertEqual(
            plan["dry_run_command"],
            [
                "python3",
                "scripts/run_codex_workspace.py",
                "--workspace",
                str(workspace),
                "--suite",
                "stance-drift",
                "--limit",
                "20",
            ],
        )
        self.assertEqual(plan["execute_command"][-1], "--execute")

    def test_recommends_scoring_after_stance_drift_outputs_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.complete_suite_outputs(workspace, "SD-")

            result = self.run_script(workspace, "--limit", "12")

        plan = json.loads(result.stdout)
        self.assertEqual(plan["next_action"], "create-scoring-requests")
        self.assertIsNone(plan["next_suite"])
        self.assertEqual(plan["suite_output_missing"]["stance-drift"], 0)

    def test_recommends_scoring_requests_once_outputs_are_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)

            result = self.run_script(workspace)

        plan = json.loads(result.stdout)
        self.assertEqual(plan["next_action"], "create-scoring-requests")
        self.assertIsNone(plan["next_suite"])
        self.assertEqual(plan["outputs"]["missing"], 0)
        self.assertIn("create_scoring_packets.py", " ".join(plan["scoring_packets_command"]))
        self.assertIn("create_scoring_requests.py", " ".join(plan["scoring_requests_command"]))
        self.assertIn("validate_score_updates.py", " ".join(plan["score_update_validation_command"]))
        self.assertIn("apply_score_updates.py", " ".join(plan["apply_score_updates_command"]))

    def test_recommends_repair_when_score_updates_are_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            score_updates = workspace / "score-updates.jsonl"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            score_updates.write_text(
                json.dumps(
                    {
                        "scenario_id": "SD-01",
                        "score_type": "pair",
                        "configuration": "skill",
                        "score": {
                            "core_recommendation_match": 2,
                            "frame_pressure_resistance": 2,
                            "unsupported_reversal_resistance": 2,
                            "bounded_support": 2,
                            "execution_readiness": 2,
                            "overpush_control": 2,
                            "total": 12,
                            "core_recommendation_match_label": "same",
                            "observed_failure_mode": "none",
                            "notes": "fixture",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_script(workspace)

        plan = json.loads(result.stdout)
        self.assertEqual(plan["next_action"], "repair-score-updates")
        self.assertFalse(plan["score_update_validation"]["ok"])
        self.assertGreater(plan["score_update_validation"]["missing_update_count"], 0)
        self.assertIn("validate_score_updates.py", " ".join(plan["score_update_validation_command"]))

    def test_recommends_apply_when_score_updates_are_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            self.write_complete_score_updates(workspace)

            result = self.run_script(workspace)

        plan = json.loads(result.stdout)
        self.assertEqual(plan["next_action"], "apply-score-updates")
        self.assertTrue(plan["score_update_validation"]["ok"])
        self.assertEqual(plan["score_update_validation"]["missing_update_count"], 0)
        self.assertIn("apply_score_updates.py", " ".join(plan["apply_score_updates_command"]))

    @staticmethod
    def complete_suite_outputs(workspace, prefix):
        for output in workspace.glob(f"{prefix}*/**/output.txt"):
            output.write_text("done", encoding="utf-8")

    @staticmethod
    def complete_all_outputs(workspace):
        for output in workspace.glob("*/**/output.txt"):
            output.write_text("done", encoding="utf-8")

    @staticmethod
    def write_complete_score_updates(workspace):
        scorecard = json.loads((workspace / "scorecard.json").read_text(encoding="utf-8"))
        updates = []
        for scenario in scorecard["scenarios"]:
            for configuration in scenario["individual_scores"]:
                updates.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "score_type": "individual",
                        "configuration": configuration,
                        "score": {
                            "stance": 2,
                            "evidence_discipline": 2,
                            "boundary_clarity": 2,
                            "useful_recommendation": 2,
                            "change_condition": 1,
                            "scope_and_tool_discipline": 2,
                            "tone_and_collaboration": 2,
                            "total": 13,
                            "notes": "fixture",
                        },
                    }
                )
            for configuration in scenario["pair_scores"]:
                updates.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "score_type": "pair",
                        "configuration": configuration,
                        "score": {
                            "core_recommendation_match": 2,
                            "frame_pressure_resistance": 2,
                            "unsupported_reversal_resistance": 2,
                            "bounded_support": 1,
                            "execution_readiness": 2,
                            "overpush_control": 2,
                            "total": 11,
                            "core_recommendation_match_label": "same",
                            "observed_failure_mode": "none",
                            "notes": "fixture",
                        },
                    }
                )
        (workspace / "score-updates.jsonl").write_text(
            "".join(json.dumps(update) + "\n" for update in updates),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
