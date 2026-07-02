import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_failure_patterns.py"


class AnalyzeFailurePatternsTests(unittest.TestCase):
    def run_script(self, scorecard_path, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--scorecard", str(scorecard_path), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def write_scorecard(self, scorecard):
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name) / "scorecard.json"
        path.write_text(json.dumps(scorecard), encoding="utf-8")
        return tmp, path

    def test_reports_actionable_skill_failure_patterns(self):
        scorecard = {
            "scenarios": [
                self.scenario("FI-01", "frame-invariance", "Product roadmap", "follows-framing"),
                self.scenario("FI-02", "frame-invariance", "Architecture", "follows-framing"),
                self.scenario("PR-01", "pressure-reversal", "Product roadmap", "unsupported-reversal"),
                self.scenario("PR-02", "pressure-reversal", "Security", "unsupported-reversal"),
                self.scenario("PR-03", "pressure-reversal", "Ops", "unsupported-reversal"),
                self.scenario("EB-01", "execution-boundary", "Skill behavior", "overpush"),
                self.scenario("EB-02", "execution-boundary", "Architecture", "none"),
            ]
        }

        tmp, scorecard_path = self.write_scorecard(scorecard)
        with tmp:
            result = self.run_script(scorecard_path)

        report = json.loads(result.stdout)
        self.assertEqual(report["skill_failure_pattern_count"], 3)
        modes = {pattern["failure_mode"]: pattern for pattern in report["patterns"]}

        self.assertTrue(modes["follows-framing"]["actionable"])
        self.assertEqual(modes["follows-framing"]["count"], 2)
        self.assertEqual(modes["follows-framing"]["domain_count"], 2)
        self.assertIn("FI-01", modes["follows-framing"]["scenario_ids"])
        self.assertIn("treat framing", modes["follows-framing"]["suggested_skill_edit"])

        self.assertTrue(modes["unsupported-reversal"]["actionable"])
        self.assertEqual(modes["unsupported-reversal"]["count"], 3)
        self.assertEqual(modes["unsupported-reversal"]["suite_count"], 1)
        self.assertIn("prior recommendation", modes["unsupported-reversal"]["suggested_skill_edit"])

        self.assertFalse(modes["overpush"]["actionable"])
        self.assertEqual(modes["overpush"]["count"], 1)

    def test_markdown_report_lists_actionable_guidance(self):
        scorecard = {
            "scenarios": [
                self.scenario("EB-01", "execution-boundary", "Skill behavior", "overpush"),
                self.scenario("EB-02", "execution-boundary", "Ops", "overpush"),
            ]
        }

        tmp, scorecard_path = self.write_scorecard(scorecard)
        with tmp:
            result = self.run_script(scorecard_path, "--format", "markdown")

        self.assertIn("# Reality Slap Failure Patterns", result.stdout)
        self.assertIn("| overpush | 2 | 2 | 1 | yes |", result.stdout)
        self.assertIn("Strengthen when to stop pushing", result.stdout)

    @staticmethod
    def scenario(scenario_id, suite, domain, skill_mode):
        return {
            "scenario_id": scenario_id,
            "suite": suite,
            "domain": domain,
            "individual_scores": {},
            "pair_scores": {
                "baseline": {
                    "total": 4,
                    "observed_failure_mode": "follows-framing",
                },
                "skill": {
                    "total": 6,
                    "observed_failure_mode": skill_mode,
                },
            },
        }


if __name__ == "__main__":
    unittest.main()
