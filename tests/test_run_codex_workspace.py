import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKSPACE = ROOT / "scripts" / "create_ab_workspace.py"
RUNNER = ROOT / "scripts" / "run_codex_workspace.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
TRADEOFF_BANK = ROOT / "evals" / "reality-slap-tradeoff-eval-bank.md"


class RunCodexWorkspaceTests(unittest.TestCase):
    def create_workspace(self, root):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKSPACE),
                "--input",
                str(BANK),
                "--output-dir",
                str(root),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def create_tradeoff_workspace(self, root):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKSPACE),
                "--input",
                str(TRADEOFF_BANK),
                "--output-dir",
                str(root),
                "--profile",
                "tradeoff",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_runner(self, workspace, *args):
        return subprocess.run(
            [sys.executable, str(RUNNER), "--workspace", str(workspace), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_runner_unchecked(self, workspace, *args):
        return subprocess.run(
            [sys.executable, str(RUNNER), "--workspace", str(workspace), *args],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_dry_run_lists_all_missing_outputs_without_writing_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_runner(workspace)

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(records), 100)
            self.assertEqual(records[0]["mode"], "dry-run")
            self.assertEqual(records[0]["scenario_id"], "FI-01")
            self.assertEqual(records[0]["configuration"], "baseline-positive")
            self.assertIn("codex", records[0]["command"][0])

            output_path = workspace / "FI-01" / "baseline-positive" / "output.txt"
            self.assertEqual(output_path.read_text(), "")

    def test_dry_run_skips_completed_outputs_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            completed = workspace / "FI-01" / "baseline-positive" / "output.txt"
            completed.write_text("already done", encoding="utf-8")

            result = self.run_runner(workspace)

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(records), 99)
            self.assertNotEqual(
                (records[0]["scenario_id"], records[0]["configuration"]),
                ("FI-01", "baseline-positive"),
            )

    def test_dry_run_does_not_skip_runner_error_marker_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            errored = workspace / "FI-01" / "baseline-positive" / "output.txt"
            errored.write_text(
                "ERROR: child process timed out after 120 seconds\n",
                encoding="utf-8",
            )

            result = self.run_runner(workspace, "--limit", "1")

            [record] = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(
                (record["scenario_id"], record["configuration"]),
                ("FI-01", "baseline-positive"),
            )

    def test_dry_run_can_be_limited_to_a_small_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_runner(workspace, "--limit", "5")

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(records), 5)
            self.assertEqual(
                (records[0]["scenario_id"], records[0]["configuration"]),
                ("FI-01", "baseline-positive"),
            )
            self.assertEqual(
                (records[-1]["scenario_id"], records[-1]["configuration"]),
                ("FI-02", "baseline-positive"),
            )

    def test_dry_run_can_filter_by_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_runner(workspace, "--suite", "pressure-reversal")

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(records), 32)
            self.assertTrue(all(record["suite"] == "pressure-reversal" for record in records))
            self.assertEqual(records[0]["scenario_id"], "PR-01")
            self.assertEqual(records[-1]["scenario_id"], "PR-08")

    def test_dry_run_can_filter_by_tradeoff_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_tradeoff_workspace(workspace)

            result = self.run_runner(workspace, "--suite", "tradeoff-stability")

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(records), 32)
            self.assertTrue(all(record["suite"] == "tradeoff-stability" for record in records))
            self.assertEqual(records[0]["scenario_id"], "TS-01")
            self.assertEqual(records[-1]["scenario_id"], "TS-08")

    def test_dry_run_can_filter_by_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_runner(workspace, "--scenario", "EB-04")

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(records), 4)
            self.assertTrue(all(record["scenario_id"] == "EB-04" for record in records))
            self.assertEqual(
                [record["configuration"] for record in records],
                [
                    "baseline-positive",
                    "baseline-negative",
                    "skill-positive",
                    "skill-negative",
                ],
            )

    def test_dry_run_can_skip_git_repo_check_for_neutral_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_runner(
                workspace,
                "--scenario",
                "EB-04",
                "--cwd",
                "/private/tmp",
                "--skip-git-repo-check",
                "--limit",
                "1",
            )

            [record] = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertIn("--skip-git-repo-check", record["command"])
            self.assertEqual(record["command"][record["command"].index("-C") + 1], "/private/tmp")
            output_arg = record["command"][record["command"].index("--output-last-message") + 1]
            self.assertTrue(Path(output_arg).is_absolute())
            self.assertEqual(Path(output_arg), workspace / "EB-04" / "baseline-positive" / "output.txt")

    def test_dry_run_can_inline_skill_only_for_skill_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            skill = Path(tmp) / "SKILL.md"
            skill.write_text("# Inline Skill\n\nDo not browse in evals.\n", encoding="utf-8")

            result = self.run_runner(
                workspace,
                "--scenario",
                "FI-01",
                "--inline-skill",
                str(skill),
            )

            records = [json.loads(line) for line in result.stdout.splitlines()]
            baseline_prompts = [
                record["command"][-1]
                for record in records
                if record["configuration"].startswith("baseline-")
            ]
            skill_records = [
                record
                for record in records
                if record["configuration"].startswith("skill-")
            ]
            skill_prompts = [record["command"][-1] for record in skill_records]

            self.assertTrue(all("Do not browse in evals." not in prompt for prompt in baseline_prompts))
            self.assertTrue(all("Do not browse in evals." in prompt for prompt in skill_prompts))
            self.assertTrue(all(record["inline_skill_path"] == str(skill) for record in skill_records))

    def test_dry_run_can_omit_full_prompt_from_compact_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            skill = Path(tmp) / "SKILL.md"
            skill.write_text("# Inline Skill\n\nDo not browse in evals.\n", encoding="utf-8")

            result = self.run_runner(
                workspace,
                "--scenario",
                "FI-01",
                "--inline-skill",
                str(skill),
                "--compact-events",
            )

            self.assertNotIn("Do not browse in evals.", result.stdout)
            records = [json.loads(line) for line in result.stdout.splitlines()]
            skill_record = [
                record
                for record in records
                if record["configuration"] == "skill-positive"
            ][0]
            self.assertTrue(skill_record["command"][-1].startswith("<prompt omitted:"))
            self.assertGreater(skill_record["prompt_chars"], 0)

    def test_execute_can_write_child_output_to_log_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            fake_codex = Path(tmp) / "fake_codex.py"
            fake_codex.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import sys",
                        "print('child stdout')",
                        "print('child stderr', file=sys.stderr)",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)
            log_dir = Path(tmp) / "child-logs"

            result = self.run_runner(
                workspace,
                "--scenario",
                "EB-04",
                "--limit",
                "1",
                "--execute",
                "--codex-bin",
                str(fake_codex),
                "--child-log-dir",
                str(log_dir),
            )

            [record] = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertIn("child_log_path", record)
            self.assertNotIn("child stdout", result.stdout)
            self.assertNotIn("child stderr", result.stdout)
            child_log = Path(record["child_log_path"]).read_text(encoding="utf-8")
            self.assertIn("child stdout", child_log)
            self.assertIn("child stderr", child_log)

    def test_execute_times_out_slow_child_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            fake_codex = Path(tmp) / "slow_codex.py"
            fake_codex.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import time",
                        "print('before sleep', flush=True)",
                        "time.sleep(2)",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)
            log_dir = Path(tmp) / "child-logs"

            result = self.run_runner_unchecked(
                workspace,
                "--scenario",
                "EB-04",
                "--limit",
                "1",
                "--execute",
                "--codex-bin",
                str(fake_codex),
                "--child-log-dir",
                str(log_dir),
                "--child-timeout-seconds",
                "0.1",
            )

            self.assertEqual(result.returncode, 124)
            self.assertIn("child run timed out after 0.1 seconds", result.stderr)
            [record] = [json.loads(line) for line in result.stdout.splitlines()]
            child_log = Path(record["child_log_path"]).read_text(encoding="utf-8")
            self.assertIn("ERROR: child process timed out after 0.1 seconds", child_log)
            output = Path(record["output_path"]).read_text(encoding="utf-8")
            self.assertIn("ERROR: child process timed out after 0.1 seconds", output)

    def test_execute_jobs_runs_children_in_parallel(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            fake_codex = Path(tmp) / "timed_codex.py"
            fake_codex.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import json",
                        "import sys",
                        "import time",
                        "from pathlib import Path",
                        "output = Path(sys.argv[sys.argv.index('--output-last-message') + 1])",
                        "start = time.time()",
                        "time.sleep(0.35)",
                        "end = time.time()",
                        "output.write_text('parallel child complete\\n', encoding='utf-8')",
                        "output.with_suffix('.timing.json').write_text(",
                        "    json.dumps({'start': start, 'end': end}),",
                        "    encoding='utf-8',",
                        ")",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            started = time.time()
            result = self.run_runner(
                workspace,
                "--scenario",
                "EB-04",
                "--limit",
                "4",
                "--execute",
                "--codex-bin",
                str(fake_codex),
                "--jobs",
                "2",
            )
            elapsed = time.time() - started

            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(records), 4)
            timings = [
                json.loads(Path(record["output_path"]).with_suffix(".timing.json").read_text())
                for record in records
            ]
            first_end = min(timing["end"] for timing in timings)
            starts_before_first_end = [
                timing for timing in timings if timing["start"] < first_end
            ]
            self.assertGreaterEqual(len(starts_before_first_end), 2)
            self.assertLess(elapsed, 1.25)


if __name__ == "__main__":
    unittest.main()
