import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEEP_FIX_SKILL = ROOT / "skills" / "deep-fix" / "SKILL.md"
REALITY_SLAP_SKILL = ROOT / "SKILL.md"
DEEP_FIX_AGENT = ROOT / "skills" / "deep-fix" / "agents" / "openai.yaml"
README = ROOT / "README.md"
REPAIR_SET_EVAL = ROOT / "docs" / "deep-fix-repair-set-evaluation-2026-07-22.json"


class DeepFixGuidanceTests(unittest.TestCase):
    def test_companion_skill_has_explicit_only_runtime_metadata(self):
        self.assertTrue(DEEP_FIX_SKILL.exists())
        self.assertTrue(DEEP_FIX_AGENT.exists())

        agent_text = DEEP_FIX_AGENT.read_text(encoding="utf-8")
        self.assertIn('display_name: "Deep Fix"', agent_text)
        self.assertIn("allow_implicit_invocation: false", agent_text)
        self.assertIn("one repair set with the smallest correct patches", agent_text)

    def test_repair_contract_freezes_one_explicit_set_in_user_order(self):
        skill_text = " ".join(
            DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold().split()
        )

        self.assertIn("one explicit repair set", skill_text)
        self.assertIn("freeze an ordered repair ledger", skill_text)
        self.assertIn("process ledger items in user order", skill_text)
        self.assertIn("smallest correct patch", skill_text)
        self.assertIn("report unrelated findings without fixing them", skill_text)

    def test_repair_set_continues_after_independent_blocker(self):
        skill_text = " ".join(
            DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold().split()
        )

        self.assertIn("continue to the next independent item", skill_text)
        self.assertIn("two-no-evidence stop applies per item", skill_text)
        self.assertIn("same prerequisite blocks the remaining ledger", skill_text)

    def test_unlisted_work_requires_proven_scope_admission(self):
        skill_text = " ".join(
            DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold().split()
        )

        self.assertIn("required dependency", skill_text)
        self.assertIn("omitting it would make the current named outcome incorrect", skill_text)
        self.assertIn(
            "directly introduce or worsen a security or data-loss defect in that outcome",
            skill_text,
        )
        self.assertIn("make that outcome's completion proof meaningless", skill_text)
        self.assertIn("when necessity is ambiguous, do not fix it", skill_text)
        self.assertIn("architectural redesign", skill_text)

    def test_not_reproduced_item_is_not_patched_speculatively(self):
        skill_text = " ".join(
            DEEP_FIX_SKILL.read_text(encoding="utf-8").casefold().split()
        )

        self.assertIn("if the evidence does not reproduce the current item", skill_text)
        self.assertIn("make no production change", skill_text)
        self.assertIn("mark it `not-reproduced`", skill_text)
        self.assertIn("continue to the next independent item", skill_text)

    def test_runtime_neutral_metadata_requires_a_durable_goal(self):
        skill_text = DEEP_FIX_SKILL.read_text(encoding="utf-8")

        self.assertIn(
            "metadata:\n  execution:\n    durable_goal:\n      required: true",
            skill_text,
        )
        self.assertNotIn("metadata:\n  hermes:", skill_text)
        normalized = " ".join(skill_text.split())
        self.assertIn("Fix one explicit repair set with the smallest correct patches", normalized)
        self.assertIn("Stop an item after two consecutive repair loops add no new evidence", normalized)

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
        self.assertIn("current ledger item", skill_text)

    def test_execution_uses_focused_verification_without_default_full_suite(self):
        skill_text = " ".join(DEEP_FIX_SKILL.read_text(encoding="utf-8").split())

        self.assertIn("Reuse an existing focused reproduction", skill_text)
        self.assertIn("once before and once after the patch", skill_text)
        self.assertIn("Do not repeat an unchanged passing check", skill_text)
        self.assertIn("Run the full test suite only when it is necessary", skill_text)

    def test_single_entry_does_not_stack_overlapping_workflow_skills(self):
        skill_text = " ".join(DEEP_FIX_SKILL.read_text(encoding="utf-8").split())

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

        self.assertIn("Use $deep-fix <problem or ordered problem list>", readme_text)
        self.assertIn("fixed repair queue", readme_text.casefold())
        self.assertNotIn("/prompts:deep-fix", readme_text)
        self.assertNotIn("/deep-fix Repair", readme_text)
        self.assertNotIn("--batch", readme_text)

    def test_readme_surfaces_deep_fix_benchmark_without_overclaiming(self):
        readme_text = README.read_text(encoding="utf-8")

        for proof in (
            "Deep repair without deep wandering.",
            "38% faster",
            "52% fewer input tokens",
            "3/3 correct one-file repairs",
            "0 file changes when blocked",
            "three action groups",
            "controlled fixture",
        ):
            self.assertIn(proof, readme_text)

        self.assertIn(
            "docs/deep-fix-sol-high-evaluation-2026-07-21.md",
            readme_text,
        )
        self.assertIn(
            "docs/deep-fix-sol-high-evaluation-2026-07-21.json",
            readme_text,
        )

    def test_readme_surfaces_repair_set_forward_test_without_overclaiming(self):
        readme_text = README.read_text(encoding="utf-8")

        for proof in (
            "3/3 repair-set scenarios",
            "8/8 fixable outcomes",
            "1/1 exact blocker",
            "0/3 planted minor changes",
            "fresh-agent behavioral forward test",
            "compact Python fixtures",
        ):
            self.assertIn(proof, readme_text)

        self.assertIn(
            "docs/deep-fix-repair-set-evaluation-2026-07-22.md",
            readme_text,
        )
        self.assertIn(
            "docs/deep-fix-repair-set-evaluation-2026-07-22.json",
            readme_text,
        )

        evaluation = json.loads(REPAIR_SET_EVAL.read_text(encoding="utf-8"))
        self.assertEqual(evaluation["summary"]["scenarios_passed"], 3)
        self.assertEqual(evaluation["summary"]["fixable_outcomes_fixed"], 8)
        self.assertEqual(evaluation["summary"]["exact_blockers_reported"], 1)
        self.assertEqual(evaluation["summary"]["planted_minor_changes"], 0)
        self.assertEqual(len(evaluation["scenarios"]), 3)
        for scenario in evaluation["scenarios"]:
            self.assertIn("exact_prompt", scenario)
            self.assertIn("focused_commands", scenario)
            self.assertIn("agent_result", scenario)
            self.assertIn("review_evidence", scenario)


if __name__ == "__main__":
    unittest.main()
