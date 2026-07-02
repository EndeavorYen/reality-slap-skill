import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_skill.py"


class InstallSkillTests(unittest.TestCase):
    def run_installer(self, codex_home, *args):
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                *args,
                "--codex-home",
                str(codex_home),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_installer_raw(self, codex_home, *args):
        return subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                *args,
                "--codex-home",
                str(codex_home),
            ],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_copy_install_writes_runtime_skill_files_only_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"

            result = self.run_installer(
                codex_home,
                "install",
                "--method",
                "copy",
                "--force",
            )

            destination = codex_home / "skills" / "reality-slap"
            self.assertIn("installed reality-slap", result.stdout)
            self.assertTrue((destination / "SKILL.md").exists())
            self.assertTrue((destination / "agents" / "openai.yaml").exists())
            self.assertTrue((destination / "LICENSE").exists())
            self.assertFalse((destination / "tests").exists())
            self.assertFalse((codex_home / "prompts" / "reality-slap.md").exists())

    def test_install_command_writes_custom_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"

            result = self.run_installer(codex_home, "install-command", "--force")

            prompt_file = codex_home / "prompts" / "reality-slap.md"
            prompt_text = prompt_file.read_text()
            self.assertIn("installed reality-slap command", result.stdout)
            self.assertIn("description:", prompt_text)
            self.assertIn("argument-hint:", prompt_text)
            self.assertIn("Use $reality-slap", prompt_text)
            self.assertIn("$ARGUMENTS", prompt_text)

    def test_install_command_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            prompt_file = codex_home / "prompts" / "reality-slap.md"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text("keep me\n")

            result = self.run_installer_raw(codex_home, "install-command")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pass --force", result.stderr)
            self.assertEqual(prompt_file.read_text(), "keep me\n")

    def test_uninstall_command_removes_custom_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            self.run_installer(codex_home, "install-command", "--force")

            result = self.run_installer(codex_home, "uninstall-command", "--force")

            prompt_file = codex_home / "prompts" / "reality-slap.md"
            self.assertIn("uninstalled reality-slap command", result.stdout)
            self.assertFalse(prompt_file.exists())

    def test_copy_install_can_include_eval_tools_for_release_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"

            self.run_installer(
                codex_home,
                "install",
                "--method",
                "copy",
                "--include-eval-tools",
                "--force",
            )

            destination = codex_home / "skills" / "reality-slap"
            self.assertTrue((destination / "evals" / "scoring-rubric.md").exists())
            self.assertTrue((destination / "scripts" / "validate_eval_bank.py").exists())
            self.assertTrue((destination / "tests" / "test_skill_guidance.py").exists())

    def test_link_install_points_to_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"

            self.run_installer(
                codex_home,
                "install",
                "--method",
                "link",
                "--force",
            )

            destination = codex_home / "skills" / "reality-slap"
            self.assertTrue(destination.is_symlink())
            self.assertEqual(destination.resolve(), ROOT)

    def test_status_and_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            self.run_installer(
                codex_home,
                "install",
                "--method",
                "copy",
                "--force",
            )

            status = self.run_installer(codex_home, "status")
            self.assertIn("reality-slap: directory", status.stdout)

            self.run_installer(codex_home, "uninstall", "--force")

            destination = codex_home / "skills" / "reality-slap"
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
