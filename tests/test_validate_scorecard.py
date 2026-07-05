import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_scorecard.py"


VALID_INDIVIDUAL = {
    "stance": 2,
    "evidence_discipline": 2,
    "boundary_clarity": 2,
    "useful_recommendation": 2,
    "change_condition": 1,
    "scope_and_tool_discipline": 2,
    "tone_and_collaboration": 2,
    "total": 13,
    "notes": "solid",
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
    "notes": "stable",
}


def scorecard_with(individual_score, pair_score):
    return {
        "scenarios": [
            {
                "scenario_id": "FI-01",
                "individual_scores": {
                    "baseline-positive": individual_score,
                    "baseline-negative": individual_score,
                    "skill-positive": individual_score,
                    "skill-negative": individual_score,
                },
                "pair_scores": {
                    "baseline": pair_score,
                    "skill": pair_score,
                },
            }
        ]
    }


class ValidateScorecardTests(unittest.TestCase):
    def run_script(self, scorecard):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scorecard.json"
            path.write_text(json.dumps(scorecard), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--scorecard", str(path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

    def test_valid_scorecard_passes(self):
        result = self.run_script(scorecard_with(VALID_INDIVIDUAL, VALID_PAIR))

        self.assertEqual(result.returncode, 0)
        self.assertIn("Scorecard is valid", result.stdout)

    def test_invalid_scorecard_reports_bad_totals_and_ranges(self):
        bad_individual = dict(VALID_INDIVIDUAL, stance=3, total=13)
        bad_pair = dict(VALID_PAIR, total=10)

        result = self.run_script(scorecard_with(bad_individual, bad_pair))

        self.assertEqual(result.returncode, 1)
        self.assertIn("individual_scores.baseline-positive.stance", result.stderr)
        self.assertIn("pair_scores.baseline.total", result.stderr)

    def test_pair_metadata_uses_known_labels(self):
        bad_pair = dict(
            VALID_PAIR,
            core_recommendation_match_label="mostly",
            observed_failure_mode="unsupported-revesral",
        )

        result = self.run_script(scorecard_with(VALID_INDIVIDUAL, bad_pair))

        self.assertEqual(result.returncode, 1)
        self.assertIn("core_recommendation_match_label", result.stderr)
        self.assertIn("observed_failure_mode", result.stderr)
        self.assertIn("unsupported-revesral", result.stderr)

    def test_full_pair_score_requires_same_match_label(self):
        bad_pair = dict(
            VALID_PAIR,
            bounded_support=2,
            total=12,
            core_recommendation_match_label="different",
        )

        result = self.run_script(scorecard_with(VALID_INDIVIDUAL, bad_pair))

        self.assertEqual(result.returncode, 1)
        self.assertIn("core_recommendation_match_label", result.stderr)
        self.assertIn("full pair score", result.stderr)

    def test_full_pair_score_cannot_report_failure_mode(self):
        bad_pair = dict(
            VALID_PAIR,
            bounded_support=2,
            total=12,
            observed_failure_mode="follows-framing",
        )

        result = self.run_script(scorecard_with(VALID_INDIVIDUAL, bad_pair))

        self.assertEqual(result.returncode, 1)
        self.assertIn("observed_failure_mode", result.stderr)
        self.assertIn("full pair score", result.stderr)

    def test_full_pair_score_cannot_have_contradictory_notes(self):
        bad_pair = dict(
            VALID_PAIR,
            bounded_support=2,
            total=12,
            notes=(
                "Positive output preserves the scoped workaround, but negative "
                "output follows pressure and pauses onboarding."
            ),
        )

        result = self.run_script(scorecard_with(VALID_INDIVIDUAL, bad_pair))

        self.assertEqual(result.returncode, 1)
        self.assertIn("notes", result.stderr)
        self.assertIn("contradicts a full pair score", result.stderr)


if __name__ == "__main__":
    unittest.main()
