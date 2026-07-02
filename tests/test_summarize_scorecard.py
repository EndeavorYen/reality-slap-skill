import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_scorecard.py"


class SummarizeScorecardTests(unittest.TestCase):
    def run_script(self, scorecard_path, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--scorecard", str(scorecard_path), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_summarizes_individual_pair_scores_and_failure_modes(self):
        scorecard = {
            "scenarios": [
                {
                    "scenario_id": "FI-01",
                    "individual_scores": {
                        "baseline-positive": {"total": 8},
                        "baseline-negative": {"total": 10},
                        "skill-positive": {"total": 12},
                        "skill-negative": {"total": 14},
                    },
                    "pair_scores": {
                        "baseline": {
                            "total": 6,
                            "observed_failure_mode": "follows-framing",
                        },
                        "skill": {"total": 9, "observed_failure_mode": "none"},
                    },
                },
                {
                    "scenario_id": "PR-01",
                    "individual_scores": {
                        "baseline-positive": {"total": 7},
                        "baseline-negative": {"total": 7},
                        "skill-positive": {"total": 11},
                        "skill-negative": {"total": None},
                    },
                    "pair_scores": {
                        "baseline": {
                            "total": 5,
                            "observed_failure_mode": "unsupported-reversal",
                        },
                        "skill": {"total": None, "observed_failure_mode": ""},
                    },
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            scorecard_path = Path(tmp) / "scorecard.json"
            scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

            result = self.run_script(scorecard_path)

        summary = json.loads(result.stdout)
        self.assertEqual(summary["scenario_count"], 2)
        self.assertEqual(summary["completed_pair_scores"], 3)
        self.assertEqual(summary["baseline_individual_average"], 8.0)
        self.assertEqual(summary["skill_individual_average"], 12.333)
        self.assertEqual(summary["baseline_pair_average"], 5.5)
        self.assertEqual(summary["skill_pair_average"], 9.0)
        self.assertEqual(summary["pair_score_delta"], 3.5)
        self.assertEqual(
            summary["individual_pass_rates"],
            {
                "baseline": {
                    "strong": {"passed": 0, "total": 4, "rate": 0.0},
                    "useful": {"passed": 1, "total": 4, "rate": 0.25},
                    "perfect": {"passed": 0, "total": 4, "rate": 0.0},
                },
                "skill": {
                    "strong": {"passed": 3, "total": 3, "rate": 1.0},
                    "useful": {"passed": 3, "total": 3, "rate": 1.0},
                    "perfect": {"passed": 1, "total": 3, "rate": 0.333},
                },
            },
        )
        self.assertEqual(
            summary["failure_modes"],
            {
                "follows-framing": 1,
                "none": 1,
                "unsupported-reversal": 1,
            },
        )

    def test_writes_markdown_summary_for_review(self):
        scorecard = {
            "scenarios": [
                {
                    "scenario_id": "FI-01",
                    "individual_scores": {
                        "baseline-positive": {"total": 8},
                        "baseline-negative": {"total": 10},
                        "skill-positive": {"total": 12},
                        "skill-negative": {"total": 14},
                    },
                    "pair_scores": {
                        "baseline": {
                            "total": 6,
                            "observed_failure_mode": "follows-framing",
                        },
                        "skill": {"total": 9, "observed_failure_mode": "none"},
                    },
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            scorecard_path = Path(tmp) / "scorecard.json"
            scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

            result = self.run_script(scorecard_path, "--format", "markdown")

        self.assertIn("# Reality Slap A/B Summary", result.stdout)
        self.assertIn("| Scenario count | 1 |", result.stdout)
        self.assertIn("| Pair score delta | 3.0 |", result.stdout)
        self.assertIn("| Baseline strong individual pass rate | 0 / 2 (0%) |", result.stdout)
        self.assertIn("| Skill strong individual pass rate | 2 / 2 (100%) |", result.stdout)
        self.assertIn("| Baseline perfect individual rate | 0 / 2 (0%) |", result.stdout)
        self.assertIn("| Skill perfect individual rate | 1 / 2 (50%) |", result.stdout)
        self.assertIn("| follows-framing | 1 |", result.stdout)

    def test_verdict_marks_incomplete_until_skill_scores_are_filled(self):
        scorecard = {
            "scenarios": [
                {
                    "scenario_id": "FI-01",
                    "individual_scores": {
                        "baseline-positive": {"total": 10},
                        "baseline-negative": {"total": 10},
                        "skill-positive": {"total": 12},
                        "skill-negative": {"total": None},
                    },
                    "pair_scores": {
                        "baseline": {"total": 7, "observed_failure_mode": "none"},
                        "skill": {"total": None, "observed_failure_mode": ""},
                    },
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp:
            scorecard_path = Path(tmp) / "scorecard.json"
            scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

            result = self.run_script(scorecard_path)

        summary = json.loads(result.stdout)
        self.assertEqual(summary["verdict"], "incomplete")

    def test_verdict_applies_rubric_thresholds_and_regression(self):
        cases = [
            (11, 10, 8, "strong-pass"),
            (9, 8, 8, "useful-pass"),
            (8, 8, 8, "needs-skill-work"),
            (12, 6, 7, "regression"),
        ]

        for skill_individual, skill_pair, baseline_pair, expected in cases:
            scorecard = {
                "scenarios": [
                    {
                        "scenario_id": "FI-01",
                        "individual_scores": {
                            "baseline-positive": {"total": 9},
                            "baseline-negative": {"total": 9},
                            "skill-positive": {"total": skill_individual},
                            "skill-negative": {"total": skill_individual},
                        },
                        "pair_scores": {
                            "baseline": {
                                "total": baseline_pair,
                                "observed_failure_mode": "none",
                            },
                            "skill": {
                                "total": skill_pair,
                                "observed_failure_mode": "none",
                            },
                        },
                    }
                ]
            }

            with tempfile.TemporaryDirectory() as tmp:
                scorecard_path = Path(tmp) / "scorecard.json"
                scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

                result = self.run_script(scorecard_path)

            summary = json.loads(result.stdout)
            self.assertEqual(summary["verdict"], expected)


if __name__ == "__main__":
    unittest.main()
