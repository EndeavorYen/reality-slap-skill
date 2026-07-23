# Open-Decision Heterogeneous Debate Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run the preregistered two-stage experiment that tests whether structured Terra/Sol peer debate plus a Reality-Slap chair materially improves open-ended decision quality over a model- and call-composition-matched serial review.

**Architecture:** Freeze a 24-case JSON bank, compile deterministic Stage 1 or Stage 2 call graphs into a temporary workspace, execute each record with its own model and effort, blind final candidates for two cross-family judges, generate a human-only conflict queue, and summarize only complete evidence through preregistered adaptive gates. Reuse existing strict JSON, retry, hash, and audit patterns without changing older experiment artifacts.

**Tech Stack:** Python 3 standard library, `unittest`, Codex CLI `exec`, JSON/JSONL workspaces, Markdown reports.

## Global Constraints

- Generator labels are exactly `gpt-5.6-sol` and `gpt-5.6-terra`.
- Sol calls use `medium`; Terra calls use `high`.
- The chair is always `gpt-5.6-sol` at `medium`.
- Seed is exactly `20260724`.
- Freeze all 24 cases, split assignments, prompts, mappings, skill hash, and rubric before the first formal call.
- Stage 1 primary generation is exactly 180 calls: 12 A, 84 B, and 84 C.
- Stage 1 judging is exactly 24 calls: one Sol judge and one Terra judge per case.
- B and C are each exactly `5 Sol medium + 2 Terra high` per case.
- Reality Slap appears only in C/D/F chairs, never in role or serial-review calls.
- Full prompts and raw logs stay in a run-specific `/private/tmp` workspace.
- At most one retry is allowed; no model, effort, case, condition, or prompt substitution.
- Missing or invalid evidence fails closed.
- `.agent-lab/` is unrelated user content and must remain untouched.

---

### Task 1: Freeze And Validate The Open-Decision Case Bank

**Files:**
- Create: `evals/open-decision-case-bank.json`
- Create: `scripts/open_decision_case_bank.py`
- Create: `tests/test_open_decision_case_bank.py`

**Interfaces:**
- Produces: `load_case_bank(path: Path) -> dict`
- Produces: `validate_case_bank(payload: dict, seed: int = 20260724) -> dict`
- Produces: `select_cases(payload: dict, subset: str) -> list[dict]`
- Produces: normalized metadata with `bank_sha256`, 12 primary IDs, 12 reserve IDs, and per-domain counts.

- [ ] **Step 1: Write failing validation tests**

```python
def test_bank_freezes_twenty_four_balanced_cases():
    audit = validate_case_bank(load_case_bank(BANK))
    assert audit["case_count"] == 24
    assert len(audit["primary_ids"]) == 12
    assert len(audit["reserve_ids"]) == 12
    assert all(counts == {"primary": 2, "reserve": 2}
               for counts in audit["domain_split_counts"].values())

def test_case_requires_open_decision_and_hidden_card_fields():
    payload = load_case_bank(BANK)
    broken = json.loads(json.dumps(payload))
    del broken["cases"][0]["adjudication"]["fatal_errors"]
    with self.assertRaisesRegex(ValueError, "fatal_errors"):
        validate_case_bank(broken)
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest tests.test_open_decision_case_bank -v`

Expected: import failure for `open_decision_case_bank`.

- [ ] **Step 3: Implement strict bank loading and deterministic audit**

```python
DOMAINS = (
    "platform-architecture", "product-launch", "operations-incidents",
    "data-privacy-security", "vendor-business-strategy",
    "organization-process",
)
REQUIRED_PUBLIC = (
    "decision_owner", "objective", "facts", "decision_request",
    "plausible_paths", "material_constraints", "harmful_failure_paths",
    "incomplete_information", "reversible_action",
)
REQUIRED_CARD = (
    "must_cover_constraints", "acceptable_decision_families",
    "fatal_errors", "known_valid_insights",
    "decision_closure_requirements", "reasoning_notes",
)

def validate_case_bank(payload, seed=20260724):
    if payload["seed"] != seed or len(payload["cases"]) != 24:
        raise ValueError("case bank must contain 24 cases at the frozen seed")
    # Reject duplicate IDs, bad list lengths, missing fields, leaked private
    # text, or any domain without exactly two primary and two reserve cases.
    return normalized_audit
```

