import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_skill_iteration_log.py"


def scenario(scenario_id, suite, domain, failure_mode):
    return {
        "scenario_id": scenario_id,
        "suite": suite,
        "domain": domain,
        "pair_scores": {
            "baseline": {"total": 7, "observed_failure_mode": "none"},
            "skill": {"total": 8, "observed_failure_mode": failure_mode},
        },
    }


class CreateSkillIterationLogTests(unittest.TestCase):
    def run_script(self, *args, check=True):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def write_scorecard(self, path, scenarios):
        path.write_text(json.dumps({"scenarios": scenarios}), encoding="utf-8")

    def test_writes_iteration_log_from_actionable_failure_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard = root / "scorecard.json"
            output = root / "iteration-log.json"
            self.write_scorecard(
                scorecard,
                [
                    scenario("FI-01", "frame-invariance", "Product roadmap", "overpush"),
                    scenario("FI-02", "frame-invariance", "Architecture", "overpush"),
                    scenario("FI-03", "frame-invariance", "Security", "overpush"),
                    scenario("PR-01", "pressure-reversal", "Product roadmap", "follows-framing"),
                    scenario("PR-02", "pressure-reversal", "Architecture", "follows-framing"),
                    scenario("EB-01", "execution-boundary", "Ops", "vague-boundary"),
                    scenario("EB-02", "execution-boundary", "Security", "vague-boundary"),
                ],
            )

            result = self.run_script(
                "--scorecard",
                str(scorecard),
                "--output",
                str(output),
            )

            written = json.loads(output.read_text())

        summary = json.loads(result.stdout)
        self.assertEqual(summary["skill_update_count"], 3)
        self.assertEqual(summary["output"], str(output))
        self.assertEqual(written["source_scorecard"], str(scorecard))
        self.assertEqual(
            [update["failure_mode"] for update in written["skill_updates"]],
            ["overpush", "follows-framing", "vague-boundary"],
        )
        self.assertTrue(all(update["file"] == "SKILL.md" for update in written["skill_updates"]))
        self.assertIn("Strengthen", written["skill_updates"][0]["change"])
        self.assertIn("scenario_ids", written["skill_updates"][0])
        self.assertFalse(written["skill_updates"][0]["applied"])
        self.assertEqual(written["skill_updates"][0]["evidence"], "")

    def test_fails_without_three_actionable_patterns_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scorecard = root / "scorecard.json"
            output = root / "iteration-log.json"
            self.write_scorecard(
                scorecard,
                [
                    scenario("FI-01", "frame-invariance", "Product roadmap", "overpush"),
                    scenario("FI-02", "frame-invariance", "Architecture", "overpush"),
                    scenario("FI-03", "frame-invariance", "Security", "overpush"),
                ],
            )

            result = self.run_script(
                "--scorecard",
                str(scorecard),
                "--output",
                str(output),
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("fewer than 3 actionable skill failure patterns", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
