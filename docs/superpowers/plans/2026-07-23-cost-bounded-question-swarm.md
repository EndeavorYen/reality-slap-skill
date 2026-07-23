# Cost-Bounded Question Swarm Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, and run the approved two-stage experiment comparing several Luna-low question generators with one Terra-high challenger under fixed Sol-medium + Reality-Slap review.

**Architecture:** Extend the existing isolated-call runner to preserve Codex JSONL usage events, then add focused screening and confirmation workspace compilers around the existing open-decision schemas and blind checklist aggregation. Stage 1 selects S2 or S4 on four exploratory cases; Stage 2 evaluates the winner against Terra high on eight newly frozen cases.

**Tech Stack:** Python standard library, Codex CLI JSONL execution, `unittest`, JSON/JSONL experiment artifacts, existing Reality Slap eval helpers.

## Global Constraints

- Reality Slap appears only in Sol-medium final revision calls.
- Luna-low models output only `target` and `question`.
- H, S2, and S4 question packets contain at most eight questions.
- Missing JSONL usage makes cost evidence incomplete.
- Failed-attempt usage remains charged.
- No model or effort substitution is allowed.
- The Stage 2 case bank is frozen before live generation.
- `.agent-lab/` remains untouched and untracked.
- Command productization and README victory claims are out of scope.

---

### Task 1: Capture Actual Codex Usage

**Files:**
- Modify: `scripts/run_open_decision_debate_experiment.py`
- Modify: `tests/test_run_open_decision_debate_experiment.py`

**Interfaces:**
- Produces: `parse_usage_events(text: str) -> dict`
- Produces: `usage_event_path(record: dict, attempt_number: int) -> Path`
- Extends: each `call.json` attempt with `usage` and `events_path`

- [ ] **Step 1: Write failing usage parser and command tests**

Add tests covering:

```python
events = "\n".join(
    [
        '{"type":"thread.started","thread_id":"t"}',
        '{"type":"turn.completed","usage":{"input_tokens":10,'
        '"cached_input_tokens":2,"output_tokens":3,'
        '"reasoning_output_tokens":1}}',
    ]
)
self.assertEqual(
    parse_usage_events(events),
    {
        "input_tokens": 10,
        "cached_input_tokens": 2,
        "output_tokens": 3,
        "reasoning_output_tokens": 1,
    },
)
```

Also require `build_command(...)` to include `--json`, reject no
`turn.completed` event, reject duplicate completion events, and reject missing
or non-integer usage fields.

- [ ] **Step 2: Run the focused test and confirm failure**

Run:

```bash
python3 -m unittest tests.test_run_open_decision_debate_experiment -v
```

Expected: FAIL because `parse_usage_events` and JSONL capture do not exist.

- [ ] **Step 3: Implement isolated JSONL event capture**

In `build_command`, insert `--json`. In `execute_call`, write stdout to
`events-attempt-<N>.jsonl`, stderr to the existing child log, parse the event
file, and store:

```python
attempt["events_path"] = str(events_path)
attempt["usage"] = usage
```

When the final response is schema-valid but usage is missing, set
`invalid_reason = "missing-usage"` so the identical retry policy applies.

- [ ] **Step 4: Re-run the focused test**

Run the same unittest command.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_open_decision_debate_experiment.py \
  tests/test_run_open_decision_debate_experiment.py
git commit -m "feat: capture model usage for experiment calls"
```

### Task 2: Freeze Question Contracts And Holdout Bank

**Files:**
- Create: `scripts/question_swarm_common.py`
- Create: `evals/question-swarm-holdout-bank.json`
- Create: `tests/test_question_swarm_common.py`

**Interfaces:**
- Produces: `question_schema(lenses: tuple[str, ...], max_questions: int) -> dict`
- Produces: `question_prompt(case: dict, draft_marker: str, lenses: tuple[str, ...], max_questions: int) -> str`
- Produces: `load_question_swarm_holdout(path: Path) -> list[dict]`
- Produces: `usage_totals(records: list[dict]) -> dict`
- Produces: `break_even_costs(small_usage: dict, high_usage: dict) -> dict`

- [ ] **Step 1: Write contract and bank validation tests**

Tests must prove:

- exactly eight `QS-01..QS-08` cases;
- exactly two cases in each locked domain;
- each case passes the existing `validate_case`;
- question objects have only `target` and `question`;
- no severity, confidence, explanation, or proposed-fix field exists;
- usage aggregation includes retries;
- incomplete usage returns `complete: false`;
- break-even output reports the exact Luna-to-Terra multiplier at 70% cost.

- [ ] **Step 2: Run the focused test and confirm failure**

```bash
python3 -m unittest tests.test_question_swarm_common -v
```

Expected: FAIL because the module and bank do not exist.

- [ ] **Step 3: Implement the shared module**

Use the existing `strict_object`, `final_decision_schema`, `public_case_text`,
`validate_case`, and SHA-256 helpers. Keep price-independent accounting as:

```python
{
    "input_tokens": ...,
    "cached_input_tokens": ...,
    "output_tokens": ...,
    "reasoning_output_tokens": ...,
    "complete": True,
}
```

Do not invent dollar prices. Calculate and report rate-card break-even
inequalities.

- [ ] **Step 4: Author and freeze eight new cases**

Create two cases per domain:

- `platform-architecture`;
- `product-launch`;
- `operations-incidents`;
- `organization-process`.

Every case must include at least four public facts, four material constraints,
three plausible paths, two harmful failure paths, one uncertainty, four private
must-cover items, two fatal errors, and five closure requirements. Hidden cards
must reward multiple valid bounded decisions rather than one preferred policy.

- [ ] **Step 5: Re-run the focused test**

Expected: PASS with eight valid, non-leaking cases.

- [ ] **Step 6: Commit**

```bash
git add scripts/question_swarm_common.py \
  evals/question-swarm-holdout-bank.json \
  tests/test_question_swarm_common.py