- [ ] **Step 4: Author all 24 cases and hidden adjudication cards**

Use four cases per frozen domain, with two marked `primary` and two `reserve`.
Every case must include at least three plausible paths, four constraints, two
harmful failure paths, one reversible action, two acceptable decision
families, two fatal errors, and one validity-gated insight.

Use this fixed ID/title matrix:

| Domain | Primary | Reserve |
| --- | --- | --- |
| Platform and architecture | `OD-01` shared inference capacity; `OD-02` event consistency boundary | `OD-13` multi-region routing; `OD-14` batch versus interactive scheduling |
| Product and launch | `OD-03` support copilot rollout; `OD-04` enterprise workflow commitment | `OD-15` personalization ramp; `OD-16` pricing experiment rollout |
| Operations and incidents | `OD-05` partial degradation response; `OD-06` migration canary | `OD-17` uncertain-cause incident communication; `OD-18` maintenance deferral |
| Data, privacy, and security | `OD-07` diagnostic retention; `OD-08` partner production access | `OD-19` privacy-preserving analytics; `OD-20` emergency administration |
| Vendor and business strategy | `OD-09` model-provider dependence; `OD-10` accelerator reservation | `OD-21` build-versus-buy search; `OD-22` sole-supplier launch |
| Organization and process | `OD-11` federated on-call ownership; `OD-12` incentive metric design | `OD-23` shared-platform ownership; `OD-24` cross-team roadmap arbitration |

- [ ] **Step 5: Run validation and full tests**

Run: `python3 -m unittest tests.test_open_decision_case_bank -v`

Expected: all case-bank tests pass and the audit reports 24 cases with six
balanced domains.

- [ ] **Step 6: Commit**

```bash
git add evals/open-decision-case-bank.json scripts/open_decision_case_bank.py tests/test_open_decision_case_bank.py
git commit -m "eval: add open-decision case bank"
```

### Task 2: Compile Deterministic Stage 1 Call Graphs

**Files:**
- Create: `scripts/create_open_decision_debate_workspace.py`
- Create: `tests/test_create_open_decision_debate_workspace.py`

**Interfaces:**
- Consumes: `select_cases()` and the frozen `SKILL.md`.
- Produces: `create_workspace(bank_path, skill_path, output_dir, subset, seed) -> dict`
- Produces: `load_records(workspace: Path) -> list[dict]`
- Produces: `records.jsonl`, `manifest.json`, strict schemas, immutable prompt files.
- Produces call kinds: `direct`, `serial`, `role`, `cross_exam`, and `chair`.
- Dependency markers are `__DEPENDENCY_PACKET_JSON__`.

- [ ] **Step 1: Write failing call-plan tests**

```python
def test_primary_stage_one_has_exact_call_budget():
    manifest = create_workspace(BANK, SKILL, workspace, "primary", 20260724)
    records = load_records(workspace)
    assert manifest["generation_call_count"] == 180
    assert manifest["planned_judge_call_count"] == 24
    assert manifest["planned_model_call_count"] == 204
    assert Counter(r["condition"] for r in records) == {
        "direct-sol": 12,
        "matched-serial-review": 84,
        "heterogeneous-debate-rs-chair": 84,
    }

def test_b_and_c_match_five_sol_two_terra_per_case():
    for condition in ("matched-serial-review",
                      "heterogeneous-debate-rs-chair"):
        calls = records_for("OD-01", condition)
        assert Counter((r["model"], r["reasoning_effort"]) for r in calls) == {
            ("gpt-5.6-sol", "medium"): 5,
            ("gpt-5.6-terra", "high"): 2,
        }
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest tests.test_create_open_decision_debate_workspace -v`

Expected: import failure for the workspace creator.

- [ ] **Step 3: Implement strict schemas**

