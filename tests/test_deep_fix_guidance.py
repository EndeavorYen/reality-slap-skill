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

    def test_goal_contract_locks_outcome_evidence_and_non_goals(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold()

        self.assertIn("durable goal contract", skill_text)
        self.assertIn("user-visible outcome", skill_text)
        self.assertIn("completion evidence", skill_text)
        self.assertIn("non-goals", skill_text)

    def test_hermes_runtime_requires_goal_bootstrap(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8")

        self.assertIn("metadata:\n  hermes:\n    goal_mode: true", skill_text)

    def test_repair_requires_root_cause_before_implementation(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold()

        self.assertIn("root cause before repair", skill_text)
        self.assertIn("reproduce the failure", skill_text)
        self.assertIn("do not present a workaround as a root-cause fix", skill_text)

    def test_phase_checkpoint_detects_drift_and_over_design(self):
        skill_text = " ".join(
            DEEP_FIX_SKILL.read_text(encoding="utf-8").split()
        )

        self.assertIn("Phase Boundary Checkpoint", skill_text)
        self.assertIn("Goal drift", skill_text)
        self.assertIn("Over-design", skill_text)
        self.assertIn("User-visible progress", skill_text)
        self.assertIn("Continue / Correct / Stop", skill_text)
        self.assertIn("not after every paragraph", skill_text)

    def test_execution_prioritizes_high_value_work_and_current_proof(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8")

        self.assertIn("Park minor findings", skill_text)
        self.assertIn("highest-leverage", skill_text)
        self.assertIn("live smoke", skill_text)
        self.assertIn("current evidence", skill_text)

    def test_reality_slap_exposes_a_bounded_execution_integrity_check(self):
        skill_text = REALITY_SLAP_SKILL.read_text(encoding="utf-8")

        self.assertIn("Execution Integrity Check", skill_text)
        self.assertIn("separate execution workflow", skill_text)
        self.assertIn("Do not take over execution", skill_text)

    def test_readme_documents_the_native_hermes_slash_entry(self):
        readme_text = README.read_text(encoding="utf-8")
        normalized_readme = " ".join(readme_text.split())

        self.assertIn("--codex-home ~/.hermes", readme_text)
        self.assertIn("/reload-skills", readme_text)
        self.assertIn("/deep-fix", readme_text)
        self.assertIn("creates or reuses an active Hermes goal", normalized_readme)


if __name__ == "__main__":
    unittest.main()
