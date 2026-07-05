import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_multiturn_workspace.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class CreateMultiturnWorkspaceTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_creates_true_multiturn_runs_with_separate_pressure_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "multiturn-workspace"

            self.run_script(
                "--input",
                str(BANK),
                "--output-dir",
                str(out_dir),
                "--scenario",
                "SD-02",
                "--scenario",
                "SD-11",
            )

            manifest = json.loads((out_dir / "manifest.json").read_text())
            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]

            self.assertEqual(manifest["mode"], "true_multi_turn")
            self.assertEqual(manifest["scenario_count"], 2)
            self.assertEqual(manifest["run_count"], 8)
            self.assertEqual(manifest["turn_count_per_run"], 2)
            self.assertEqual(len(records), 8)

            record = records[0]
            self.assertEqual(record["scenario_id"], "SD-02")
            self.assertEqual(record["configuration"], "baseline-positive")
            self.assertEqual(record["turn_count"], 2)
            self.assertTrue((out_dir / record["turns_path"]).exists())
            self.assertTrue((out_dir / record["output_path"]).exists())

            turns = [
                json.loads(line)
                for line in (out_dir / record["turns_path"]).read_text().splitlines()
            ]
            self.assertEqual([turn["turn_id"] for turn in turns], ["turn-01", "turn-02"])
            self.assertIn("AI coding agent", turns[0]["prompt"])
            self.assertIn("What do you recommend?", turns[0]["prompt"])
            self.assertNotIn("boundary you would not cross", turns[0]["prompt"])
            self.assertNotIn("what evidence would change your judgment", turns[0]["prompt"])
            self.assertNotIn("auto-merge", turns[0]["prompt"])
            self.assertIn("auto-merge", turns[1]["prompt"])
            self.assertEqual((out_dir / record["output_path"]).read_text(), "")

    def test_skill_instruction_is_not_reinjected_on_pressure_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "multiturn-workspace"

            self.run_script(
                "--input",
                str(BANK),
                "--output-dir",
                str(out_dir),
                "--scenario",
                "SD-02",
            )

            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]
            skill_record = [
                record
                for record in records
                if record["configuration"] == "skill-positive"
            ][0]
            turns = [
                json.loads(line)
                for line in (out_dir / skill_record["turns_path"]).read_text().splitlines()
            ]

            self.assertIn("Use $reality-slap", turns[0]["prompt"])
            self.assertNotIn("Use $reality-slap", turns[1]["prompt"])

    def test_can_insert_neutral_decay_turns_between_context_and_pressure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "multiturn-workspace"

            self.run_script(
                "--input",
                str(BANK),
                "--output-dir",
                str(out_dir),
                "--scenario",
                "SD-02",
                "--decay-turns",
                "1",
            )

            manifest = json.loads((out_dir / "manifest.json").read_text())
            records = [
                json.loads(line)
                for line in (out_dir / "records.jsonl").read_text().splitlines()
            ]
            self.assertEqual(manifest["turn_count_per_run"], 3)

            skill_record = [
                record
                for record in records
                if record["configuration"] == "skill-positive"
            ][0]
            self.assertEqual(skill_record["turn_count"], 3)
            turns = [
                json.loads(line)
                for line in (out_dir / skill_record["turns_path"]).read_text().splitlines()
            ]

            self.assertEqual(
                [turn["turn_id"] for turn in turns],
                ["turn-01", "turn-02", "turn-03"],
            )
            self.assertEqual(
                [turn["kind"] for turn in turns],
                ["context", "decay", "pressure"],
            )
            self.assertIn("neutral coordination update", turns[1]["prompt"])
            self.assertNotIn("recommendation boundary", turns[1]["prompt"])
            self.assertNotIn("AI automation governance", turns[1]["prompt"])
            self.assertNotIn("auto-merge", turns[1]["prompt"])
            self.assertIn("auto-merge", turns[2]["prompt"])
            self.assertNotIn("Use $reality-slap", turns[1]["prompt"])
            self.assertNotIn("Use $reality-slap", turns[2]["prompt"])


if __name__ == "__main__":
    unittest.main()
