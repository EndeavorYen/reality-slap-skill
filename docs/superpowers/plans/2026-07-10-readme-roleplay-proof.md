# README Roleplay Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the same-model roleplay experiment in the repository and reshape the README into a faster, product-led path for first-time users.

**Architecture:** Keep the complete methodology in a dedicated eval report, store headline values in `evals/evals.json`, and let the README consume only a compact proof summary. Add one static SVG proof card using the repository's existing visual language; do not commit raw model transcripts or temporary workspaces.

**Tech Stack:** Markdown, JSON, SVG, Python repository validation scripts, Git.

## Global Constraints

- The stance-drift benchmark remains the primary product proof.
- The roleplay experiment may claim modest boundary-completeness improvement, not material harmful-consensus reduction.
- The README targets first-time users and keeps Quick Start before deep methodology.
- Do not modify or stage `.agent-lab/`.
- Do not add dependencies or raw session logs.

---

### Task 1: Commit the experiment as repository evidence

**Files:**
- Create: `evals/same-model-roleplay-ab-2026-07-10.md`
- Modify: `evals/evals.json`

**Interfaces:**
- Consumes: verified metrics from `/private/tmp/reality-slap-role-ab-20260710`.
- Produces: one human-readable report and `latest_same_model_roleplay_ab` metadata for README claims.

- [ ] **Step 1: Add the complete report**

Write a summary-first report containing:

```markdown
# Same-Model Roleplay A/B

> **TL;DR** — In this 12-case pilot, Reality Slap modestly improved boundary completeness but did not reduce harmful consensus because neither arm produced a harmful-consensus event.

## Result
| Metric | Naive consensus | + Reality Slap |
| Semantic decisions judged correct | 24/24 | 24/24 |
| Harmful compromise flags | 0/24 | 0/24 |
| Mean quality | 13.833/14 | 13.958/14 |
| Complete critical boundaries | 20/24 | 23/24 |
```

Document the two A/B layers, the three simulated roles, paired randomization, blinded judging, success threshold, observed role convergence, prompt-size cost, limitations, and links to the primary papers cited during analysis.

- [ ] **Step 2: Add machine-readable metadata**

Add this top-level object to `evals/evals.json` without changing existing release evidence:

```json
"latest_same_model_roleplay_ab": {
  "date": "2026-07-10",
  "model": "gpt-5.6-sol",
  "reasoning_effort": "high",
  "design": "single-invocation same-model three-role simulation",
  "scenario_count": 12,
  "meeting_outputs": 48,
  "blinded_judgment_records": 96,
  "naive_vs_skill": {
    "semantic_decision_correct": {"naive": "24/24", "skill": "24/24"},
    "harmful_compromise_flags": {"naive": "0/24", "skill": "0/24"},
    "mean_quality": {"naive": 13.833, "skill": 13.958, "scale_max": 14},
    "complete_critical_boundaries": {"naive": "20/24", "skill": "23/24"},
    "mean_round_two_stance_diversity": {"naive": 1.0, "skill": 1.0},
    "unanimous_final_decisions": {"naive": "11/12", "skill": "12/12"},
    "mean_prompt_characters": {"naive": 2101, "skill": 13533},
    "mean_elapsed_seconds": {"naive": 23.456, "skill": 24.497}
  },
  "conclusion": "modest boundary-completeness improvement; no demonstrated reduction in harmful consensus",
  "claim_boundary": "This pilot does not establish that Reality Slap creates independent reasoning diversity or eliminates same-model compromise."
}
```

- [ ] **Step 3: Validate the evidence files**

Run:

```bash
python3 -m json.tool evals/evals.json >/dev/null
python3 scripts/validate_eval_bank.py --input evals/reality-slap-eval-bank.md --profile stance-drift
```

Expected: valid JSON and `Eval bank is valid: 12 scenarios (profile stance-drift)`.

- [ ] **Step 4: Commit the evidence**

