import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_eval_design.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
RUBRIC = ROOT / "evals" / "scoring-rubric.md"
RUNBOOK = ROOT / "evals" / "ab-test-runbook.md"


class AuditEvalDesignTests(unittest.TestCase):
    def run_script(self, *args, check=True, bank=BANK, runbook=RUNBOOK):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--bank",
                str(bank),
                "--rubric",
                str(RUBRIC),
                "--runbook",
                str(runbook),
                *args,
            ],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def test_current_eval_design_covers_goal_requirements(self):
        result = self.run_script()
        audit = json.loads(result.stdout)

        self.assertTrue(audit["ok"])
        self.assertEqual(audit["profile"], "stance-drift")
        self.assertEqual(audit["scenario_count"], 12)
        self.assertEqual(audit["suite_counts"], {"SD": 12})
        self.assertEqual(audit["prompt_count"], 48)
        self.assertEqual(audit["missing_pressure_groups"], [])
        self.assertEqual(audit["missing_rubric_dimensions"], [])
        self.assertEqual(audit["missing_runbook_capabilities"], [])

    def test_profile_requires_matching_output_count_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            runbook = Path(tmp) / "runbook.md"
            runbook.write_text(
                RUNBOOK.read_text(encoding="utf-8").replace(
                    "48 / 48",
                    "output count pending",
                ),
                encoding="utf-8",
            )

            result = self.run_script(runbook=runbook, check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing runbook capability full-output-count", result.stderr)

    def test_missing_required_coverage_fails_with_actionable_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_bank = Path(tmp) / "bank.md"
            bad_rubric = Path(tmp) / "rubric.md"
            bad_runbook = Path(tmp) / "runbook.md"
            bad_bank.write_text(
                """
| ID | Domain | Facts | Positive framing | Negative framing | Expected core recommendation |
| --- | --- | --- | --- | --- | --- |
| SD-01 | Product roadmap | Generic facts. | Good. | Bad. | Stable. |
""",
                encoding="utf-8",
            )
            bad_rubric.write_text("Core recommendation match only\n", encoding="utf-8")
            bad_runbook.write_text("Run outputs manually.\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--bank",
                    str(bad_bank),
                    "--rubric",
                    str(bad_rubric),
                    "--runbook",
                    str(bad_runbook),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("expected 12 scenarios", result.stderr)
        self.assertIn("missing pressure group", result.stderr)
        self.assertIn("missing rubric dimension", result.stderr)
        self.assertIn("missing runbook capability", result.stderr)
        self.assertIn("missing runbook capability scoring-request-validation", result.stderr)
        self.assertIn("missing runbook capability score-update-validation", result.stderr)
        self.assertIn("missing runbook capability scoring-workflow-planning", result.stderr)


if __name__ == "__main__":
    unittest.main()
