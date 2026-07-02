import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_release_ready.py"
QUICK_VALIDATE = Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"


class CheckReleaseReadyTests(unittest.TestCase):
    def run_checker(self, *args):
        return subprocess.run(
            [
                sys.executable,
                str(CHECKER),
                "--quick-validate",
                str(QUICK_VALIDATE),
                *args,
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_dry_run_lists_release_gate_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_checker(
                "--dry-run",
                "--codex-home",
                str(Path(tmp) / "codex-home"),
            )

        report = json.loads(result.stdout)
        names = [command["name"] for command in report["commands"]]
        self.assertTrue(report["ok"])
        self.assertEqual(report["mode"], "install-release")
        self.assertIn("official-skill-validator", names)
        self.assertIn("unit-tests", names)
        self.assertIn("pilot-eval-bank", names)
        self.assertIn("full-eval-bank", names)
        self.assertIn("full-eval-design", names)
        self.assertIn("copy-install", names)
        self.assertIn("installed-skill-validator", names)
        self.assertIn("copy-uninstall", names)

    def test_dry_run_can_skip_unit_tests(self):
        result = self.run_checker("--dry-run", "--skip-tests")

        report = json.loads(result.stdout)
        names = [command["name"] for command in report["commands"]]
        self.assertNotIn("unit-tests", names)
        self.assertIn("official-skill-validator", names)

    def test_dry_run_can_include_full_eval_completion_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "full-workspace"
            result = self.run_checker(
                "--dry-run",
                "--full-eval-workspace",
                str(workspace),
            )

        report = json.loads(result.stdout)
        names = [command["name"] for command in report["commands"]]
        self.assertEqual(report["mode"], "score-release")
        self.assertIn("full-eval-goal-completion", names)
        command = [
            command
            for command in report["commands"]
            if command["name"] == "full-eval-goal-completion"
        ][0]["command"]
        self.assertIn(str(workspace), command)

    def test_release_gate_inspects_runtime_install_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_checker(
                "--skip-tests",
                "--codex-home",
                str(Path(tmp) / "codex-home"),
            )

        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        names = [result["name"] for result in report["results"]]
        self.assertIn("installed-runtime-layout", names)
        layout = [
            result
            for result in report["results"]
            if result["name"] == "installed-runtime-layout"
        ][0]
        self.assertTrue(layout["ok"])
        layout_stdout = json.loads(layout["stdout"])
        self.assertEqual(layout_stdout["missing"], [])
        self.assertEqual(layout_stdout["unexpected_top_level"], [])


if __name__ == "__main__":
    unittest.main()
