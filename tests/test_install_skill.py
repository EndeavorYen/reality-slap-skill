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
