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

    def test_install_command_rejects_a_second_deep_fix_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"

            result = self.run_installer_raw(
                codex_home,
                "install-command",
                "--name",
                "deep-fix",
                "--force",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Use $deep-fix as the single entry", result.stderr)
            self.assertFalse((codex_home / "prompts" / "deep-fix.md").exists())

    def test_install_deep_fix_checks_legacy_entry_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            legacy_prompt = codex_home / "prompts" / "deep-fix.md"
            legacy_prompt.parent.mkdir(parents=True)
            legacy_prompt.write_text("legacy\n")

            result = self.run_installer_raw(codex_home, "install-deep-fix")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pass --force to remove it", result.stderr)
            self.assertFalse((codex_home / "skills" / "deep-fix").exists())
            self.assertEqual(legacy_prompt.read_text(), "legacy\n")

    def test_install_deep_fix_installs_one_skill_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"

            result = self.run_installer(
                codex_home,
                "install-deep-fix",
                "--method",
                "copy",
                "--force",
            )

            deep_fix = codex_home / "skills" / "deep-fix"
            self.assertIn("installed deep-fix", result.stdout)
            self.assertFalse((codex_home / "skills" / "reality-slap").exists())
            self.assertTrue((deep_fix / "SKILL.md").exists())
            self.assertTrue((deep_fix / "agents" / "openai.yaml").exists())
            self.assertTrue((deep_fix / "LICENSE").exists())
            self.assertFalse((codex_home / "prompts" / "deep-fix.md").exists())

    def test_force_install_deep_fix_does_not_touch_reality_slap(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            dependency_skill = (
                codex_home / "skills" / "reality-slap" / "SKILL.md"
            )
            dependency_skill.parent.mkdir(parents=True)
            dependency_skill.write_text("stale reality slap\n")

            self.run_installer(
                codex_home,
                "install-deep-fix",
                "--method",
                "copy",
                "--force",
            )

            self.assertEqual(dependency_skill.read_text(), "stale reality slap\n")

    def test_uninstall_deep_fix_preserves_reality_slap_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            dependency_skill = codex_home / "skills" / "reality-slap" / "SKILL.md"
            dependency_skill.parent.mkdir(parents=True)
            dependency_skill.write_text("keep me\n")
            self.run_installer(
                codex_home,
                "install-deep-fix",
                "--method",
                "copy",
                "--force",
            )

            result = self.run_installer(
                codex_home,
                "uninstall-deep-fix",
                "--force",
            )

            self.assertIn("uninstalled deep-fix", result.stdout)
            self.assertEqual(dependency_skill.read_text(), "keep me\n")
            self.assertFalse((codex_home / "skills" / "deep-fix").exists())
            self.assertFalse((codex_home / "prompts" / "deep-fix.md").exists())

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
