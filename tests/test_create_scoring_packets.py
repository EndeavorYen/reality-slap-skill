import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKSPACE = ROOT / "scripts" / "create_ab_workspace.py"
CREATE_MULTITURN_WORKSPACE = ROOT / "scripts" / "create_multiturn_workspace.py"
PACKETS = ROOT / "scripts" / "create_scoring_packets.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class CreateScoringPacketsTests(unittest.TestCase):
    def create_workspace(self, workspace):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKSPACE),
                "--input",
                str(BANK),
                "--output-dir",
                str(workspace),
                "--scenario",
                "SD-01",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def create_multiturn_workspace(self, workspace):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_MULTITURN_WORKSPACE),
                "--input",
                str(BANK),
                "--output-dir",
                str(workspace),
                "--scenario",
                "SD-01",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_script(self, workspace, *args):
        return subprocess.run(
            [sys.executable, str(PACKETS), "--workspace", str(workspace), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_jsonl_individual_packets_include_only_completed_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.write_output(workspace, "SD-01", "baseline-positive", "baseline yes")
            self.write_output(workspace, "SD-01", "baseline-negative", "baseline no")
            self.write_output(workspace, "SD-01", "skill-positive", "skill yes")

            result = self.run_script(workspace, "--kind", "individual")

        packets = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(packets), 3)
        self.assertEqual(packets[0]["packet_type"], "individual")
        self.assertEqual(
            packets[0]["score_update_target"],
            {
                "scenario_id": "SD-01",
                "score_type": "individual",
                "configuration": "baseline-positive",
            },
        )
        self.assertIn("GPU", packets[0]["prompt"])
        self.assertEqual(packets[0]["output"], "baseline yes")
        self.assertIn("stance", packets[0]["score_dimensions"])

    def test_jsonl_pair_packets_require_both_framing_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.write_output(workspace, "SD-01", "baseline-positive", "baseline yes")
            self.write_output(workspace, "SD-01", "baseline-negative", "baseline no")
            self.write_output(workspace, "SD-01", "skill-positive", "skill yes")

            result = self.run_script(workspace, "--kind", "pair")

        packets = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(packets), 1)
        packet = packets[0]
        self.assertEqual(packet["packet_type"], "pair")
        self.assertEqual(
            packet["score_update_target"],
            {
                "scenario_id": "SD-01",
                "score_type": "pair",
                "configuration": "baseline",
            },
        )
        self.assertEqual(packet["positive_output"], "baseline yes")
        self.assertEqual(packet["negative_output"], "baseline no")
        self.assertIn("core_recommendation_match", packet["score_dimensions"])

    def test_markdown_packets_are_reviewable(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.write_output(workspace, "SD-01", "baseline-positive", "baseline yes")

            result = self.run_script(
                workspace,
                "--kind",
                "individual",
                "--format",
                "markdown",
            )

        self.assertIn("# Reality Slap Scoring Packets", result.stdout)
        self.assertIn("## SD-01 baseline-positive", result.stdout)
        self.assertIn("baseline yes", result.stdout)

    def test_multiturn_individual_packets_include_turn_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_multiturn_workspace(workspace)
            self.write_output(workspace, "SD-01", "baseline-positive", "baseline final")

            result = self.run_script(workspace, "--kind", "individual")

        [packet] = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(packet["packet_type"], "individual")
        self.assertEqual(packet["output"], "baseline final")
        self.assertIn("turn-01", packet["prompt"])
        self.assertIn("turn-02", packet["prompt"])
        self.assertIn("Final user request", packet["prompt"])

    @staticmethod
    def write_output(workspace, scenario_id, configuration, text):
        path = workspace / scenario_id / configuration / "output.txt"
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
