import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_question_swarm_fixture import run_fixture


class QuestionSwarmFixtureTests(unittest.TestCase):
    def test_all_verdict_paths(self):
        expected = {
            "green": "green-command-candidate",
            "quality-fail": "cost-only-quality-fail",
            "cost-fail": "quality-only-cost-fail",
            "safety-regression": "safety-regression",
            "price-unresolved": "price-unresolved",
            "evaluator-instability": "inconclusive-evaluator-instability",
            "incomplete": "incomplete",
        }
        for mode, verdict in expected.items():
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp_dir:
                result = run_fixture(Path(temp_dir) / "workspace", mode)
                self.assertEqual(result["verdict"], verdict)
                self.assertEqual(result["counts"], {"generation": 56, "judges": 16})


if __name__ == "__main__":
    unittest.main()