git commit -m "eval: freeze question swarm contracts and holdout"
```

### Task 3: Build Stage 1 Screening

**Files:**
- Create: `scripts/create_question_swarm_screening_workspace.py`
- Create: `scripts/create_question_swarm_screening_judging.py`
- Create: `scripts/summarize_question_swarm_screening.py`
- Create: `tests/test_question_swarm_screening.py`

**Interfaces:**
- Produces: `create_screening_workspace(bank_path, output_dir, seed) -> dict`
- Produces: `create_screening_judges(workspace: Path) -> list[dict]`
- Produces: `summarize_screening(workspace: Path, rate_card: dict | None) -> dict`
- Produces: `selected_arm` equal to `S2`, `S4`, or `None`

- [ ] **Step 1: Write failing workspace and gate tests**

Tests must assert, for four cases:

- 4 Sol-medium drafts;
- 4 Terra-high H calls;
- 8 Luna-low S2 calls;
- 16 Luna-low S4 calls;
- four Sol-medium question-judge records;
- H/S2/S4 each contain at most eight opaque questions;
- all question calls are isolated and depend only on the shared draft;
- no question prompt contains Reality Slap;
- question-judge mappings hide model, effort, arm, lens, and call IDs;
- S2 wins ties within 5%;
- neither arm advancing yields `small-swarm-not-cost-effective`;
- absent rate card yields `price-unresolved`, not a fabricated cost pass.

- [ ] **Step 2: Run the focused test and confirm failure**

```bash
python3 -m unittest tests.test_question_swarm_screening -v
```

- [ ] **Step 3: Implement the Stage 1 workspace**

Use `OD-13`, `OD-16`, `OD-19`, and `OD-22`. Compile one shared Sol draft and
seven question calls per case. Store per-record packet order rather than one
global role order.

- [ ] **Step 4: Implement opaque question judging**

Each judge response must map every opaque question exactly once to zero or more
hidden checklist item IDs and emit duplicate relationships. Validate exact ID
coverage before accepting output.

- [ ] **Step 5: Implement Stage 1 selection**

Compute unique coverage, critical/fatal misses, duplicate fraction, reviewable
fraction, usage completeness, and both 70% measured/break-even cost results.
Select only an eligible S2/S4 arm.

- [ ] **Step 6: Re-run the focused test**

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/create_question_swarm_screening_workspace.py \
  scripts/create_question_swarm_screening_judging.py \
  scripts/summarize_question_swarm_screening.py \
  tests/test_question_swarm_screening.py
git commit -m "feat: add question swarm screening funnel"
```

### Task 4: Build Stage 2 Confirmation

**Files:**
- Create: `scripts/create_question_swarm_confirmation_workspace.py`
- Create: `scripts/create_question_swarm_confirmation_judging.py`
- Create: `scripts/summarize_question_swarm_confirmation.py`
- Create: `tests/test_question_swarm_confirmation.py`

**Interfaces:**
- Produces: `create_confirmation_workspace(bank_path, skill_path, selected_arm, output_dir, seed) -> dict`
- Produces: `create_confirmation_judges(workspace: Path) -> list[dict]`
- Produces: `summarize_confirmation(workspace: Path, rate_card: dict | None) -> dict`

- [ ] **Step 1: Write failing call-graph and verdict tests**

Tests must prove:

- eight shared Sol-medium drafts;
- eight Terra-high H question calls;
- 16 S2 or 32 S4 Luna-low calls;
- eight B1, eight H, and eight S Sol-medium revisions;
- Reality Slap exists in B1/H/S revision prompts and nowhere else;
- B1 has no question packet;
- H/S packets have at most eight opaque questions;
- H and S share the same draft bytes;
- two blind judges per case see only opaque H/S labels;
- B1 is excluded from final quality ranking;
- all success, quality-fail, cost-fail, safety, incomplete, price-unresolved,
  and evaluator-instability verdicts are reachable.

- [ ] **Step 2: Run the focused test and confirm failure**

```bash
python3 -m unittest tests.test_question_swarm_confirmation -v
```

- [ ] **Step 3: Implement Stage 2 generation**

The revision prompt must instruct Sol to silently assess whether each question
is plausible, material, supported, and action-relevant, then return only:

```json
{
  "challenge_dispositions": [],
  "final_decision": { "...": "existing final decision schema" }
}
```