Implement `first_round_schema()`, `cross_exam_schema()`,
`serial_artifact_schema()`, and `final_decision_schema()` with
`additionalProperties: false`. The final schema must require recommendation,
accepted/rejected claims, residual dissent, owner, next action, stop
conditions, rollback path, change evidence, known facts, inferences, and
uncertainties.

- [ ] **Step 4: Implement B's seven-call dependency graph**

```python
SERIAL_PHASES = (
    ("draft", "gpt-5.6-sol", "medium"),
    ("risk-audit", "gpt-5.6-terra", "high"),
    ("alternative-audit", "gpt-5.6-terra", "high"),
    ("revision", "gpt-5.6-sol", "medium"),
    ("adversarial-audit", "gpt-5.6-sol", "medium"),
    ("calibration-audit", "gpt-5.6-sol", "medium"),
    ("final", "gpt-5.6-sol", "medium"),
)
```

Risk and alternative audits depend only on the draft and never on each other.
The final depends on all six preceding records.

- [ ] **Step 5: Implement C's sealed roles, cross-exams, and chair**

Use roles `proposal_advocate`, `failure_mode_red_team`, and
`option_architect`. Assign Terra in deterministic four-case blocks per subset.
Each cross-exam depends on all three first-round outputs but retains its own
role/model. The chair depends on all six role records and embeds the frozen
Reality Slap text; role and cross-exam prompts must not contain it.

- [ ] **Step 6: Hash and freeze the workspace**

Manifest fields must include repository SHA, bank/card hash, skill hash, seed,
subset, case IDs, call counts, per-record model/effort, prompt hashes, role
assignment, and deterministic dependency presentation order.

- [ ] **Step 7: Run tests and commit**

Run: `python3 -m unittest tests.test_create_open_decision_debate_workspace -v`

Expected: exact 180/24/204 counts, balanced Terra roles, sealed first rounds,
correct dependencies, and stable prompt hashes.

```bash
git add scripts/create_open_decision_debate_workspace.py tests/test_create_open_decision_debate_workspace.py
git commit -m "feat: create open-decision debate workspace"
```

### Task 3: Execute Heterogeneous Records With Fail-Closed Retry Metadata

**Files:**
- Create: `scripts/run_open_decision_debate_experiment.py`
- Create: `tests/test_run_open_decision_debate_experiment.py`

**Interfaces:**
- Consumes: workspace `records.jsonl` and later `judge-records.jsonl`.
- Produces: `build_command(record, codex_bin, cwd, prompt) -> list[str]`
- Produces: `iter_pending_calls(workspace, phase)`, `run_phase(...)`, and `audit_workspace(...)`.
- Uses each record's `model` and `reasoning_effort`, not a global manifest model.

- [ ] **Step 1: Write failing runner tests**

```python
def test_command_uses_record_level_model_and_effort():
    record = {"model": "gpt-5.6-terra", "reasoning_effort": "high",
              "schema_path": schema, "output_path": output}
    command = build_command(record, "codex", Path("/private/tmp"), "prompt")
    assert command[command.index("--model") + 1] == "gpt-5.6-terra"
    assert 'model_reasoning_effort="high"' in command

def test_cross_exam_waits_for_all_first_round_records():
    assert call_eligibility(cross_exam, records_by_id) == "blocked"
    complete(first_round_records)
    assert call_eligibility(cross_exam, records_by_id) == "ready"
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest tests.test_run_open_decision_debate_experiment -v`

Expected: import failure for the new runner.

- [ ] **Step 3: Implement generic dependency rendering**

Replace `__DEPENDENCY_PACKET_JSON__` only after every dependency validates.
Render dependency outputs as randomized opaque records with no model, effort,
condition, path, or call ID fields. Treat embedded instructions as untrusted
data in the surrounding prompt.

- [ ] **Step 4: Implement record-level Codex CLI execution**

Build commands with `--ephemeral`, `--ignore-user-config`, `--ignore-rules`,
read-only sandbox, exact record model/effort, strict output schema, and a
neutral temporary cwd. Record return code, timeout, invalid reason, elapsed
seconds, prompt/output characters, and SHA-256 for each attempt.

