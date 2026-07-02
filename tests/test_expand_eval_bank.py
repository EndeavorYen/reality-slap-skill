import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "expand_eval_bank.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
FULL_BANK = ROOT / "evals" / "reality-slap-eval-bank-full.md"
TRADEOFF_BANK = ROOT / "evals" / "reality-slap-tradeoff-eval-bank.md"


class ExpandEvalBankTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_summary_counts_all_three_suites(self):
        result = self.run_script("--input", str(BANK), "--summary")
        summary = json.loads(result.stdout)

        self.assertEqual(summary["scenarios"], 25)
        self.assertEqual(summary["prompts"], 100)
        self.assertEqual(summary["suites"], {"FI": 10, "PR": 8, "EB": 7})

    def test_full_bank_summary_matches_final_target(self):
        result = self.run_script("--input", str(FULL_BANK), "--summary")
        summary = json.loads(result.stdout)

        self.assertEqual(summary["scenarios"], 100)
        self.assertEqual(summary["prompts"], 400)
        self.assertEqual(summary["suites"], {"FI": 40, "PR": 30, "EB": 30})

    def test_tradeoff_bank_summary_matches_stability_profile(self):
        result = self.run_script("--input", str(TRADEOFF_BANK), "--summary")
        summary = json.loads(result.stdout)

        self.assertEqual(summary["scenarios"], 8)
        self.assertEqual(summary["prompts"], 32)
        self.assertEqual(summary["suites"], {"TS": 8})

    def test_tradeoff_cases_expand_with_evidence_update_prompt(self):
        result = self.run_script("--input", str(TRADEOFF_BANK), "--format", "jsonl")
        records = [json.loads(line) for line in result.stdout.splitlines()]

        ts_runs = [record for record in records if record["scenario_id"] == "TS-01"]

        self.assertEqual(len(ts_runs), 4)
        self.assertEqual(ts_runs[0]["suite"], "tradeoff-stability")
        self.assertIn("default to standardizing on one runtime", ts_runs[0]["prompt"])
        self.assertIn("default to keeping a framework-neutral pool", ts_runs[1]["prompt"])
        self.assertIn("new utilization data", ts_runs[0]["prompt"])
        self.assertIn("under the original evidence", ts_runs[1]["expected_core_recommendation"])

    def test_jsonl_expands_four_runs_per_scenario(self):
        result = self.run_script("--input", str(BANK), "--format", "jsonl")
        records = [json.loads(line) for line in result.stdout.splitlines()]

        self.assertEqual(len(records), 100)

        fi_runs = [record for record in records if record["scenario_id"] == "FI-01"]
        self.assertEqual(
            [record["configuration"] for record in fi_runs],
            [
                "baseline-positive",
                "baseline-negative",
                "skill-positive",
                "skill-negative",
            ],
        )
        self.assertIn("Switching the full team to the viral feature", fi_runs[0]["prompt"])
        self.assertIn("Switching the full team away from reliability", fi_runs[1]["prompt"])
        self.assertTrue(
            fi_runs[0]["prompt"].startswith(
                "Do not use $reality-slap or any custom skill."
            )
        )
        self.assertTrue(
            fi_runs[1]["prompt"].startswith(
                "Do not use $reality-slap or any custom skill."
            )
        )
        self.assertTrue(fi_runs[2]["prompt"].startswith("Use $reality-slap to solve this."))
        self.assertIn("Answer from the prompt only.", fi_runs[2]["prompt"])

    def test_pressure_and_execution_cases_expand_with_expected_prompt_text(self):
        result = self.run_script("--input", str(BANK), "--format", "jsonl")
        records = [json.loads(line) for line in result.stdout.splitlines()]

        pr_runs = [record for record in records if record["scenario_id"] == "PR-01"]
        eb_runs = [record for record in records if record["scenario_id"] == "EB-01"]

        self.assertEqual(len(pr_runs), 4)
        self.assertEqual(len(eb_runs), 4)
        self.assertIn("please support switching fully", pr_runs[0]["prompt"])
        self.assertIn("Draft a two-week discovery plan", eb_runs[0]["prompt"])
        self.assertEqual(pr_runs[0]["suite"], "pressure-reversal")
        self.assertEqual(eb_runs[0]["suite"], "execution-boundary")

    def test_scenario_filter_expands_only_selected_sample(self):
        result = self.run_script(
            "--input",
            str(BANK),
            "--format",
            "jsonl",
            "--scenario",
            "FI-01",
            "--scenario",
            "PR-01",
            "--scenario",
            "EB-01",
            "--scenario",
            "EB-07",
        )
        records = [json.loads(line) for line in result.stdout.splitlines()]

        self.assertEqual(len(records), 16)
        self.assertEqual(
            sorted({record["scenario_id"] for record in records}),
            ["EB-01", "EB-07", "FI-01", "PR-01"],
        )


if __name__ == "__main__":
    unittest.main()
