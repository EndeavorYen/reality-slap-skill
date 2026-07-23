import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_weak_challenge_swarm_fixture import run_fixture


class WeakChallengeSwarmFixtureTests(unittest.TestCase):
    def run_mode(self, mode):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return run_fixture(Path(temp_dir.name) / "workspace", mode)

    def test_green_fixture_runs_exact_live_pipeline_without_models(self):
        result = self.run_mode("green")
        self.assertEqual(
            result["verdict"],
            "weak-challenge-swarm-plus-reality-slap-internal-signal",
        )
        self.assertEqual(result["audit"]["invalid_call_ids"], [])
        self.assertEqual(result["counts"]["generation_records"], 96)
        self.assertEqual(result["counts"]["judge_records"], 24)
        self.assertGreaterEqual(
            result["summary"]["screening_metrics"]["burden_reduction"],
            0.25,
        )

    def test_amber_and_not_supported_routes_use_real_checklists(self):
        amber = self.run_mode("amber")
        unsupported = self.run_mode("not-supported")
        self.assertEqual(amber["verdict"], "replication-required")
        self.assertEqual(amber["summary"]["screening_metrics"]["improved_cases"], 2)
        self.assertEqual(unsupported["verdict"], "not-supported")

    def test_safety_and_instability_fail_closed(self):
        unsafe = self.run_mode("safety-regression")
        unstable = self.run_mode("evaluator-instability")
        self.assertEqual(unsafe["verdict"], "safety-regression")
        self.assertEqual(
            unstable["verdict"],
            "inconclusive-evaluator-instability",
        )
        self.assertLess(unstable["summary"]["checklist_agreement"], 0.75)

    def test_incomplete_and_invalid_challenge_are_visible(self):
        incomplete = self.run_mode("incomplete")
        invalid = self.run_mode("invalid-challenge")
        self.assertEqual(incomplete["verdict"], "incomplete")
        self.assertTrue(incomplete["summary"]["incomplete_call_ids"])
        self.assertEqual(invalid["fixture_verdict"], "invalid-challenge")
        self.assertTrue(invalid["audit"]["invalid_call_ids"])

    def test_rs_over_rejection_fixture_exposes_negative_c1_minus_c0(self):
        result = self.run_mode("rs-over-rejection")
        comparison = result["summary"]["factorial_comparisons"][
            "reality_slap_with_challenges"
        ]
        self.assertGreater(comparison["burden_delta"], 0)
        self.assertEqual(result["verdict"], "not-supported")


if __name__ == "__main__":
    unittest.main()