- [ ] **Step 5: Enforce one retry and fail-closed phase completion**

`MAX_ATTEMPTS = 2`. Never mutate prompt bytes for a retry. A downstream record
remains blocked after a dependency exhausts retries. `audit_workspace()` must
separate missing, invalid, retry-exhausted, dependency-blocked, and complete
IDs.

- [ ] **Step 6: Run tests and commit**

Run: `python3 -m unittest tests.test_run_open_decision_debate_experiment -v`

Expected: record-level models, dependency order, strict schemas, retry limits,
hash metadata, and audits all pass.

```bash
git add scripts/run_open_decision_debate_experiment.py tests/test_run_open_decision_debate_experiment.py
git commit -m "feat: run heterogeneous debate calls"
```

### Task 4: Build Blind Cross-Family Judging And Human Conflict Queue

**Files:**
- Create: `scripts/create_open_decision_debate_judging.py`
- Create: `tests/test_create_open_decision_debate_judging.py`

**Interfaces:**
- Produces: `create_judge_records(workspace, stage) -> list[dict]`
- Produces: `judge-mappings.json`, two differently mapped judge records per case.
- Produces: `create_conflict_queue(workspace) -> dict`
- Consumes optional `human-adjudications.json` with blinded resolutions.

- [ ] **Step 1: Write failing blinding tests**

```python
def test_stage_one_creates_two_different_blind_mappings_per_case():
    records = create_judge_records(workspace, "stage1")
    assert len(records) == 24
    assert {r["model"] for r in records} == {
        "gpt-5.6-sol", "gpt-5.6-terra"
    }
    sol, terra = records_for("OD-01")
    assert sol["label_to_condition"] != terra["label_to_condition"]

def test_judge_prompt_contains_only_final_candidates():
    prompt = Path(record["prompt_path"]).read_text()
    assert "first_round" not in prompt
    assert "cross_exam" not in prompt
    assert "gpt-5.6" not in prompt
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest tests.test_create_open_decision_debate_judging -v`

Expected: import failure for the judging module.

- [ ] **Step 3: Implement the 21-point judge schema and packet**

Require seven integer `0..3` dimensions, total score, six critical booleans
with explanations, all pairwise preferences, ranking, and validity-gated novel
insights. Include public case and private adjudication card, but no process
metadata.

- [ ] **Step 4: Implement cross-family mappings and judge records**

Create one Sol-medium and one Terra-high record per case. Independently shuffle
opaque labels using `seed:case:judge-model:stage`. Reject repeated mappings.
Store mapping hashes outside judge-visible prompts.

- [ ] **Step 5: Implement human conflict queue generation**

A conflict entry is required when pairwise winners differ, critical flags
differ, or total scores differ by more than three. The queue exposes only the
blinded packet and judge rationales. Validate a human resolution containing
`pairwise_winner`, resolved critical flags, rationale, and reviewer timestamp.

- [ ] **Step 6: Run tests and commit**

Run: `python3 -m unittest tests.test_create_open_decision_debate_judging -v`

Expected: all mappings, prompt secrecy, judge models, conflict triggers, and
human resolution validation pass.

```bash
git add scripts/create_open_decision_debate_judging.py tests/test_create_open_decision_debate_judging.py
git commit -m "feat: add blind debate judging"
```

### Task 5: Calculate Adaptive Gates And Claim-Honest Reports

**Files:**
- Create: `scripts/summarize_open_decision_debate_experiment.py`
- Create: `tests/test_summarize_open_decision_debate_experiment.py`

**Interfaces:**
- Produces: `summarize(workspace, stage) -> dict`
- Produces: `render_markdown(summary) -> str`
- Produces: `stage1_gate(n, wins, losses, score_delta, closure, agreement, regressions) -> dict`
- Produces: `final_verdict(gate_result: dict) -> str`
- Produces verdicts and component findings exactly as named in the spec.

- [ ] **Step 1: Write failing gate tests**

