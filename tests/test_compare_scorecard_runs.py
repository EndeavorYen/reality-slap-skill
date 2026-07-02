import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_scorecard_runs.py"


class CompareScorecardRunsTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def write_scorecard(self, root, name, skill_individual, baseline_pair, skill_pair, failure_mode):
        scorecard = {
            "scenarios": [
                {
                    "scenario_id": "FI-01",
                    "suite": "frame-invariance",
                    "domain": "Product roadmap",
                    "individual_scores": {
                        "baseline-positive": {"total": 8},
                        "baseline-negative": {"total": 8},
                        "skill-positive": {"total": skill_individual},
                        "skill-negative": {"total": skill_individual},
                    },
                    "pair_scores": {
                        "baseline": {
                            "total": baseline_pair,
                            "observed_failure_mode": "follows-framing",
                        },
                        "skill": {
                            "total": skill_pair,
                            "observed_failure_mode": failure_mode,
                        },
                    },
                }
            ]
        }
        path = root / f"{name}.json"
        path.write_text(json.dumps(scorecard), encoding="utf-8")
        return path

    def test_compares_adjacent_scorecard_runs_as_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = self.write_scorecard(root, "v1", 8, 6, 6, "overpush")
            v2 = self.write_scorecard(root, "v2", 10, 6, 8, "none")

            result = self.run_script("--run", f"v1={v1}", "--run", f"v2={v2}")

        report = json.loads(result.stdout)
        self.assertEqual([run["label"] for run in report["runs"]], ["v1", "v2"])
        self.assertEqual(report["runs"][0]["summary"]["verdict"], "needs-skill-work")
        self.assertEqual(report["runs"][1]["summary"]["verdict"], "useful-pass")

        comparison = report["comparisons"][0]
        self.assertEqual(comparison["from"], "v1")
        self.assertEqual(comparison["to"], "v2")
        self.assertEqual(comparison["skill_individual_average_delta"], 2.0)
        self.assertEqual(comparison["skill_pair_average_delta"], 2.0)
        self.assertEqual(comparison["pair_score_delta_delta"], 2.0)
        self.assertEqual(comparison["verdict_change"], "needs-skill-work -> useful-pass")
        self.assertEqual(comparison["skill_failure_mode_delta"], {"overpush": -1})
        self.assertTrue(comparison["improved"])

    def test_markdown_report_is_reviewable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            v1 = self.write_scorecard(root, "v1", 8, 6, 6, "overpush")
            v2 = self.write_scorecard(root, "v2", 10, 6, 8, "none")

            result = self.run_script(
                "--run",
                f"v1={v1}",
                "--run",
                f"v2={v2}",
                "--format",
                "markdown",
            )

        self.assertIn("# Reality Slap Scorecard Trend", result.stdout)
        self.assertIn("| v1 | needs-skill-work | 8.0 | 6.0 | 0.0 |", result.stdout)
        self.assertIn("| v2 | useful-pass | 10.0 | 8.0 | 2.0 |", result.stdout)
        self.assertIn("| v1 -> v2 | yes | +2.0 | +2.0 | +2.0 |", result.stdout)
        self.assertIn("`overpush`: -1", result.stdout)


if __name__ == "__main__":
    unittest.main()
