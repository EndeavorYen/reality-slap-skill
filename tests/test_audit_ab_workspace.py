import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKSPACE = ROOT / "scripts" / "create_ab_workspace.py"
AUDIT = ROOT / "scripts" / "audit_ab_workspace.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class AuditAbWorkspaceTests(unittest.TestCase):
    def create_sample_workspace(self, workspace):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKSPACE),
                "--input",
                str(BANK),
                "--output-dir",
                str(workspace),
                "--scenario",
                "FI-01",
                "--scenario",
                "PR-01",
                "--scenario",
                "EB-01",
                "--scenario",
                "EB-07",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_audit(self, workspace, *args):
        return subprocess.run(
            [sys.executable, str(AUDIT), "--workspace", str(workspace), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_reports_output_and_scorecard_completion_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)

            (workspace / "FI-01" / "baseline-positive" / "output.txt").write_text(
                "baseline answer", encoding="utf-8"
            )
            (workspace / "PR-01" / "skill-negative" / "output.txt").write_text(
                "skill answer", encoding="utf-8"
            )
            scorecard_path = workspace / "scorecard.json"
            scorecard = json.loads(scorecard_path.read_text())
            scorecard["scenarios"][0]["individual_scores"]["baseline-positive"][
                "total"
            ] = 12
            scorecard["scenarios"][0]["pair_scores"]["skill"]["total"] = 8
            scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

            result = self.run_audit(workspace)

        audit = json.loads(result.stdout)
        self.assertEqual(audit["scenario_count"], 4)
        self.assertEqual(audit["prompt_count"], 16)
        self.assertEqual(audit["outputs"]["total"], 16)
        self.assertEqual(audit["outputs"]["complete"], 2)
        self.assertEqual(audit["outputs"]["missing"], 14)
        self.assertFalse(audit["workspace_ready_for_scoring"])
        self.assertEqual(audit["scorecard"]["individual_total"], 16)
        self.assertEqual(audit["scorecard"]["individual_complete"], 1)
        self.assertEqual(audit["scorecard"]["pair_total"], 8)
        self.assertEqual(audit["scorecard"]["pair_complete"], 1)
        self.assertFalse(audit["scorecard_complete"])
        self.assertEqual(audit["suite_summary"]["frame-invariance"]["outputs_complete"], 1)
        self.assertEqual(audit["suite_summary"]["pressure-reversal"]["outputs_complete"], 1)
        self.assertEqual(audit["suite_summary"]["execution-boundary"]["outputs_total"], 8)
        self.assertEqual(
            audit["missing_outputs"][0]["output_path"],
            str(workspace / "FI-01" / "baseline-negative" / "output.txt"),
        )

    def test_runner_error_markers_do_not_count_as_completed_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)

            timeout_output = workspace / "FI-01" / "baseline-positive" / "output.txt"
            timeout_output.write_text(
                "ERROR: child process timed out after 120 seconds\n",
                encoding="utf-8",
            )
            quota_output = workspace / "PR-01" / "skill-negative" / "output.txt"
            quota_output.write_text(
                "ERROR: You've hit your usage limit. Try again later.\n",
                encoding="utf-8",
            )

            result = self.run_audit(workspace)

        audit = json.loads(result.stdout)
        self.assertEqual(audit["outputs"]["complete"], 0)
        self.assertEqual(audit["outputs"]["missing"], 16)
        self.assertEqual(len(audit["invalid_outputs"]), 2)
        self.assertEqual(
            audit["invalid_outputs"][0]["reason"],
            "ERROR: child process timed out after",
        )
        self.assertEqual(
            audit["invalid_outputs"][1]["reason"],
            "ERROR: You've hit your usage limit",
        )

    def test_markdown_report_lists_invalid_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)
            output_path = workspace / "FI-01" / "baseline-positive" / "output.txt"
            output_path.write_text(
                "ERROR: child process timed out after 120 seconds\n",
                encoding="utf-8",
            )

            result = self.run_audit(workspace, "--format", "markdown")

        self.assertIn("## Invalid Outputs", result.stdout)
        self.assertIn("FI-01", result.stdout)
        self.assertIn("ERROR: child process timed out after", result.stdout)

    def test_markdown_report_is_human_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)

            result = self.run_audit(workspace, "--format", "markdown")

        self.assertIn("# Reality Slap Workspace Audit", result.stdout)
        self.assertIn("| Outputs complete | 0 / 16 |", result.stdout)
        self.assertIn("| Scorecard complete | no |", result.stdout)
        self.assertIn("| frame-invariance | 1 | 0 / 4 | 0 / 2 |", result.stdout)

    def test_reports_workspace_integrity_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)

            manifest_path = workspace / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["prompt_count"] = 999
            manifest["scenario_ids"].append("FI-99")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            scorecard_path = workspace / "scorecard.json"
            scorecard = json.loads(scorecard_path.read_text())
            scorecard["scenarios"][0]["individual_scores"].pop("skill-negative")
            scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

            result = self.run_audit(workspace)

        audit = json.loads(result.stdout)
        self.assertFalse(audit["integrity"]["ok"])
        self.assertFalse(audit["workspace_ready_for_scoring"])
        self.assertFalse(audit["scorecard_complete"])
        self.assertIn("manifest prompt_count 999 != records 16", audit["integrity"]["errors"])
        self.assertIn(
            "manifest scenario_ids do not match records scenario ids",
            audit["integrity"]["errors"],
        )
        self.assertIn(
            "FI-01 individual score configurations do not match manifest configurations",
            audit["integrity"]["errors"],
        )

    def test_reports_prompt_and_expected_file_integrity_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)

            skill_prompt = workspace / "FI-01" / "skill-positive" / "prompt.txt"
            skill_prompt.write_text(
                skill_prompt.read_text(encoding="utf-8").replace(
                    "Use $reality-slap to solve this. Answer from the prompt only.\n\n",
                    "",
                ),
                encoding="utf-8",
            )
            expected = workspace / "PR-01" / "baseline-negative" / "expected.txt"
            expected.write_text("wrong expectation\n", encoding="utf-8")

            result = self.run_audit(workspace)

        audit = json.loads(result.stdout)
        self.assertFalse(audit["integrity"]["ok"])
        self.assertFalse(audit["workspace_ready_for_scoring"])
        self.assertIn(
            "FI-01 skill-positive prompt.txt does not match records prompt",
            audit["integrity"]["errors"],
        )
        self.assertIn(
            "PR-01 baseline-negative expected.txt does not match expected core recommendation",
            audit["integrity"]["errors"],
        )

    def test_reports_record_level_prompt_condition_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)

            records_path = workspace / "records.jsonl"
            records = [
                json.loads(line)
                for line in records_path.read_text(encoding="utf-8").splitlines()
            ]
            records[0]["uses_skill"] = True
            records[0]["prompt"] = (
                "Use $reality-slap to solve this. Answer from the prompt only.\n\n"
                + records[0]["prompt"]
            )
            records[2]["prompt"] = records[2]["prompt"].replace(
                "Use $reality-slap to solve this. Answer from the prompt only.\n\n",
                "",
            )
            records_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            result = self.run_audit(workspace)

        audit = json.loads(result.stdout)
        self.assertFalse(audit["integrity"]["ok"])
        self.assertIn(
            "FI-01 baseline-positive uses_skill does not match configuration",
            audit["integrity"]["errors"],
        )
        self.assertIn(
            "FI-01 baseline-positive baseline prompt contains $reality-slap invocation",
            audit["integrity"]["errors"],
        )
        self.assertIn(
            "FI-01 skill-positive skill prompt is missing $reality-slap invocation",
            audit["integrity"]["errors"],
        )

    def test_reports_missing_baseline_prompt_isolation_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_sample_workspace(workspace)

            records_path = workspace / "records.jsonl"
            records = [
                json.loads(line)
                for line in records_path.read_text(encoding="utf-8").splitlines()
            ]
            records[0]["prompt"] = records[0]["prompt"].replace(
                "Do not use $reality-slap or any custom skill. Answer from the prompt only.\n\n",
                "",
            )
            records_path.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            result = self.run_audit(workspace)

        audit = json.loads(result.stdout)
        self.assertFalse(audit["integrity"]["ok"])
        self.assertIn(
            "FI-01 baseline-positive baseline prompt is missing anti-skill isolation",
            audit["integrity"]["errors"],
        )


if __name__ == "__main__":
    unittest.main()
