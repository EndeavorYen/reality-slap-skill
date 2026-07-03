import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_ab_workspace.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


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
                "SD-01",
                "--scenario",
                "SD-06",
            )

            manifest = json.loads((out_dir / "manifest.json").read_text())
            self.assertEqual(manifest["scenario_count"], 2)
            self.assertEqual(manifest["prompt_count"], 8)
            self.assertEqual(manifest["scenario_ids"], ["SD-01", "SD-06"])

            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(records), 8)

            prompt_path = out_dir / "SD-01" / "baseline-positive" / "prompt.txt"
            output_path = out_dir / "SD-01" / "baseline-positive" / "output.txt"
            self.assertIn("request proxy", prompt_path.read_text())
            self.assertEqual(output_path.read_text(), "")

    def test_default_workspace_uses_active_eval_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script("--input", str(BANK), "--output-dir", str(out_dir))

            manifest = json.loads((out_dir / "manifest.json").read_text())
            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]

            self.assertEqual(manifest["scenario_count"], 6)
            self.assertEqual(manifest["prompt_count"], 24)
            self.assertEqual(len(records), 24)
            self.assertEqual(manifest["scenario_ids"][0], "SD-01")
            self.assertEqual(manifest["scenario_ids"][-1], "SD-06")

    def test_stance_drift_profile_accepts_active_eval_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script(
                "--input",
                str(BANK),
                "--output-dir",
                str(out_dir),
                "--profile",
                "stance-drift",
            )

            manifest = json.loads((out_dir / "manifest.json").read_text())
            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]
            scorecard = json.loads((out_dir / "scorecard.json").read_text())

            self.assertEqual(manifest["scenario_count"], 6)
            self.assertEqual(manifest["prompt_count"], 24)
            self.assertEqual(manifest["profile"], "stance-drift")
            self.assertEqual(len(records), 24)
            self.assertEqual(manifest["scenario_ids"][0], "SD-01")
            self.assertEqual(manifest["scenario_ids"][-1], "SD-06")
            self.assertEqual(scorecard["scenarios"][0]["suite"], "stance-drift")

    def test_scorecard_contains_individual_and_pair_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "ab-workspace"

            self.run_script(
                "--input",
                str(BANK),
                "--output-dir",
                str(out_dir),
                "--scenario",
                "SD-01",
            )

            scorecard = json.loads((out_dir / "scorecard.json").read_text())
            scenario = scorecard["scenarios"][0]

            self.assertEqual(scenario["scenario_id"], "SD-01")
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
