import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_open_decision_debate_fixture import FIXTURE_MODES, run_fixture


class OpenDecisionDebateFixtureTests(unittest.TestCase):
    def test_fixture_runs_full_green_pipeline(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_fixture(Path(temp_dir) / "fixture", mode="stage2-green")

        self.assertEqual(result["status"], "complete")
        self.assertEqual(
            result["verdict"],
            "large-structured-debate-gain-supported",
        )
        self.assertEqual(result["audit"]["invalid_call_ids"], [])

    def test_fixture_exercises_every_preregistered_stage_one_route(self):
        expected = {
            "green": "stage1-large-bundle-signal",
            "amber": "incomplete",
            "not-supported": "not-supported",
            "safety-regression": "safety-regression",
            "evaluator-instability": "inconclusive-evaluator-instability",
            "incomplete": "incomplete",
        }
        self.assertTrue(expected.keys() <= FIXTURE_MODES)
        for mode, verdict in expected.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp_dir:
                result = run_fixture(Path(temp_dir) / "fixture", mode=mode)
                self.assertEqual(result["verdict"], verdict)


if __name__ == "__main__":
    unittest.main()
