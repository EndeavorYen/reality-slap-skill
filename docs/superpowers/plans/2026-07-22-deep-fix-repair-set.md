# Deep Fix Fixed Repair Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the single `$deep-fix` entry from one-problem repair to a frozen, ordered repair set that finishes independent requested items without scope creep.

**Architecture:** Keep the behavior in the existing concise `SKILL.md` contract and UI metadata. Lock scope with a repair ledger, apply the existing root-cause loop per item, admit unlisted changes only through an evidence-based necessity gate, and validate behavior with fresh multi-problem forward tests.

**Tech Stack:** Markdown skill contract, YAML agent metadata, Python `unittest`, fresh Codex forward-test workspaces, repository release scripts.

## Global Constraints

- Keep exactly one user entry: `$deep-fix`.
- Freeze the user-supplied repair set before production edits.
- Process requested items in user order; continue after an independently blocked item.
- Fix unlisted work only when evidence proves it is required for correctness, safety, data integrity, or meaningful verification.
- Do not add modes, flags, dependencies, retries, speculative abstractions, or broad cleanup.
- Run focused proof per item and at most one necessary full suite at the end.

---

### Task 1: Lock the repair-set behavior with failing guidance tests

**Files:**
- Modify: `tests/test_deep_fix_guidance.py`
- Test: `tests/test_deep_fix_guidance.py`

**Interfaces:**
- Consumes: current one-problem wording in `skills/deep-fix/SKILL.md` and `skills/deep-fix/agents/openai.yaml`
- Produces: regression assertions for one repair set, ordered ledger execution, per-item blockers, scope admission, and one canonical entry

- [ ] **Step 1: Replace one-problem assertions with repair-set assertions**

Assert that the skill and UI metadata contain these observable contracts:

```python
self.assertIn("one explicit repair set", skill_text)
self.assertIn("freeze", skill_text)
self.assertIn("user order", skill_text)
self.assertIn("continue to the next independent item", skill_text)
self.assertIn("required dependency", skill_text)
self.assertIn("when necessity is ambiguous", skill_text)
self.assertIn("per item", skill_text)
self.assertIn("one repair set", agent_text)
```

Also assert that the README retains `Use $deep-fix` as the only entry and names
the fixed repair queue without adding `/deep-fix` or a batch flag.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `rtk python3 -m unittest tests.test_deep_fix_guidance`

Expected: FAIL because the current skill and UI metadata require one problem
and do not define the repair ledger or independent-blocker behavior.

- [ ] **Step 3: Commit only after Task 2 turns the test green**

Commit test and contract together as `feat(deep-fix): add bounded repair sets`.

### Task 2: Implement the minimal fixed repair-set contract

**Files:**
- Modify: `skills/deep-fix/SKILL.md`
- Modify: `skills/deep-fix/agents/openai.yaml`
- Modify: `tests/test_deep_fix_guidance.py`

**Interfaces:**
- Consumes: Task 1 assertions
- Produces: one durable repair-set goal, ordered ledger state, per-item root-cause loops, critical-dependency admission, and concise completion output

- [ ] **Step 1: Update frontmatter and durable goal wording**

Change the description and durable constraint from one problem to one explicit
repair set while retaining the smallest-correct-patch and two-no-evidence-loop
constraints.

- [ ] **Step 2: Replace the one-repair contract with a frozen ledger**

Require each ledger item to hold its user-visible outcome and focused proof.
Forbid adding peer items discovered during inspection.

- [ ] **Step 3: Apply the root-cause loop per item**

Require user-order processing, shared-root-cause deduplication, independent
continuation after blockers, and a per-item two-no-evidence stop.

- [ ] **Step 4: Add the evidence-based scope admission gate**

Allow only required dependencies for correctness, security, data integrity, or
meaningful verification. Keep cleanup, upgrades, refactors, and ambiguous work
report-only.

- [ ] **Step 5: Update UI metadata and run focused GREEN verification**

Run: `rtk python3 -m unittest tests.test_deep_fix_guidance`

Expected: all Deep Fix guidance tests pass.

### Task 3: Forward-test multi-problem behavior and publish evidence

**Files:**
- Create: `docs/deep-fix-repair-set-evaluation-2026-07-22.md`
- Create: `docs/deep-fix-repair-set-evaluation-2026-07-22.json`
- Modify: `README.md`
- Modify: `tests/test_deep_fix_guidance.py`

**Interfaces:**
- Consumes: updated skill contract from Task 2 and three fresh isolated fixtures
- Produces: raw scenario results, machine-readable summary, honest README capability claim, and regression assertions for the evidence links

- [ ] **Step 1: Create three disposable raw fixtures**

Create independent-bugs, shared-root-cause, and blocked-then-independent
workspaces outside the repository. Each contains explicit focused tests and at
least one unrelated minor cleanup opportunity.

- [ ] **Step 2: Run fresh-agent forward tests**

Prompt each fresh agent only with the updated skill path, raw workspace, ordered
problem list, and focused command. Do not disclose expected patches or planted
minor files.

- [ ] **Step 3: Score actual artifacts**

For each workspace, run the provided focused tests, inspect changed files, and
record requested outcomes, blocked classification, and unrelated modifications.

- [ ] **Step 4: Write evaluation artifacts and README copy**

State exact scenario counts and limitations. Preserve the prior one-problem
speed benchmark as historical narrow evidence; do not imply the new multi-item
evaluation measured universal speed gains.

- [ ] **Step 5: Add README evidence assertions and run focused tests**

Run: `rtk python3 -m unittest tests.test_deep_fix_guidance`

Expected: tests pass and both new evidence links are present.

### Task 4: Release review, installation, and publish

**Files:**
- Modify only files identified by review findings that are Critical or Important

**Interfaces:**
- Consumes: complete implementation and evaluation artifacts
- Produces: reviewed commit, fresh release evidence, matching global install, and pushed feature branch

- [ ] **Step 1: Run release-quality verification**

Run: `rtk python3 scripts/check_release_ready.py`

Expected: official validators pass, all unit tests pass, install/uninstall smoke
passes, and top-level result is `"ok": true`.

- [ ] **Step 2: Run independent read-only code review**

Review the complete diff against this plan. Fix Critical and Important findings;
leave unrelated Minor suggestions report-only.

- [ ] **Step 3: Install and verify this machine's global Deep Fix copy**

Run: `rtk python3 scripts/install_skill.py install-deep-fix --method copy --force`

Then compare SHA-256 for repository and installed `SKILL.md` plus
`agents/openai.yaml`; both pairs must match.

- [ ] **Step 4: Push the feature branch**

Push `feature/deep-fix-repair-queue` with upstream tracking after confirming the
scoped worktree is clean and the main checkout's `.agent-lab/` remains untouched.