```python
def test_primary_green_requires_nine_wins_two_points_and_guardrails():
    result = stage1_gate(n=12, wins=9, losses=2, score_delta=2.0,
                         closure=12, agreement=0.75, regressions=[])
    assert result["decision"] == "green"

def test_seven_wins_positive_delta_is_amber():
    result = stage1_gate(n=12, wins=7, losses=4, score_delta=0.8,
                         closure=12, agreement=0.9, regressions=[])
    assert result["decision"] == "amber"

def test_low_agreement_precedes_human_resolution():
    assert final_verdict(gate(low_agreement=True)) == \
        "inconclusive-evaluator-instability"
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest tests.test_summarize_open_decision_debate_experiment -v`

Expected: import failure for the summarizer.

- [ ] **Step 3: Decode blinded judgments and human resolutions**

Verify mapping hashes and case IDs. Preserve both raw judge outcomes. Use human
pairwise/critical resolutions only where the queue required them. Missing
required resolutions produce `incomplete`.

- [ ] **Step 4: Implement Stage 1 gates**

Implement exact 12-case and 24-case green/amber/stop thresholds from the spec.
Any safety regression yields `safety-regression`; agreement below 75% yields
`inconclusive-evaluator-instability`; complete stable non-gains yield
`not-supported`.

- [ ] **Step 5: Implement Stage 2 component gates**

For C versus D/E/F require `ceil(2n/3)` wins, `+0.75/21`, no critical
regression, and 75% agreement. Reality-Slap contribution also requires no
increase in false unanimity or suppressed valid dissent.

- [ ] **Step 6: Render JSON and Markdown without hiding failed thresholds**

Report models, efforts, case subset, all counts, retries, human conflicts,
actual characters/time, judge agreement, every threshold, limitations, and
claim boundary. Keep `stage1-large-bundle-signal` distinct from
`large-structured-debate-gain-supported`.

- [ ] **Step 7: Run tests and commit**

Run: `python3 -m unittest tests.test_summarize_open_decision_debate_experiment -v`

Expected: green, amber, reserve-green, red, safety, instability, incomplete,
and every Stage 2 component path pass.

```bash
git add scripts/summarize_open_decision_debate_experiment.py tests/test_summarize_open_decision_debate_experiment.py
git commit -m "feat: summarize open-decision debate"
```

### Task 6: Compile Call-Matched Stage 2 Ablations

**Files:**
- Modify: `scripts/create_open_decision_debate_workspace.py`
- Modify: `tests/test_create_open_decision_debate_workspace.py`
- Modify: `scripts/summarize_open_decision_debate_experiment.py`
- Modify: `tests/test_summarize_open_decision_debate_experiment.py`

**Interfaces:**
- Extends: `create_stage2_records(stage1_workspace, output_dir) -> dict`
- Conditions: D `heterogeneous-parallel-self-review-rs-chair`,
  E `heterogeneous-debate-normal-chair`, F `homogeneous-sol-debate-rs-chair`.

- [ ] **Step 1: Write failing Stage 2 call-plan tests**

```python
def test_stage_two_adds_exactly_276_calls_for_twelve_cases():
    manifest = create_stage2_records(stage1_workspace, stage2_workspace)
    assert manifest["new_generation_call_count"] == 252
    assert manifest["planned_judge_call_count"] == 24
    assert manifest["planned_model_call_count"] == 276

def test_d_self_reviews_never_receive_peer_outputs():
    for record in records_for(condition=D, kind="self_review"):
        assert record["depends_on"] == [record["own_first_round_call_id"]]
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `python3 -m unittest tests.test_create_open_decision_debate_workspace -v`

Expected: missing `create_stage2_records`.

- [ ] **Step 3: Implement D, E, and F**

D preserves five Sol/two Terra calls and seven-call depth but prevents peer
exposure. E preserves C roles and cross-exams but omits frozen Reality Slap
from its chair. F preserves C prompts and dependencies but runs every record as
Sol medium.

- [ ] **Step 4: Snapshot and hash Stage 1 C candidates**

Stage 2 must reuse C byte-for-byte. Record C output hashes before compiling
ablations and fail if any source candidate changes.

- [ ] **Step 5: Run focused and summarizer tests**

Run: `python3 -m unittest tests.test_create_open_decision_debate_workspace tests.test_summarize_open_decision_debate_experiment -v`

Expected: exact counts, C snapshot protection, D peer isolation, E skill
absence, F homogeneous model settings, and component verdicts pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/create_open_decision_debate_workspace.py scripts/summarize_open_decision_debate_experiment.py tests/test_create_open_decision_debate_workspace.py tests/test_summarize_open_decision_debate_experiment.py
git commit -m "feat: add debate mechanism ablations"
```