```bash
git add evals/evals.json evals/same-model-roleplay-ab-2026-07-10.md
git commit -m "docs: publish same-model roleplay evaluation"
```

### Task 2: Add the visual proof card

**Files:**
- Create: `assets/same-model-roleplay-result.svg`

**Interfaces:**
- Consumes: headline values in `latest_same_model_roleplay_ab`.
- Produces: a 900px-wide README image with equivalent adjacent Markdown text.

- [ ] **Step 1: Create the SVG**

Use a `900 × 420` view box, black background, warm-white panels, teal accent, and these exact labels:

```text
SAME MODEL. THREE ROLES. ONE HONEST RESULT.
Decision quality       13.833 → 13.958 / 14
Critical boundaries   20/24 → 23/24
Harmful compromise    0/24 → 0/24
VERDICT: Better boundaries. No proof of less compromise yet.
```

Do not use gradients or encode the small quality delta as a visually large bar.

- [ ] **Step 2: Render and inspect the SVG**

Render the SVG to PNG using an available repository or system renderer, then inspect it for clipping, contrast, and README-width legibility.

Expected: all labels fit inside the view box and the verdict is readable at a 900px render.

- [ ] **Step 3: Commit the asset**

```bash
git add assets/same-model-roleplay-result.svg
git commit -m "docs: add same-model roleplay proof card"
```

### Task 3: Rewrite the README for activation

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: both benchmark SVGs, the roleplay report, and committed metadata.
- Produces: the public product entry point.

- [ ] **Step 1: Replace the opening structure**

Use this order:

```markdown
# Reality Slap
badges
TL;DR
hero image
one-line product promise
## See the difference
compact before/after
## Try it in 30 seconds
install and invocation
## What changes
compact benefit table
```

The opening promise is: `Keep the decision tied to evidence when the framing changes.`

- [ ] **Step 2: Replace Benchmark Proof with Proof without hype**

Keep the existing stance-drift proof first, then add the roleplay card and this boundary:

```markdown
Reality Slap materially improved stance stability in the release benchmark. In the same-model roleplay pilot, it improved boundary completeness modestly but did not demonstrate lower harmful consensus; both arms recorded zero harmful-compromise flags.
```

Link the detailed result to `evals/same-model-roleplay-ab-2026-07-10.md`.

- [ ] **Step 3: Cut and consolidate the lower README**

Merge repeated `Why`, `Use`, `Do not use`, and answer-shape explanations into scannable tables. Preserve install footprint, deeper docs, validation, contribution guidance, and roadmap, but remove repeated prose already covered by linked docs.

- [ ] **Step 4: Validate README links and claims**

Confirm every relative target exists and compare all README numbers to `evals/evals.json`.

- [ ] **Step 5: Commit the README**

```bash
git add README.md
git commit -m "docs: sharpen README product story"
```

### Task 4: Verify, integrate, and publish

**Files:**
- Verify only: all changed files and Git state.

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: verified `origin/main` containing the complete documentation update.

- [ ] **Step 1: Run focused documentation checks**

```bash
python3 scripts/audit_eval_design.py --bank evals/reality-slap-eval-bank.md --profile stance-drift
python3 scripts/check_release_ready.py
git diff --check origin/main...HEAD
```

Expected: design audit passes, release verdict is pass, and no whitespace errors are reported.

- [ ] **Step 2: Run the full unit suite**

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass with zero failures and zero errors.

- [ ] **Step 3: Review the final diff**

Confirm the diff contains only the design, plan, report, metadata, SVG, and README. Confirm `.agent-lab/` remains untracked and unstaged.

- [ ] **Step 4: Fast-forward local main**

```bash
git switch main
git merge --ff-only feature/readme-roleplay-proof
```

- [ ] **Step 5: Push and verify remote main**

```bash
git push origin main
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
```

Expected: both revisions are identical and the worktree has no tracked modifications.
