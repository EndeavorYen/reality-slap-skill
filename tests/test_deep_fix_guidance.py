import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEEP_FIX_SKILL = ROOT / "skills" / "deep-fix" / "SKILL.md"
REALITY_SLAP_SKILL = ROOT / "SKILL.md"
DEEP_FIX_AGENT = ROOT / "skills" / "deep-fix" / "agents" / "openai.yaml"
README = ROOT / "README.md"


class DeepFixGuidanceTests(unittest.TestCase):
    def test_companion_skill_has_explicit_only_runtime_metadata(self):
        self.assertTrue(DEEP_FIX_SKILL.exists())
        self.assertTrue(DEEP_FIX_AGENT.exists())

        agent_text = DEEP_FIX_AGENT.read_text(encoding="utf-8")
        self.assertIn('display_name: "Deep Fix"', agent_text)
        self.assertIn("allow_implicit_invocation: false", agent_text)
        self.assertIn("one problem with the smallest correct patch", agent_text)

    def test_repair_contract_locks_one_problem_and_smallest_patch(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold()

        self.assertIn("fix one user-visible problem", skill_text)
        self.assertIn("smallest correct patch", skill_text)
        self.assertIn("report unrelated findings without fixing them", skill_text)

    def test_runtime_neutral_metadata_requires_a_durable_goal(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8")

        self.assertIn(
            "metadata:\n  execution:\n    durable_goal:\n      required: true",
            skill_text,
        )
        self.assertNotIn("metadata:\n  hermes:", skill_text)
        normalized = " ".join(skill_text.split())
        self.assertIn("Fix one user-visible problem with the smallest correct patch", normalized)
        self.assertIn("Stop after two consecutive repair loops add no new evidence", normalized)

    def test_repair_requires_root_cause_before_implementation(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold()

        self.assertIn("root cause before repair", skill_text)
        self.assertIn("existing focused reproduction", skill_text)
        self.assertIn("do not present a workaround as a root-cause fix", skill_text)

    def test_checkpoint_is_exception_only_and_stops_after_two_no_evidence_loops(self):
        skill_text = " ".join(
            DEEP_FIX_SKILL.read_text(encoding="utf-8").split()
        )

        self.assertIn("Do not emit a checkpoint on a straight-line repair", skill_text)
        self.assertIn("before entering a second repair loop", skill_text)
        self.assertIn(
            "Progress: <new evidence or effective change> | Scope: OK / Drift | "
            "Decision: Continue / Stop | Next: <one action>",
            skill_text,
        )
        self.assertIn("two consecutive repair loops add no new evidence", skill_text)

    def test_execution_uses_focused_verification_without_default_full_suite(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8")

        self.assertIn("Reuse an existing focused reproduction", skill_text)
        self.assertIn("once before and once after the patch", skill_text)
        self.assertIn("Do not repeat an unchanged passing check", skill_text)
        self.assertIn("Run the full test suite only when it is necessary", skill_text)

    def test_single_entry_does_not_stack_overlapping_workflow_skills(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8")

        self.assertIn("Do not load overlapping repair workflow skills", skill_text)
        self.assertIn("unless the user explicitly invoked them", skill_text)

    def test_straight_line_repair_batches_tool_round_trips(self):
        skill_text = " ".join(DEEP_FIX_SKILL.read_text(encoding="utf-8").split())

        self.assertIn("three action groups", skill_text)
        self.assertIn("Use the provided reproduction command exactly", skill_text)
        self.assertIn("Do not enumerate unrelated files", skill_text)
        self.assertIn("Do not spend a repair loop cleaning harmless generated artifacts", skill_text)

    def test_reality_slap_exposes_a_bounded_execution_integrity_check(self):
        skill_text = REALITY_SLAP_SKILL.read_text(encoding="utf-8")

        self.assertIn("Execution Integrity Check", skill_text)
        self.assertIn("separate execution workflow", skill_text)
        self.assertIn("Do not take over execution", skill_text)

    def test_readme_documents_one_canonical_entry(self):
        readme_text = README.read_text(encoding="utf-8")

        self.assertIn("Use $deep-fix <problem>", readme_text)
        self.assertNotIn("/prompts:deep-fix", readme_text)
        self.assertNotIn("/deep-fix Repair", readme_text)


if __name__ == "__main__":
    unittest.main()
