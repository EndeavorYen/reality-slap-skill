import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_eval_bank.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class ValidateEvalBankTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_current_bank_passes_validation(self):
        result = self.run_script("--input", str(BANK), "--profile", "stance-drift")

        self.assertEqual(result.returncode, 0)
        self.assertIn("Eval bank is valid", result.stdout)
        self.assertIn("6 scenarios", result.stdout)
        self.assertIn("profile stance-drift", result.stdout)

    def test_invalid_bank_reports_counts_duplicates_and_forbidden_terms(self):
        invalid_bank = """
| ID | Domain | Facts | Positive framing | Negative framing | Expected core recommendation |
| --- | --- | --- | --- | --- | --- |
| SD-01 | Product roadmap | Generic facts. | Good framing. | Bad framing. | Stable recommendation. |
| SD-01 | Product roadmap | Mentions GERM and /Users/simon/Code/Rexiano. | Good framing. | Bad framing. | Stable recommendation. |
"""

        with tempfile.TemporaryDirectory() as tmp:
            bank_path = Path(tmp) / "invalid.md"
            bank_path.write_text(invalid_bank, encoding="utf-8")

            result = self.run_script("--input", str(bank_path), "--profile", "stance-drift")

        self.assertEqual(result.returncode, 1)
        self.assertIn("expected 6 scenarios", result.stderr)
        self.assertIn("duplicate scenario id SD-01", result.stderr)
        self.assertIn("forbidden project-specific term", result.stderr)


if __name__ == "__main__":
    unittest.main()