No explicit dispositions are emitted.

- [ ] **Step 4: Implement two-candidate blind judging**

Reuse the existing hidden-card checklist and conservative aggregation contract,
but compile only H and S candidates per judge. Use different deterministic
mappings for Sol-medium and Terra-high judges.

- [ ] **Step 5: Implement cost and quality gates**

Calculate:

```python
review_increment = max(0, revision_usage[arm] - revision_usage["B1"])
critique_loop = challenger_usage[arm] + review_increment
```

Evaluate the exact gates from the approved spec without letting secondary
scores override guardrail or burden failures.

- [ ] **Step 6: Re-run the focused test**

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/create_question_swarm_confirmation_workspace.py \
  scripts/create_question_swarm_confirmation_judging.py \
  scripts/summarize_question_swarm_confirmation.py \
  tests/test_question_swarm_confirmation.py
git commit -m "feat: add question swarm confirmation pipeline"
```

### Task 5: Add Deterministic End-To-End Fixtures

**Files:**
- Create: `scripts/run_question_swarm_fixture.py`
- Create: `tests/test_question_swarm_fixture.py`

**Interfaces:**
- Produces fixture modes: `green`, `quality-fail`, `cost-fail`,
  `safety-regression`, `price-unresolved`, `incomplete`,
  `evaluator-instability`

- [ ] **Step 1: Write failing fixture tests**

Each mode must create a fresh workspace, populate schema-valid generation and
judge outputs plus JSONL usage metadata, run the real summarizers, and assert
the exact verdict.

- [ ] **Step 2: Run the focused test and confirm failure**

```bash
python3 -m unittest tests.test_question_swarm_fixture -v
```

- [ ] **Step 3: Implement the fixture**

Generate deterministic question coverage, final decisions, blind checklist
responses, and usage totals. Do not bypass the production aggregation or gate
functions.

- [ ] **Step 4: Run all experiment-focused tests**

```bash
python3 -m unittest \
  tests.test_run_open_decision_debate_experiment \
  tests.test_question_swarm_common \
  tests.test_question_swarm_screening \
  tests.test_question_swarm_confirmation \
  tests.test_question_swarm_fixture -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_question_swarm_fixture.py \
  tests/test_question_swarm_fixture.py
git commit -m "test: prove cost-bounded question swarm pipeline"
```

### Task 6: Pre-Live Verification

**Files:**
- No production edits expected.

- [ ] **Step 1: Check diff and focused tests**

```bash
git diff --check
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run the release gate once**

```bash
python3 scripts/check_release_ready.py
```

Expected: `ok: true`, including official validator and full unit suite.

- [ ] **Step 3: Freeze provenance**

Record repository SHA, bank SHA, skill SHA, seed, model/effort matrix, prompt
hashes, schemas, and exact planned call counts in both manifests. Any later
code or bank change invalidates the formal run.

### Task 7: Run Stage 1 Live Screening

**Files:**
- Raw workspace: `/private/tmp/question-swarm-screening-<run-id>/`
- Create after completion: `evals/question-swarm-screening-2026-07-23.json`
- Create after completion: `evals/question-swarm-screening-2026-07-23.md`

- [ ] **Step 1: Create and execute the frozen workspace**

Run generation waves, create question judges, then run the judge phase with at
most four parallel workers and one identical retry.

- [ ] **Step 2: Audit completeness**

Require all response schemas, usage events, metadata, dependencies, prompt
hashes, and judge mappings to pass.

- [ ] **Step 3: Summarize and apply the Stage 1 gate**

Commit the normalized JSON and Markdown. If neither S2 nor S4 qualifies, publish
the stop result and do not spend Stage 2 calls.

- [ ] **Step 4: Commit**

```bash
git add evals/question-swarm-screening-2026-07-23.json \
  evals/question-swarm-screening-2026-07-23.md
git commit -m "eval: record question swarm screening result"
```

### Task 8: Run Stage 2 And Publish The Result

**Files:**
- Raw workspace: `/private/tmp/question-swarm-confirmation-<run-id>/`
- Create: `evals/question-swarm-cost-2026-07-23.json`
- Create: `evals/question-swarm-cost-2026-07-23.md`

- [ ] **Step 1: Create the confirmation workspace from the frozen winner**

Reject a missing or non-eligible Stage 1 winner. Freeze the eight-case bank,
selected arm, rate-card status, and repository SHA.

- [ ] **Step 2: Execute generation and blind judging**

Run dependency waves until complete, create blind H/S judge packets, then run
both judges. Retry only failed identical calls once.

- [ ] **Step 3: Audit and summarize**

Publish primary defect burden, paired outcomes, guardrails, agreement, actual
token usage, review increment, break-even price ratios, elapsed diagnostics,
retry details, verdict, limitations, and non-trivial mechanism insights.

- [ ] **Step 4: Re-run the release gate**

```bash
git diff --check
python3 scripts/check_release_ready.py
```

- [ ] **Step 5: Commit the result**

```bash
git add evals/question-swarm-cost-2026-07-23.json \
  evals/question-swarm-cost-2026-07-23.md
git commit -m "eval: record cost-bounded question swarm result"
```

