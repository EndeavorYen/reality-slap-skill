import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "expand_eval_bank.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class ExpandEvalBankTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_summary_counts_active_stance_drift_suite(self):
        result = self.run_script("--input", str(BANK), "--summary")
        summary = json.loads(result.stdout)

        self.assertEqual(summary["scenarios"], 6)
        self.assertEqual(summary["prompts"], 24)
        self.assertEqual(summary["suites"], {"SD": 6})

    def test_jsonl_expands_four_runs_per_scenario(self):
        result = self.run_script("--input", str(BANK), "--format", "jsonl")
        records = [json.loads(line) for line in result.stdout.splitlines()]

        self.assertEqual(len(records), 24)

        sd_runs = [record for record in records if record["scenario_id"] == "SD-01"]
        self.assertEqual(
            [record["configuration"] for record in sd_runs],
            [
                "baseline-positive",
                "baseline-negative",
                "skill-positive",
                "skill-negative",
            ],
        )
        self.assertIn("simulated conversation", sd_runs[0]["prompt"])
        self.assertIn("proxies every inference request", sd_runs[0]["prompt"])
        self.assertIn("publish best practices", sd_runs[1]["prompt"])
        self.assertEqual(sd_runs[0]["suite"], "stance-drift")
        self.assertTrue(
            sd_runs[0]["prompt"].startswith(
                "Use only the instructions in this prompt."
            )
        )
        self.assertTrue(sd_runs[2]["prompt"].startswith("Use $reality-slap to solve this."))

    def test_evidence_update_case_expands_without_old_suite_names(self):
        result = self.run_script(
            "--input",
            str(BANK),
            "--format",
            "jsonl",
            "--scenario",
            "SD-05",
        )
        records = [json.loads(line) for line in result.stdout.splitlines()]

        self.assertEqual(len(records), 4)
        self.assertTrue(all(record["suite"] == "stance-drift" for record in records))
        self.assertIn("material evidence satisfied the prior blockers", records[0]["expected_core_recommendation"])
        self.assertIn("stay firm", records[1]["prompt"])

    def test_scenario_filter_expands_only_selected_sample(self):
        result = self.run_script(
            "--input",
            str(BANK),
            "--format",
            "jsonl",
            "--scenario",
            "SD-01",
            "--scenario",
            "SD-06",
        )
        records = [json.loads(line) for line in result.stdout.splitlines()]

        self.assertEqual(len(records), 8)
        self.assertEqual(
            sorted({record["scenario_id"] for record in records}),
            ["SD-01", "SD-06"],
        )


if __name__ == "__main__":
    unittest.main()
