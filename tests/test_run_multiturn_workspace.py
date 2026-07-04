import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKSPACE = ROOT / "scripts" / "create_multiturn_workspace.py"
RUNNER = ROOT / "scripts" / "run_multiturn_workspace.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class RunMultiturnWorkspaceTests(unittest.TestCase):
    def create_workspace(self, root):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKSPACE),
                "--input",
                str(BANK),
                "--output-dir",
                str(root),
                "--scenario",
                "SD-02",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_runner(self, workspace, *args, check=True):
        return subprocess.run(
            [sys.executable, str(RUNNER), "--workspace", str(workspace), *args],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def test_dry_run_lists_true_multiturn_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_runner(workspace, "--limit", "1")

            [record] = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(record["mode"], "dry-run")
            self.assertEqual(record["scenario_id"], "SD-02")
            self.assertEqual(record["configuration"], "baseline-positive")
            self.assertEqual(record["turn_count"], 2)
            self.assertTrue(record["requires_persisted_session"])
            self.assertTrue(Path(record["output_path"]).is_absolute())

    def test_execute_resumes_the_session_id_from_the_first_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            self.create_workspace(workspace)
            fake_codex = root / "fake_codex.py"
            fake_codex.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import json",
                        "import sys",
                        "from pathlib import Path",
                        "args = sys.argv[1:]",
                        "log_path = Path(__file__).with_suffix('.jsonl')",
                        "output = Path(args[args.index('--output-last-message') + 1])",
                        "prompt = args[-1]",
                        "is_resume = 'resume' in args",
                        "with log_path.open('a', encoding='utf-8') as log:",
                        "    log.write(json.dumps({'args': args, 'prompt': prompt}) + '\\n')",
                        "if is_resume:",
                        "    output.write_text('turn 2 final bounded support\\n', encoding='utf-8')",
                        "else:",
                        "    output.write_text('turn 1 tiered autonomy\\n', encoding='utf-8')",
                        "    print(json.dumps({'type': 'session.started', 'session_id': 'session-abc'}))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            result = self.run_runner(
                workspace,
                "--scenario",
                "SD-02",
                "--configuration",
                "baseline-positive",
                "--execute",
                "--codex-bin",
                str(fake_codex),
                "--jobs",
                "1",
                "--child-log-dir",
                str(root / "child-logs"),
            )

            [event] = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(event["mode"], "execute")
            self.assertEqual((workspace / "SD-02" / "baseline-positive" / "output.txt").read_text(), "turn 2 final bounded support\n")
            self.assertEqual((workspace / "SD-02" / "baseline-positive" / "turn-01-output.txt").read_text(), "turn 1 tiered autonomy\n")
            self.assertEqual((workspace / "SD-02" / "baseline-positive" / "turn-02-output.txt").read_text(), "turn 2 final bounded support\n")

            transcript = json.loads(
                (workspace / "SD-02" / "baseline-positive" / "transcript.json").read_text()
            )
            self.assertEqual(transcript["session_id"], "session-abc")
            self.assertEqual(
                [turn["assistant_output"] for turn in transcript["turns"]],
                ["turn 1 tiered autonomy\n", "turn 2 final bounded support\n"],
            )

            commands = [
                json.loads(line)
                for line in fake_codex.with_suffix(".jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(commands), 2)
            self.assertNotIn("--ephemeral", commands[0]["args"])
            self.assertIn("resume", commands[1]["args"])
            self.assertIn("session-abc", commands[1]["args"])


if __name__ == "__main__":
    unittest.main()
