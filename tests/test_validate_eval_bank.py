import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_eval_bank.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
FULL_BANK = ROOT / "evals" / "reality-slap-eval-bank-full.md"
TRADEOFF_BANK = ROOT / "evals" / "reality-slap-tradeoff-eval-bank.md"


class ValidateEvalBankTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_current_bank_passes_validation(self):
        result = self.run_script("--input", str(BANK))

        self.assertEqual(result.returncode, 0)
        self.assertIn("Eval bank is valid", result.stdout)
        self.assertIn("25 scenarios", result.stdout)
        self.assertIn("profile pilot", result.stdout)

    def test_current_pilot_bank_fails_full_profile_until_expanded(self):
        result = self.run_script("--input", str(BANK), "--profile", "full")

        self.assertEqual(result.returncode, 1)
        self.assertIn("expected 100 scenarios", result.stderr)
        self.assertIn("expected 40 FI scenarios", result.stderr)
        self.assertIn("expected 30 PR scenarios", result.stderr)
        self.assertIn("expected 30 EB scenarios", result.stderr)

    def test_full_bank_passes_full_profile_validation(self):
        result = self.run_script("--input", str(FULL_BANK), "--profile", "full")

        self.assertEqual(result.returncode, 0)
        self.assertIn("Eval bank is valid", result.stdout)
        self.assertIn("100 scenarios", result.stdout)
        self.assertIn("profile full", result.stdout)

    def test_tradeoff_bank_passes_tradeoff_profile_validation(self):
        result = self.run_script("--input", str(TRADEOFF_BANK), "--profile", "tradeoff")

        self.assertEqual(result.returncode, 0)
        self.assertIn("Eval bank is valid", result.stdout)
        self.assertIn("8 scenarios", result.stdout)
        self.assertIn("profile tradeoff", result.stdout)

    def test_invalid_bank_reports_counts_duplicates_and_forbidden_terms(self):
        invalid_bank = """
| ID | Domain | Facts | Positive framing | Negative framing | Expected core recommendation |
| --- | --- | --- | --- | --- | --- |
| FI-01 | Product roadmap | Generic facts. | Good framing. | Bad framing. | Stable recommendation. |
| FI-01 | Product roadmap | Mentions /Users/simon/Code/Rexiano. | Good framing. | Bad framing. | Stable recommendation. |
"""

        with tempfile.TemporaryDirectory() as tmp:
            bank_path = Path(tmp) / "invalid.md"
            bank_path.write_text(invalid_bank, encoding="utf-8")

            result = self.run_script("--input", str(bank_path))

        self.assertEqual(result.returncode, 1)
        self.assertIn("expected 25 scenarios", result.stderr)
        self.assertIn("duplicate scenario id FI-01", result.stderr)
        self.assertIn("forbidden project-specific term", result.stderr)


if __name__ == "__main__":
    unittest.main()
