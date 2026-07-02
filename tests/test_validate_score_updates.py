import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_score_updates.py"


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


def scorecard():
    return {
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


def update(score_type, configuration, score):
    return {
        "scenario_id": "FI-01",
        "score_type": score_type,
        "configuration": configuration,
        "score": score,
    }


def complete_updates():
    return [
        update("individual", "baseline-positive", VALID_INDIVIDUAL),
        update("individual", "baseline-negative", VALID_INDIVIDUAL),
        update("individual", "skill-positive", VALID_INDIVIDUAL),
        update("individual", "skill-negative", VALID_INDIVIDUAL),
        update("pair", "baseline", VALID_PAIR),
        update("pair", "skill", VALID_PAIR),
    ]


class ValidateScoreUpdatesTests(unittest.TestCase):
    def run_script(self, scorecard_data, updates, *args):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard_path = root / "scorecard.json"
            updates_path = root / "updates.jsonl"
            scorecard_path.write_text(json.dumps(scorecard_data), encoding="utf-8")
            updates_path.write_text(
                "".join(json.dumps(update_record) + "\n" for update_record in updates),
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--scorecard",
                    str(scorecard_path),
                    "--updates",
                    str(updates_path),
                    *args,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

    def test_complete_updates_cover_every_expected_target_once(self):
        result = self.run_script(scorecard(), complete_updates())

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["expected_updates"], 6)
        self.assertEqual(report["provided_updates"], 6)
        self.assertEqual(report["missing_update_count"], 0)
        self.assertEqual(report["duplicate_update_count"], 0)
        self.assertEqual(report["unknown_update_count"], 0)

    def test_missing_duplicate_and_unknown_targets_fail(self):
        updates = complete_updates()
        updates.pop(3)
        updates.append(update("pair", "skill", VALID_PAIR))
        updates.append(update("pair", "missing", VALID_PAIR))

        result = self.run_script(scorecard(), updates)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["missing_update_count"], 1)
        self.assertEqual(report["duplicate_update_count"], 1)
        self.assertEqual(report["unknown_update_count"], 1)
        self.assertIn("missing score update FI-01 individual skill-negative", result.stderr)
        self.assertIn("duplicate score update FI-01 pair skill", result.stderr)
        self.assertIn("unknown pair configuration missing", result.stderr)

    def test_invalid_score_values_fail_even_when_coverage_is_complete(self):
        updates = complete_updates()
        updates[0] = update(
            "individual",
            "baseline-positive",
            dict(VALID_INDIVIDUAL, total=12),
        )

        result = self.run_script(scorecard(), updates)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["missing_update_count"], 0)
        self.assertIn("FI-01.individual_scores.baseline-positive.total", result.stderr)

    def test_unknown_failure_mode_fails_even_when_coverage_is_complete(self):
        updates = complete_updates()
        updates[-1] = update(
            "pair",
            "skill",
            dict(VALID_PAIR, observed_failure_mode="unsupported-revesral"),
        )

        result = self.run_script(scorecard(), updates)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["missing_update_count"], 0)
        self.assertIn("FI-01.pair_scores.skill.observed_failure_mode", result.stderr)
        self.assertIn("unsupported-revesral", result.stderr)

    def test_can_validate_only_pair_updates_for_pair_scoring_batches(self):
        pair_updates = [
            update("pair", "baseline", VALID_PAIR),
            update("pair", "skill", VALID_PAIR),
        ]

        result = self.run_script(scorecard(), pair_updates, "--kind", "pair")

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["expected_updates"], 2)
        self.assertEqual(report["provided_updates"], 2)


if __name__ == "__main__":
    unittest.main()
