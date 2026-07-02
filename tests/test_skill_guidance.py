import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"


class SkillGuidanceTests(unittest.TestCase):
    def test_execution_requests_must_not_announce_reality_slap(self):
        skill_text = SKILL.read_text(encoding="utf-8")

        self.assertIn("execution or drafting", skill_text)
        self.assertIn("do not announce Reality Slap", skill_text)
        self.assertIn("go straight to the requested deliverable", skill_text)

    def test_execution_requests_must_not_use_reality_checkpoint_labels(self):
        skill_text = SKILL.read_text(encoding="utf-8")

        self.assertIn("Do not use `Reality slap:`", skill_text)
        self.assertIn("Do not use `Reality check:`", skill_text)
        self.assertIn("Use the requested deliverable shape instead", skill_text)

    def test_execution_requests_must_not_foreground_skill_loading(self):
        skill_text = SKILL.read_text(encoding="utf-8")

        self.assertIn("Do not say `Using reality-slap`", skill_text)
        self.assertIn("Do not mention checking the skill or local instructions", skill_text)
        self.assertIn("Apply the skill silently", skill_text)

    def test_self_contained_prompts_must_not_read_local_instruction_files(self):
        skill_text = SKILL.read_text(encoding="utf-8")

        self.assertIn("self-contained prompts", skill_text)
        self.assertIn("Do not read `AGENTS.md`, `RTK.md`, `CLAUDE_CODE_BOOST.md`", skill_text)
        self.assertIn("other local instruction files", skill_text)

    def test_self_contained_legal_privacy_prompts_must_not_browse(self):
        skill_text = SKILL.read_text(encoding="utf-8")

        self.assertIn("legal, privacy, security, or standards", skill_text)
        self.assertIn("do not browse", skill_text)
        self.assertIn("risk and control guidance", skill_text)


if __name__ == "__main__":
    unittest.main()
