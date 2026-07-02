import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_eval_design.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
FULL_BANK = ROOT / "evals" / "reality-slap-eval-bank-full.md"
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
        self.assertEqual(audit["profile"], "pilot")
        self.assertEqual(audit["scenario_count"], 25)
        self.assertEqual(audit["suite_counts"], {"EB": 7, "FI": 10, "PR": 8})
        self.assertEqual(audit["prompt_count"], 100)
        self.assertEqual(audit["missing_domain_groups"], [])
        self.assertEqual(audit["missing_rubric_dimensions"], [])
        self.assertEqual(audit["missing_runbook_capabilities"], [])

    def test_current_pilot_bank_fails_full_profile_until_expanded(self):
        result = self.run_script("--profile", "full", check=False)
        audit = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(audit["ok"])
        self.assertEqual(audit["profile"], "full")
        self.assertIn("expected 100 scenarios", result.stderr)
        self.assertIn("expected 40 FI scenarios", result.stderr)
        self.assertIn("expected 30 PR scenarios", result.stderr)
        self.assertIn("expected 30 EB scenarios", result.stderr)

    def test_full_eval_design_covers_goal_requirements(self):
        result = self.run_script("--profile", "full", bank=FULL_BANK)
        audit = json.loads(result.stdout)

        self.assertTrue(audit["ok"])
        self.assertEqual(audit["profile"], "full")
        self.assertEqual(audit["scenario_count"], 100)
        self.assertEqual(audit["suite_counts"], {"EB": 30, "FI": 40, "PR": 30})
        self.assertEqual(audit["prompt_count"], 400)
        self.assertEqual(audit["missing_runbook_capabilities"], [])

    def test_full_profile_requires_full_output_count_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            runbook = Path(tmp) / "runbook.md"
            runbook.write_text(
                RUNBOOK.read_text(encoding="utf-8").replace(
                    "400 / 400",
                    "full output count pending",
                ),
                encoding="utf-8",
            )

            result = self.run_script(
                "--profile",
                "full",
                bank=FULL_BANK,
                runbook=runbook,
                check=False,
            )

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
| FI-01 | Product roadmap | Generic facts. | Good. | Bad. | Stable. |
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
        self.assertIn("expected 25 scenarios", result.stderr)
        self.assertIn("missing domain group", result.stderr)
        self.assertIn("missing rubric dimension", result.stderr)
        self.assertIn("missing runbook capability", result.stderr)
        self.assertIn("missing runbook capability scoring-request-validation", result.stderr)
        self.assertIn("missing runbook capability score-update-validation", result.stderr)
        self.assertIn("missing runbook capability scoring-workflow-planning", result.stderr)


if __name__ == "__main__":
    unittest.main()
