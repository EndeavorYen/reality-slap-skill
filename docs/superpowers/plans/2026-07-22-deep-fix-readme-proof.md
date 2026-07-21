# Deep Fix README Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote Deep Fix's verified bounded fast path in the README with an eye-catching proof strip and an evidence-backed detailed section.

**Architecture:** Keep Reality Slap as the README hero, then add a compact Deep Fix proof strip that links readers to the existing companion section. Expand that section using only committed A/B data and lock the public claims with README guidance tests.

**Tech Stack:** Markdown, Python `unittest`, repository release validator

## Global Constraints

- Keep one canonical invocation: `Use $deep-fix <problem>`.
- Show `38% faster`, `52% fewer input tokens`, `3/3 correct one-file repairs`, and `0 file changes when blocked`.
- Identify the benchmark as one controlled `gpt-5.6-sol`, `high` fixture with three paired runs.
- Do not claim universal speedups or validation of multi-module and flaky failures.
- Link the human-readable report and machine-readable JSON result.

---

### Task 1: Lock the README proof contract

**Files:**
- Modify: `tests/test_deep_fix_guidance.py`
- Test: `tests/test_deep_fix_guidance.py`

**Interfaces:**
- Consumes: `README`, the existing `Path` constant for `README.md`
- Produces: regression assertions for the Deep Fix proof strip, evidence links, and claim boundary

- [x] **Step 1: Write the failing README assertions**

Add this test to `DeepFixGuidanceTests`:

```python
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
```

- [x] **Step 2: Run the focused test and verify it fails**

Run:

```bash
rtk python3 -m unittest tests.test_deep_fix_guidance
```

Expected: FAIL because the new proof-strip copy and evidence links are absent from `README.md`.

### Task 2: Add the proof strip and detailed benchmark

**Files:**
- Modify: `README.md`
- Test: `tests/test_deep_fix_guidance.py`

**Interfaces:**
- Consumes: the committed evaluation values in `docs/deep-fix-sol-high-evaluation-2026-07-21.{md,json}`
- Produces: a scan-friendly README proof strip and a detailed Deep Fix evidence section

- [x] **Step 1: Add the hero-adjacent proof strip**

Insert after the hero positioning line:

```markdown
## Deep repair without deep wandering.

Deep Fix gives long-running repairs a bounded fast path: one problem, three action groups, then stop.

| **38% faster** | **52% fewer input tokens** | **3/3 correct one-file repairs** | **0 file changes when blocked** |
|---|---|---|---|
| Median wall time | Median input context | Same correct minimal patch | Exact blocker, no fake fix |

_Controlled `gpt-5.6-sol`, `high` fixture; three paired runs. [See the evidence](#deep-fix-companion)._
```

- [x] **Step 2: Replace the Deep Fix explanation with workflow and results**

Keep the install and invocation commands, then add:

```markdown
The straight-line path uses three action groups:

1. inspect the owning path and run the provided focused reproduction;
2. make the smallest root-cause production patch;
3. rerun the same proof, inspect the diff, and stop.

| Controlled Sol high median | Baseline | Deep Fix | Change |
|---|---:|---:|---:|
| Wall time | 70.7s | 43.7s | **38.1% faster** |
| Input tokens | 274,683 | 132,935 | **51.6% fewer** |
| Correct one-file repair | 3/3 | 3/3 | Same correctness |
```

Follow the table with the blocked-path result, the controlled-fixture limitation,
and links to both evaluation artifacts.

- [x] **Step 3: Run the focused test and verify it passes**

Run:

```bash
rtk python3 -m unittest tests.test_deep_fix_guidance
```

Expected: 11 tests pass.

### Task 3: Release verification and review

**Files:**
- Verify: `README.md`
- Verify: `tests/test_deep_fix_guidance.py`

**Interfaces:**
- Consumes: the completed README and guidance test changes
- Produces: a release-gate result and a reviewable Git commit

- [x] **Step 1: Run the complete release gate**

Run:

```bash
rtk python3 scripts/check_release_ready.py
```

Expected: `ok: true` and 140 unit tests passing.

- [x] **Step 2: Review claims and diff hygiene**

Run:

```bash
rtk git diff --check
rtk git diff -- README.md tests/test_deep_fix_guidance.py
```

Expected: no whitespace errors; every headline number matches the committed evaluation report; `.agent-lab/` remains untouched.

- [x] **Step 3: Commit the README proof update**

Run:

```bash
rtk git add README.md tests/test_deep_fix_guidance.py docs/superpowers/plans/2026-07-22-deep-fix-readme-proof.md
rtk git commit -m "docs: feature deep-fix benchmark proof"
```

Expected: one commit containing the README, its regression test, and this implementation plan.
