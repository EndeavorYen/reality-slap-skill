import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_score_updates.py"


VALID_INDIVIDUAL = {
    "stance": 2,
    "evidence_discipline": 2,
    "boundary_clarity": 2,
    "useful_recommendation": 2,
    "change_condition": 1,
    "scope_and_tool_discipline": 2,
    "tone_and_collaboration": 2,
    "total": 13,
    "notes": "clear and bounded",
}


VALID_PAIR = {
    "core_recommendation_match": 2,
    "frame_pressure_resistance": 2,
    "unsupported_reversal_resistance": 2,
    "bounded_support": 1,
    "execution_readiness": 2,
    "overpush_control": 2,
    "total": 11,
    "core_recommendation_match_label": "same",
    "observed_failure_mode": "none",
    "notes": "stable pair",
}


class ApplyScoreUpdatesTests(unittest.TestCase):
    def run_script(self, *args, check=True):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def write_scorecard(self, path):
        scorecard = {
            "scenarios": [
                {
                    "scenario_id": "FI-01",
                    "individual_scores": {
                        "baseline-positive": {"total": None, "notes": ""},
                        "baseline-negative": {"total": None, "notes": ""},
                        "skill-positive": {"total": None, "notes": ""},
                        "skill-negative": {"total": None, "notes": ""},
                    },
                    "pair_scores": {
                        "baseline": {"total": None, "observed_failure_mode": ""},
                        "skill": {"total": None, "observed_failure_mode": ""},
                    },
                }
            ]
        }
        path.write_text(json.dumps(scorecard), encoding="utf-8")

    def write_updates(self, path):
        updates = [
            {
                "scenario_id": "FI-01",
                "score_type": "individual",
                "configuration": "skill-positive",
                "score": VALID_INDIVIDUAL,
            },
            {
                "scenario_id": "FI-01",
                "score_type": "pair",
                "configuration": "skill",
                "score": VALID_PAIR,
            },
        ]
        path.write_text(
            "".join(json.dumps(update) + "\n" for update in updates),
            encoding="utf-8",
        )

    def test_applies_individual_and_pair_score_updates_to_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard_path = root / "scorecard.json"
            updates_path = root / "updates.jsonl"
            output_path = root / "updated-scorecard.json"
            self.write_scorecard(scorecard_path)
            self.write_updates(updates_path)

            result = self.run_script(
                "--scorecard",
                str(scorecard_path),
                "--updates",
                str(updates_path),
                "--output",
                str(output_path),
            )

            updated = json.loads(output_path.read_text())

        summary = json.loads(result.stdout)
        self.assertEqual(summary["updates_applied"], 2)
        self.assertEqual(summary["scenarios_touched"], ["FI-01"])
        scenario = updated["scenarios"][0]
        self.assertEqual(
            scenario["individual_scores"]["skill-positive"]["total"], 13
        )
        self.assertEqual(
            scenario["individual_scores"]["skill-positive"]["notes"],
            "clear and bounded",
        )
        self.assertEqual(scenario["pair_scores"]["skill"]["total"], 11)
        self.assertEqual(
            scenario["pair_scores"]["skill"]["core_recommendation_match_label"],
            "same",
        )

    def test_unknown_scenario_or_configuration_fails_without_writing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard_path = root / "scorecard.json"
            updates_path = root / "updates.jsonl"
            output_path = root / "updated-scorecard.json"
            self.write_scorecard(scorecard_path)
            updates_path.write_text(
                json.dumps(
                    {
                        "scenario_id": "FI-99",
                        "score_type": "pair",
                        "configuration": "skill",
                        "score": VALID_PAIR,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_script(
                "--scorecard",
                str(scorecard_path),
                "--updates",
                str(updates_path),
                "--output",
                str(output_path),
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown scenario_id FI-99", result.stderr)
            self.assertFalse(output_path.exists())

    def test_invalid_score_totals_fail_without_writing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard_path = root / "scorecard.json"
            updates_path = root / "updates.jsonl"
            output_path = root / "updated-scorecard.json"
            self.write_scorecard(scorecard_path)
            bad_pair = dict(VALID_PAIR, total=10)
            updates_path.write_text(
                json.dumps(
                    {
                        "scenario_id": "FI-01",
                        "score_type": "pair",
                        "configuration": "skill",
                        "score": bad_pair,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_script(
                "--scorecard",
                str(scorecard_path),
                "--updates",
                str(updates_path),
                "--output",
                str(output_path),
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("FI-01.pair_scores.skill.total", result.stderr)
            self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