### Task 7: Prove The Full Pipeline In Fixture Mode

**Files:**
- Create: `scripts/run_open_decision_debate_fixture.py`
- Create: `tests/test_open_decision_debate_fixture.py`
- Modify: `evals/evals.json`

**Interfaces:**
- Produces a one-command deterministic fixture workspace.
- Produces: `run_fixture(output_dir: Path, mode: str) -> dict`
- Exercises Stage 1 green, amber, not-supported, safety regression, evaluator
  instability, incomplete, and Stage 2 component outcomes without model calls.

- [ ] **Step 1: Write a failing fixture smoke test**

```python
def test_fixture_runs_full_green_pipeline(tmp_path):
    result = run_fixture(tmp_path, mode="stage2-green")
    assert result["status"] == "complete"
    assert result["verdict"] == "large-structured-debate-gain-supported"
    assert result["audit"]["invalid_call_ids"] == []
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `python3 -m unittest tests.test_open_decision_debate_fixture -v`

Expected: import failure for the fixture runner.

- [ ] **Step 3: Implement fixture payload writers**

Generate schema-valid candidate, judge, and human-adjudication records for each
verdict mode. Fixture records must pass the same loader, hash, mapping, and gate
code used by live data.

- [ ] **Step 4: Register preregistration metadata**

Add a non-result metadata entry to `evals/evals.json` pointing to the design,
plan, case bank, fixed models/efforts, seed, adaptive gate, and explicit
`status: preregistered`. Do not write a supported result before live evidence.

- [ ] **Step 5: Run all repository gates**

Run:

```bash
python3 -m unittest discover -s tests
python3 scripts/validate_eval_bank.py --input evals/reality-slap-eval-bank.md --profile stance-drift
python3 scripts/check_release_ready.py
git diff --check
```

Expected: all tests pass, release readiness reports `"ok": true`, and the
worktree is clean except intended files.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_open_decision_debate_fixture.py tests/test_open_decision_debate_fixture.py evals/evals.json
git commit -m "test: prove open-decision debate pipeline"
```

### Task 8: Run Stage 1 Primary Calls And Blind Judging

**Files:**
- Create after successful live run: `evals/open-decision-debate-stage1-2026-07-24.json`
- Create after successful live run: `evals/open-decision-debate-stage1-2026-07-24.md`
- Modify after successful live run: `evals/evals.json`

**Interfaces:**
- Uses the implemented CLI entry points.
- Raw workspace: `/private/tmp/reality-slap-open-decision-20260724-primary`

- [ ] **Step 1: Create and audit the frozen primary workspace**

Run:

```bash
python3 scripts/create_open_decision_debate_workspace.py \
  --input evals/open-decision-case-bank.json \
  --skill SKILL.md \
  --output /private/tmp/reality-slap-open-decision-20260724-primary \
  --subset primary \
  --seed 20260724
python3 scripts/run_open_decision_debate_experiment.py \
  --workspace /private/tmp/reality-slap-open-decision-20260724-primary \
  --phase generation \
  --audit-only
```

Expected: 180 generation records, 60 immediately ready, 120 dependency-blocked,
zero missing prompt/schema files, and exact manifest hashes.

- [ ] **Step 2: Execute all generation dependency waves**

Run the generation phase repeatedly until the audit reports 180 complete calls
or a retry-exhausted blocker:

