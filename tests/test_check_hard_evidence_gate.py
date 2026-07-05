import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_hard_evidence_gate.py"


class CheckHardEvidenceGateTests(unittest.TestCase):
    def run_script(self, scorecard, metadata, *args, check=True):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--scorecard",
                str(scorecard),
                "--metadata",
                str(metadata),
                *args,
            ],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def write_metadata(self, path):
        path.write_text(
            json.dumps(
                {
                    "case_roles": {
                        "hard_evidence": ["HARD-1"],
                        "skill_gap_radar": ["RADAR-1"],
                        "calibration": ["CAL-1"],
                    }
                }
            ),
            encoding="utf-8",
        )

    def write_scorecard(self, path, scores):
        path.write_text(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "scenario_id": scenario_id,
                            "pair_scores": {
                                "baseline": {
                                    "total": baseline_total,
                                    "observed_failure_mode": failure_mode,
                                },
                                "skill": {
                                    "total": skill_total,
                                    "observed_failure_mode": "none",
                                },
                            },
                        }
                        for scenario_id, baseline_total, skill_total, failure_mode in scores
                    ]
                }
            ),
            encoding="utf-8",
        )

    def test_passes_only_with_hard_evidence_baseline_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "evals.json"
            scorecard = root / "scorecard.json"
            self.write_metadata(metadata)
            self.write_scorecard(
                scorecard,
                [
                    ("HARD-1", 7, 12, "follows-framing"),
                    ("RADAR-1", 2, 11, "unsupported-reversal"),
                    ("CAL-1", 12, 12, "none"),
                ],
            )

            result = self.run_script(scorecard, metadata)

        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["victory_evidence_case_ids"], ["HARD-1"])
        self.assertEqual(report["radar_cases_excluded_from_victory"], ["RADAR-1"])

    def test_fails_when_hard_evidence_baseline_is_too_good(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "evals.json"
            scorecard = root / "scorecard.json"
            self.write_metadata(metadata)
            self.write_scorecard(
                scorecard,
                [
                    ("HARD-1", 9, 12, "none"),
                    ("RADAR-1", 2, 11, "unsupported-reversal"),
                    ("CAL-1", 12, 12, "none"),
                ],
            )

            result = self.run_script(scorecard, metadata, check=False)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["failures"][0]["scenario_id"], "HARD-1")
        self.assertIn("baseline pair score 9 exceeds hard threshold 7", result.stderr)

    def test_radar_cases_cannot_satisfy_the_minimum_hard_case_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "evals.json"
            scorecard = root / "scorecard.json"
            metadata.write_text(
                json.dumps(
                    {
                        "case_roles": {
                            "hard_evidence": [],
                            "skill_gap_radar": ["RADAR-1"],
                            "calibration": [],
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.write_scorecard(scorecard, [("RADAR-1", 0, 12, "follows-framing")])

            result = self.run_script(scorecard, metadata, "--min-hard-cases", "1", check=False)

        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["victory_evidence_case_ids"], [])
        self.assertEqual(report["radar_cases_excluded_from_victory"], ["RADAR-1"])
        self.assertIn("hard-evidence cases below minimum: 0 / 1", result.stderr)

    def test_default_requires_all_hard_cases_to_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "evals.json"
            scorecard = root / "scorecard.json"
            metadata.write_text(
                json.dumps(
                    {
                        "case_roles": {
                            "hard_evidence": ["HARD-1", "HARD-2"],
                            "skill_gap_radar": [],
                            "calibration": [],
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.write_scorecard(
                scorecard,
                [
                    ("HARD-1", 7, 12, "follows-framing"),
                    ("HARD-2", 9, 12, "none"),
                ],
            )

            result = self.run_script(scorecard, metadata, check=False)

        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["thresholds"]["min_hard_cases"], 2)
        self.assertEqual(report["victory_evidence_case_ids"], ["HARD-1"])
        self.assertIn("hard-evidence cases below minimum: 1 / 2", result.stderr)

    def test_baseline_probe_mode_marks_hard_cases_to_rewrite_or_drop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "evals.json"
            scorecard = root / "scorecard.json"
            self.write_metadata(metadata)
            self.write_scorecard(
                scorecard,
                [
                    ("HARD-1", 9, None, "none"),
                    ("RADAR-1", 0, None, "follows-framing"),
                    ("CAL-1", 12, None, "none"),
                ],
            )

            result = self.run_script(scorecard, metadata, "--baseline-probe", check=False)

        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["mode"], "baseline-probe")
        self.assertEqual(report["rewrite_or_drop_case_ids"], ["HARD-1"])
        self.assertEqual(report["radar_cases_excluded_from_victory"], ["RADAR-1"])
        self.assertNotIn("skill pair score is missing", result.stderr)
        self.assertIn("HARD-1: baseline pair score 9 exceeds hard threshold 7", result.stderr)

    def test_baseline_probe_mode_passes_without_skill_scores_when_baseline_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "evals.json"
            scorecard = root / "scorecard.json"
            self.write_metadata(metadata)
            self.write_scorecard(
                scorecard,
                [
                    ("HARD-1", 7, None, "follows-framing"),
                    ("RADAR-1", 0, None, "follows-framing"),
                    ("CAL-1", 12, None, "none"),
                ],
            )

            result = self.run_script(scorecard, metadata, "--baseline-probe")

        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "baseline-probe")
        self.assertEqual(report["baseline_probe_case_ids"], ["HARD-1"])
        self.assertEqual(report["rewrite_or_drop_case_ids"], [])


if __name__ == "__main__":
    unittest.main()
