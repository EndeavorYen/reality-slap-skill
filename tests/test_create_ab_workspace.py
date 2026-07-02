import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ab_workspace.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
FULL_BANK = ROOT / "evals" / "reality-slap-eval-bank-full.md"
TRADEOFF_BANK = ROOT / "evals" / "reality-slap-tradeoff-eval-bank.md"


class CreateAbWorkspaceTests(unittest.TestCase):
    def run_script(self, *args, check=True):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def test_creates_sample_workspace_with_prompts_and_output_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script(
                "--input",
                str(BANK),
                "--output-dir",
                str(out_dir),
                "--scenario",
                "FI-01",
                "--scenario",
                "PR-01",
                "--scenario",
                "EB-01",
                "--scenario",
                "EB-07",
            )

            manifest = json.loads((out_dir / "manifest.json").read_text())
            self.assertEqual(manifest["scenario_count"], 4)
            self.assertEqual(manifest["prompt_count"], 16)
            self.assertEqual(
                manifest["scenario_ids"], ["FI-01", "PR-01", "EB-01", "EB-07"]
            )

            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(records), 16)

            prompt_path = out_dir / "FI-01" / "baseline-positive" / "prompt.txt"
            output_path = out_dir / "FI-01" / "baseline-positive" / "output.txt"
            self.assertIn("Switching the full team", prompt_path.read_text())
            self.assertEqual(output_path.read_text(), "")

    def test_default_workspace_uses_full_eval_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script("--input", str(BANK), "--output-dir", str(out_dir))

            manifest = json.loads((out_dir / "manifest.json").read_text())
            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]

            self.assertEqual(manifest["scenario_count"], 25)
            self.assertEqual(manifest["prompt_count"], 100)
            self.assertEqual(len(records), 100)
            self.assertEqual(manifest["scenario_ids"][0], "FI-01")
            self.assertEqual(manifest["scenario_ids"][-1], "EB-07")

    def test_full_profile_rejects_pilot_bank_before_creating_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input",
                    str(BANK),
                    "--output-dir",
                    str(out_dir),
                    "--profile",
                    "full",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("expected 100 scenarios", result.stderr)
            self.assertFalse(out_dir.exists())

    def test_full_profile_accepts_full_eval_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script(
                "--input",
                str(FULL_BANK),
                "--output-dir",
                str(out_dir),
                "--profile",
                "full",
            )

            manifest = json.loads((out_dir / "manifest.json").read_text())
            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]

            self.assertEqual(manifest["scenario_count"], 100)
            self.assertEqual(manifest["prompt_count"], 400)
            self.assertEqual(manifest["profile"], "full")
            self.assertEqual(len(records), 400)
            self.assertEqual(manifest["scenario_ids"][-1], "EB-30")

    def test_tradeoff_profile_accepts_tradeoff_eval_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script(
                "--input",
                str(TRADEOFF_BANK),
                "--output-dir",
                str(out_dir),
                "--profile",
                "tradeoff",
            )

            manifest = json.loads((out_dir / "manifest.json").read_text())
            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]
            scorecard = json.loads((out_dir / "scorecard.json").read_text())

            self.assertEqual(manifest["scenario_count"], 8)
            self.assertEqual(manifest["prompt_count"], 32)
            self.assertEqual(manifest["profile"], "tradeoff")
            self.assertEqual(len(records), 32)
            self.assertEqual(manifest["scenario_ids"][0], "TS-01")
            self.assertEqual(manifest["scenario_ids"][-1], "TS-08")
            self.assertEqual(scorecard["scenarios"][0]["suite"], "tradeoff-stability")

    def test_scorecard_contains_individual_and_pair_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script(
                "--input",
                str(BANK),
                "--output-dir",
                str(out_dir),
                "--scenario",
                "FI-01",
            )

            scorecard = json.loads((out_dir / "scorecard.json").read_text())
            scenario = scorecard["scenarios"][0]

            self.assertEqual(scenario["scenario_id"], "FI-01")
            self.assertEqual(
                sorted(scenario["individual_scores"]),
                [
                    "baseline-negative",
                    "baseline-positive",
                    "skill-negative",
                    "skill-positive",
                ],
            )
            self.assertEqual(sorted(scenario["pair_scores"]), ["baseline", "skill"])
            self.assertIn("stance", scenario["individual_scores"]["skill-positive"])
            self.assertIn("core_recommendation_match", scenario["pair_scores"]["skill"])
            self.assertIn("execution_readiness", scenario["pair_scores"]["skill"])
            self.assertIsNone(scenario["pair_scores"]["skill"]["total"])


if __name__ == "__main__":
    unittest.main()