```bash
python3 scripts/run_open_decision_debate_experiment.py \
  --workspace /private/tmp/reality-slap-open-decision-20260724-primary \
  --phase generation \
  --max-workers 6 \
  --timeout-seconds 240
```

Expected: 180 complete, zero missing/invalid/retry-exhausted records. If not,
stop and report the exact call IDs; do not create judge packets.

- [ ] **Step 3: Create and execute 24 blind judge calls**

Run:

```bash
python3 scripts/create_open_decision_debate_judging.py \
  --workspace /private/tmp/reality-slap-open-decision-20260724-primary \
  --stage stage1
python3 scripts/run_open_decision_debate_experiment.py \
  --workspace /private/tmp/reality-slap-open-decision-20260724-primary \
  --phase judge \
  --max-workers 4 \
  --timeout-seconds 240
```

Expected: 24 complete judge records and two distinct mappings per case.

- [ ] **Step 4: Generate and resolve only required conflicts**

Run:

```bash
python3 scripts/create_open_decision_debate_judging.py \
  --workspace /private/tmp/reality-slap-open-decision-20260724-primary \
  --create-conflict-queue
```

If the queue is non-empty, present the blinded conflicts to the operator and
wait for `human-adjudications.json`. Validate every required resolution before
summarization. Do not reveal condition identities during adjudication.

- [ ] **Step 5: Summarize and branch on the preregistered gate**

Run:

```bash
python3 scripts/summarize_open_decision_debate_experiment.py \
  --workspace /private/tmp/reality-slap-open-decision-20260724-primary \
  --json evals/open-decision-debate-stage1-2026-07-24.json \
  --markdown evals/open-decision-debate-stage1-2026-07-24.md
```

Expected: one of the exact Stage 1 verdicts and a machine-readable
`next_action` of `run-stage2`, `run-reserve`, or `stop`.

- [ ] **Step 6: Commit complete primary evidence**

```bash
git add evals/open-decision-debate-stage1-2026-07-24.json evals/open-decision-debate-stage1-2026-07-24.md evals/evals.json
git commit -m "eval: run open-decision debate stage one"
```

### Task 9: Follow The Adaptive Next Action

**Files:**
- Create conditionally: reserve or Stage 2 result JSON/Markdown.
- Modify conditionally: `evals/evals.json`.

**Interfaces:**
- Consumes only the `next_action` emitted by Task 8.

- [ ] **Step 1: Stop cleanly on a stop verdict**

If `next_action == "stop"`, do not run additional model calls. Record the exact
not-supported, safety, instability, or incomplete boundary and proceed to the
final repository verification.

- [ ] **Step 2: Run the frozen reserve on amber**

If `next_action == "run-reserve"`, create a second workspace with
`--subset reserve`, repeat Task 8's 204-call process, combine only primary and
reserve evidence through the summarizer, and proceed to Stage 2 only if the
24-case green gate passes.

- [ ] **Step 3: Run Stage 2 on green**

If `next_action == "run-stage2"`, compile D/E/F from the completed Stage 1
workspace, verify C snapshot hashes, execute the 252 new generation calls and
24 judge calls, resolve only required conflicts, and emit the exact Stage 2
verdict plus component findings.

- [ ] **Step 4: Reconcile metadata and run final gates**

Run:

```bash
python3 -m unittest discover -s tests
python3 scripts/check_release_ready.py
git diff --check
```

Expected: all tests pass, release readiness reports `"ok": true`, result
metadata matches the committed report and JSON, and no raw prompts or logs are
tracked.

- [ ] **Step 5: Commit final evidence**

Stage 2:

```bash
git add evals/open-decision-debate-stage2-2026-07-24.json evals/open-decision-debate-stage2-2026-07-24.md evals/evals.json
git commit -m "eval: test structured heterogeneous debate"
```

Reserve-only stop:

```bash
git add evals/open-decision-debate-stage1-24case-2026-07-24.json evals/open-decision-debate-stage1-24case-2026-07-24.md evals/evals.json
git commit -m "eval: extend open-decision debate stage one"
```
