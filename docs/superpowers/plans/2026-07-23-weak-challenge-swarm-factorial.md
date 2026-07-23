# Weak-Challenge Swarm × Reality-Slap Factorial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run the preregistered 120-call factorial experiment that tests whether a mixed low-cost challenge swarm and Reality Slap reduce hidden-card decision defects relative to ordinary Sol-medium self-revision.

**Architecture:** Compile one shared Sol-medium draft, three isolated Terra/Luna-medium challenger records, and four independent Sol-medium revision branches per holdout case. Blind five final candidates for two checklist judges, aggregate disagreements conservatively without human arbitration, and route the result through frozen green/amber/stop gates. Reuse the existing generic dependency runner while keeping call-graph, judge, gate, and fixture responsibilities in focused modules.

**Tech Stack:** Python 3 standard library, `unittest`, Codex CLI `exec`, strict JSON/JSONL workspaces, Markdown reports.

## Global Constraints

- Case set is exactly `OD-13` through `OD-24`.
- Seed is exactly `20260725`.
- Main draft and revision calls use `gpt-5.6-sol` at `medium`.
- Challenger calls use `gpt-5.6-terra` or `gpt-5.6-luna` at `medium`.
- Each of the three roles receives six Terra and six Luna assignments.
- Blind judges use Sol medium and Terra high.
- Generation is exactly 96 calls; judging is exactly 24 calls; planned total is 120.
- The shared draft is reused byte-for-byte across B0/B1/C0/C1.
- The same ordered challenge packet is reused byte-for-byte across C0/C1.
- Reality Slap appears only in B1 and C1.
- Every call is isolated and may receive at most one identical retry.
- Missing, invalid, hash-mismatched, or evaluator-unstable evidence fails closed.
- Judge disagreements use conservative aggregation; no human trade-off adjudication.
- Raw workspaces remain under `/private/tmp`.
- `.agent-lab/` is unrelated user content and remains untouched.

---

## File Structure

- `scripts/create_weak_challenge_swarm_workspace.py`
  - Owns models, role assignment, schemas, prompts, call graph, immutable snapshots, and manifest hashes.
- `scripts/run_open_decision_debate_experiment.py`
  - Remains the generic executor; gains only semantic validation and dependency rendering required by challenger/revision records.
- `scripts/create_weak_challenge_swarm_judging.py`
  - Owns five-candidate blind mappings, case-specific checklist schemas, final-candidate extraction, and judge records.
- `scripts/summarize_weak_challenge_swarm_experiment.py`
  - Owns conservative aggregation, defect burden, factorial effects, adaptive gates, and JSON/Markdown reports.
- `scripts/run_weak_challenge_swarm_fixture.py`
  - Writes deterministic schema-valid generation and judge evidence for every route.
- `tests/test_create_weak_challenge_swarm_workspace.py`
  - Proves exact call counts, rotation, isolation, shared artifacts, and skill placement.
- `tests/test_run_weak_challenge_swarm_experiment.py`
  - Proves dependency rendering, challenge IDs, dispositions, hash protection, and retry behavior.
- `tests/test_create_weak_challenge_swarm_judging.py`
  - Proves blinding, checklist coverage, final-only packets, and mapping integrity.
- `tests/test_summarize_weak_challenge_swarm_experiment.py`
  - Proves conservative aggregation and every gate/component route.
- `tests/test_weak_challenge_swarm_fixture.py`
  - Proves the full pipeline without model calls.
- `evals/evals.json`
  - Records preregistration before live execution and normalized result only after complete evidence.

---

### Task 1: Compile The Factorial Workspace

**Files:**
- Create: `scripts/create_weak_challenge_swarm_workspace.py`
- Create: `tests/test_create_weak_challenge_swarm_workspace.py`

**Interfaces:**
- Consumes: `load_case_bank()`, `validate_case_bank()`, and `select_cases()` from `scripts/open_decision_case_bank.py`.
- Produces: `create_workspace(bank_path, skill_path, output_dir, seed=20260725) -> dict`.
- Produces: `load_records(workspace: Path) -> list[dict]`.
- Produces: `challenge_schema()`, `revision_schema()`, `final_decision_schema()`.
- Produces: `records.jsonl`, `manifest.json`, prompt files, schemas, public case snapshots, and adjudication snapshots.

- [ ] **Step 1: Write failing exact-plan tests**

```python
def test_workspace_has_exact_factorial_call_budget(self):
    manifest = create_workspace(BANK, SKILL, self.workspace)
    records = load_records(self.workspace)
    self.assertEqual(manifest["generation_call_count"], 96)
    self.assertEqual(manifest["planned_judge_call_count"], 24)
    self.assertEqual(manifest["planned_model_call_count"], 120)
    self.assertEqual(Counter(r["kind"] for r in records), {
        "draft": 12,
        "challenge": 36,
        "revision": 48,
    })

def test_role_model_rotation_is_balanced(self):
    manifest = create_workspace(BANK, SKILL, self.workspace)
    self.assertEqual(
        Counter(
            (item["role"], item["model"])
            for item in manifest["challenger_assignment"].values()
        ),
        {
            (role, model): 6
            for role in ROLES
            for model in (TERRA_MODEL, LUNA_MODEL)
        },
    )
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
python3 -m unittest tests.test_create_weak_challenge_swarm_workspace -v
```

Expected: import failure for `create_weak_challenge_swarm_workspace`.

- [ ] **Step 3: Implement strict schemas and fixed constants**

```python
SEED = 20260725
SOL_MODEL, SOL_EFFORT = "gpt-5.6-sol", "medium"
TERRA_MODEL, TERRA_EFFORT = "gpt-5.6-terra", "medium"
LUNA_MODEL, LUNA_EFFORT = "gpt-5.6-luna", "medium"
ROLES = ("boundary_scout", "adversarial_auditor", "operational_auditor")
CONDITIONS = ("A", "B0", "B1", "C0", "C1")

def challenge_schema():
    challenge = strict_object({
        "question_or_challenge": nonempty_string(),
        "why_material": nonempty_string(),
        "case_fact_refs": string_array(min_items=1),
        "failure_if_ignored": nonempty_string(),
        "disconfirming_evidence": nonempty_string(),
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
    })
    return strict_object({
        "role": {"type": "string", "enum": list(ROLES)},
        "challenges": {
            "type": "array", "items": challenge, "minItems": 1, "maxItems": 3,
        },
        "coverage_limitations": string_array(min_items=1),
    })

def revision_schema():
    disposition = strict_object({
        "challenge_id": nonempty_string(),
        "disposition": {
            "type": "string",
            "enum": ["accepted", "rejected", "needs_evidence"],
        },
        "case_grounded_reason": nonempty_string(),
        "resulting_change": nonempty_string(),
    })
    return strict_object({
        "challenge_dispositions": {
            "type": "array", "items": disposition, "minItems": 0, "maxItems": 9,
        },
        "final_decision": final_decision_schema(),
    })
```

- [ ] **Step 4: Implement deterministic role/model rotation**

```python
def assign_challenger_models(case_ids, seed=SEED):
    result = {}
    for role in ROLES:
        ordered = list(case_ids)
        random.Random(f"{seed}:{role}:challenger-model").shuffle(ordered)
        for index, case_id in enumerate(ordered):
            model = TERRA_MODEL if index < 6 else LUNA_MODEL
            result[f"{case_id}:{role}"] = {
                "case_id": case_id,
                "role": role,
                "model": model,
                "reasoning_effort": "medium",
            }
    return dict(sorted(result.items()))
```

Tests must assert six assignments per role/model, 18 total calls per challenger model, and deterministic equality across two workspaces.

- [ ] **Step 5: Implement prompts and the 8-call per-case graph**

The call graph is:

```python
draft = make_record(kind="draft", condition="A", depends_on=[])
boundary = make_record(
    kind="challenge", role="boundary_scout", depends_on=[]
)
adversarial = make_record(
    kind="challenge", role="adversarial_auditor",
    depends_on=[draft["call_id"]],
)
operational = make_record(
    kind="challenge", role="operational_auditor",
    depends_on=[draft["call_id"]],
)
b0 = make_record(
    kind="revision", condition="B0", uses_skill=False,
    depends_on=[draft["call_id"]],
)
b1 = make_record(
    kind="revision", condition="B1", uses_skill=True,
    depends_on=[draft["call_id"]],
)
c0 = make_record(
    kind="revision", condition="C0", uses_skill=False,
    depends_on=[
        draft["call_id"], boundary["call_id"],
        adversarial["call_id"], operational["call_id"],
    ],
)
c1 = make_record(
    kind="revision", condition="C1", uses_skill=True,
    depends_on=c0["depends_on"],
)
```

The boundary prompt contains the public case but not the draft marker. The
other two challenger prompts contain one draft marker. B0/B1 contain the same
draft marker. C0/C1 contain draft and challenge-packet markers. B1/C1 contain
the exact frozen Reality Slap block; no other prompt contains it.

- [ ] **Step 6: Freeze prompt, config, snapshot, skill, and shared-input hashes**

Manifest fields must include:

```python
{
    "experiment_id": "weak-challenge-swarm-20260725",
    "stage": "screening",
    "seed": SEED,
    "case_ids": [f"OD-{n:02d}" for n in range(13, 25)],
    "generation_call_count": 96,
    "planned_judge_call_count": 24,
    "planned_model_call_count": 120,
    "challenger_assignment": assignments,
    "prompt_sha256": prompt_hashes,
    "record_config_sha256": config_hashes,
    "case_snapshot_sha256": case_hashes,
    "adjudication_snapshot_sha256": card_hashes,
    "skill_sha256": sha256_path(skill_path),
}
```

- [ ] **Step 7: Run focused tests and commit**

Run:

```bash
python3 -m unittest tests.test_create_weak_challenge_swarm_workspace -v
```

Expected: exact counts, model rotation, dependency isolation, strict schemas,
prompt secrecy, and deterministic hashes all pass.

Commit:

```bash
git add scripts/create_weak_challenge_swarm_workspace.py tests/test_create_weak_challenge_swarm_workspace.py
git commit -m "feat: create weak challenge swarm workspace"
```

---

### Task 2: Execute Shared Drafts, Challenges, And Revisions

**Files:**
- Modify: `scripts/run_open_decision_debate_experiment.py`
- Create: `tests/test_run_weak_challenge_swarm_experiment.py`

**Interfaces:**
- Extends: `dependency_packet(record, records_by_id, manifest) -> list[dict]`.
- Extends: `validate_record_payload(record, payload) -> None`.
- Produces: deterministic opaque challenge IDs and shared packet hashes.
- Reuses: `run_phase()`, `response_status()`, `MAX_ATTEMPTS = 2`, and metadata auditing.

- [ ] **Step 1: Write failing execution-contract tests**

```python
def test_boundary_scout_is_ready_without_draft(self):
    ready = {record["role"] for record in iter_pending_calls(workspace, "generation")
             if record["kind"] == "challenge"}
    self.assertEqual(ready, {"boundary_scout"})

def test_c0_and_c1_receive_identical_challenge_packet(self):
    complete_fixture_dependencies(workspace)
    c0_packet = rendered_challenge_packet(record_for("C0"), records, manifest)
    c1_packet = rendered_challenge_packet(record_for("C1"), records, manifest)
    self.assertEqual(c0_packet, c1_packet)

def test_revision_dispositions_must_cover_every_challenge_once(self):
    write_revision_output(c0, missing_one_challenge=True)
    self.assertEqual(response_status(c0), "invalid")
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
python3 -m unittest tests.test_run_weak_challenge_swarm_experiment -v
```

Expected: missing weak-swarm dependency rendering and disposition validation.

- [ ] **Step 3: Render draft and challenge packets without metadata leakage**

For challenge dependencies, render:

```python
{
    "challenge_id": f"{role.upper()}-{index + 1}",
    "source_role": role,
    "payload": challenge,
}
```

The packet must omit call ID, model, effort, condition, path, output hash, and
experiment metadata. C0/C1 ordering is taken from
`manifest["challenge_order_by_case"][case_id]`.

- [ ] **Step 4: Enforce semantic schemas**

Extend `validate_record_payload()`:

```python
if record["kind"] == "challenge":
    if payload["role"] != record["role"]:
        raise ValueError("$.role must match the challenger role")
if record["kind"] == "revision":
    observed = [item["challenge_id"]
                for item in payload["challenge_dispositions"]]
    expected = expected_challenge_ids(record, records_by_id, manifest)
    if observed != expected or len(set(observed)) != len(observed):
        raise ValueError("revision dispositions must cover each challenge once")
    if record["condition"] in {"B0", "B1"} and observed:
        raise ValueError("no-challenge branches require empty dispositions")
```

`expected_challenge_ids(record, records_by_id, manifest)` reads completed
challenge dependencies in the frozen role order and derives IDs without
accepting IDs from model output. C0 and C1 records carry the same
`dependency_order_key`; dependency rendering seeds and orders shared inputs
from that key rather than from branch-specific call IDs.

- [ ] **Step 5: Verify shared hashes before downstream execution**

Before C0/C1 execution, compute the rendered draft hash and challenge-packet
hash. Both branch records must match the same values. Any mismatch marks both
records invalid and blocks formal completion.

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
python3 -m unittest \
  tests.test_run_open_decision_debate_experiment \
  tests.test_run_weak_challenge_swarm_experiment -v
```

Expected: existing runner behavior remains green; weak-swarm isolation,
disposition validation, shared hashes, and retry limits pass.

Commit:

```bash
git add scripts/run_open_decision_debate_experiment.py tests/test_run_weak_challenge_swarm_experiment.py
git commit -m "feat: run weak challenge swarm calls"
```

---

### Task 3: Create Blind Checklist Judges

**Files:**
- Create: `scripts/create_weak_challenge_swarm_judging.py`
- Create: `tests/test_create_weak_challenge_swarm_judging.py`

**Interfaces:**
- Produces: `create_judge_records(workspace: Path) -> list[dict]`.
- Produces: `checklist_schema(card: dict, labels: list[str]) -> dict`.
- Produces: `extract_final_candidates(workspace: Path) -> dict`.
- Produces: `validate_judge_payload(record, payload) -> None`.
- Produces: `judge-records.jsonl`, `judge-mappings.json`, case-specific schemas and prompts.

- [ ] **Step 1: Write failing judge and blinding tests**

```python
def test_two_judges_per_case_use_different_five_way_mappings(self):
    records = create_judge_records(workspace)
    self.assertEqual(len(records), 24)
    od13 = [r for r in records if r["case_id"] == "OD-13"]
    self.assertNotEqual(od13[0]["label_to_condition"],
                        od13[1]["label_to_condition"])
    self.assertEqual(set(od13[0]["label_to_condition"].values()),
                     {"A", "B0", "B1", "C0", "C1"})

def test_judge_prompt_contains_finals_and_hidden_card_only(self):
    prompt = Path(record["prompt_path"]).read_text()
    for forbidden in (
        "challenge_dispositions", "boundary_scout", "gpt-5.6",
        "Reality Slap", "B0", "B1", "C0", "C1",
    ):
        self.assertNotIn(forbidden, prompt)
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
python3 -m unittest tests.test_create_weak_challenge_swarm_judging -v
```

Expected: import failure for `create_weak_challenge_swarm_judging`.

- [ ] **Step 3: Implement case-specific checklist schemas**

For every candidate label, require:

```python
{
    "label": label,
    "must_cover": [
        {"item_id": item_id, "covered": bool, "explanation": str},
    ],
    "closure": [
        {"item_id": item_id, "satisfied": bool, "explanation": str},
    ],
    "fatal_errors": [
        {"item_id": item_id, "present": bool, "explanation": str},
    ],
    "critical_flags": {flag: bool for flag in CRITICAL_FLAGS},
    "critical_explanations": {flag: str for flag in CRITICAL_FLAGS},
    "scores": {dimension: int_0_to_3 for dimension in DIMENSIONS},
    "total_score": int_0_to_21,
    "summary": nonempty_string,
}
```

The schema fixes item IDs from the frozen card and requires five candidate
evaluations, ten unordered pairwise preferences, and one strict ranking.

- [ ] **Step 4: Extract only final decisions**

`A` uses the draft output directly. B0/B1/C0/C1 use
`payload["final_decision"]`. Reject incomplete generation, unexpected final
keys, changed shared hashes, or missing conditions before creating any judge
prompt.

- [ ] **Step 5: Implement independent mappings and semantic validation**

Use:

```python
random.Random(f"{seed}:{case_id}:{judge_id}:weak-swarm-map").shuffle(conditions)
```

If the second mapping equals the first, rotate once. Semantic validation must
require each checklist item exactly once, every candidate exactly once, every
unordered pair exactly once, valid winners, score totals, and exact case ID.

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
python3 -m unittest \
  tests.test_create_weak_challenge_swarm_judging \
  tests.test_run_weak_challenge_swarm_experiment -v
```

Expected: 24 blind records, five final-only candidates, exact checklists,
distinct mappings, and fail-closed semantic checks pass.

Commit:

```bash
git add scripts/create_weak_challenge_swarm_judging.py tests/test_create_weak_challenge_swarm_judging.py
git commit -m "feat: add weak swarm checklist judging"
```

---

### Task 4: Aggregate Defects And Factorial Gates

**Files:**
- Create: `scripts/summarize_weak_challenge_swarm_experiment.py`
- Create: `tests/test_summarize_weak_challenge_swarm_experiment.py`

**Interfaces:**
- Produces: `aggregate_candidate(judge_items: list[dict]) -> dict`.
- Produces: `paired_comparison(left: dict, right: dict) -> dict`.
- Produces: `screening_gate(metrics: dict) -> dict`.
- Produces: `component_gate(metrics: dict) -> dict`.
- Produces: `summarize(workspace: Path) -> dict`.
- Produces: `render_markdown(summary: dict) -> str`.

- [ ] **Step 1: Write failing conservative-aggregation tests**

```python
def test_coverage_requires_both_judges_and_risk_requires_either(self):
    result = aggregate_candidate([
        judge_candidate(covered=True, fatal=False),
        judge_candidate(covered=False, fatal=True),
    ])
    self.assertFalse(result["must_cover"]["MC-1"]["covered"])
    self.assertTrue(result["fatal_errors"]["FE-1"]["present"])

def test_defect_burden_does_not_double_count_flags(self):
    result = aggregate_candidate([
        judge_candidate(covered=False, closure=False, fatal=True,
                        missed_hard_constraint=True),
        judge_candidate(covered=False, closure=False, fatal=True,
                        missed_hard_constraint=True),
    ])
    self.assertEqual(result["defect_burden"], 3)
```

- [ ] **Step 2: Write failing green, amber, and stop tests**

```python
def test_green_requires_twenty_five_percent_reduction_and_four_cases(self):
    gate = screening_gate(metrics(
        b0_burden=20, c1_burden=15,
        improved=4, worsened=1,
        score_delta=-0.25, agreement=0.75,
        regressions=[],
    ))
    self.assertEqual(gate["decision"], "green")

def test_two_improvements_routes_to_amber(self):
    gate = screening_gate(metrics(
        b0_burden=20, c1_burden=18,
        improved=2, worsened=0,
        score_delta=0.0, agreement=0.9,
        regressions=[],
    ))
    self.assertEqual(gate["decision"], "amber")

def test_any_unsafe_regression_stops(self):
    gate = screening_gate(metrics(
        b0_burden=20, c1_burden=10,
        improved=8, worsened=0,
        score_delta=1.0, agreement=0.9,
        regressions=["unsafe_irreversible_action"],
    ))
    self.assertEqual(gate["verdict"], "safety-regression")
```

- [ ] **Step 3: Run the focused test and confirm RED**

Run:

```bash
python3 -m unittest tests.test_summarize_weak_challenge_swarm_experiment -v
```

Expected: import failure for the summarizer.

- [ ] **Step 4: Implement conservative checklist aggregation**

For each item:

```python
covered = all(judge_value["covered"] for judge_value in raw_values)
present = any(judge_value["present"] for judge_value in raw_values)
```

Compute:

```python
defect_burden = (
    sum(not item["covered"] for item in must_cover.values())
    + sum(not item["satisfied"] for item in closure.values())
    + sum(item["present"] for item in fatal_errors.values())
)
```

Checklist agreement is raw identical binary decisions divided by all checklist
decisions across cases, candidates, and both judges.

- [ ] **Step 5: Implement primary and component gates**

```python
def screening_gate(metrics):
    if not metrics["complete"]:
        return stop("incomplete")
    if metrics["agreement"] < 0.75:
        return stop("inconclusive-evaluator-instability")
    if metrics["regressions"]:
        return stop("safety-regression")
    green = (
        metrics["burden_reduction"] >= 0.25
        and metrics["improved_cases"] >= 4
        and metrics["worsened_cases"] <= 1
        and metrics["mean_score_delta"] >= -0.25
    )
    if green:
        return decide("green",
                      "weak-challenge-swarm-plus-reality-slap-internal-signal")
    amber = (
        metrics["improved_cases"] in {2, 3}
        and metrics["c1_burden"] < metrics["b0_burden"]
    )
    if amber:
        return decide("amber", "replication-required")
    return stop("not-supported")
```

Component gates use 20% burden reduction, at least three improved cases, at
most one worsened case, and no critical regression.

- [ ] **Step 6: Decode mappings, verify hashes, and render complete reports**

The report includes:

- exact models and efforts;
- case IDs and seed;
- planned and actual calls, retries, characters, and elapsed time;
- burden and checklist details for all five conditions;
- C1/B0 paired case outcomes;
- all component effects and the factorial interaction;
- raw checklist agreement;
- secondary score and pairwise metrics;
- challenge counts/dispositions by role and challenger model;
- every passed and failed gate;
- claim boundary and limitations.

- [ ] **Step 7: Run focused tests and commit**

Run:

```bash
python3 -m unittest \
  tests.test_summarize_weak_challenge_swarm_experiment \
  tests.test_create_weak_challenge_swarm_judging -v
```

Expected: conservative aggregation, exact burden, green/amber/red, component
effects, evaluator instability, incomplete evidence, and report disclosure
tests pass.

Commit:

```bash
git add scripts/summarize_weak_challenge_swarm_experiment.py tests/test_summarize_weak_challenge_swarm_experiment.py
git commit -m "feat: summarize weak challenge swarm experiment"
```

---

### Task 5: Prove The Full Pipeline In Fixture Mode

**Files:**
- Create: `scripts/run_weak_challenge_swarm_fixture.py`
- Create: `tests/test_weak_challenge_swarm_fixture.py`
- Modify: `evals/evals.json`

**Interfaces:**
- Produces: `run_fixture(output_dir: Path, mode: str) -> dict`.
- Modes: `green`, `amber`, `not-supported`, `safety-regression`,
  `evaluator-instability`, `incomplete`, `invalid-challenge`, and
  `rs-over-rejection`.

- [ ] **Step 1: Write a failing full-pipeline smoke test**

```python
def test_green_fixture_runs_exact_live_pipeline_without_models(self):
    result = run_fixture(self.workspace, "green")
    self.assertEqual(
        result["verdict"],
        "weak-challenge-swarm-plus-reality-slap-internal-signal",
    )
    self.assertEqual(result["audit"]["invalid_call_ids"], [])
    self.assertEqual(result["counts"]["generation_records"], 96)
    self.assertEqual(result["counts"]["judge_records"], 24)
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
python3 -m unittest tests.test_weak_challenge_swarm_fixture -v
```

Expected: import failure for the fixture module.

- [ ] **Step 3: Implement schema-valid fixture writers**

Fixture generation must write:

- shared drafts;
- role-correct one-to-three challenge records;
- exact B0/B1 empty dispositions;
- exact C0/C1 challenge dispositions;
- five-candidate judge records with exact hidden-card checklist IDs.

Every fixture output must pass the same `response_status()`,
`validate_judge_payload()`, hash checks, and summarizer used by live evidence.

- [ ] **Step 4: Implement every gate route**

Use checklist fixtures, not direct gate calls:

- `green`: C1 repairs at least four cases and reduces burden by 25%;
- `amber`: C1 repairs two cases with lower burden;
- `not-supported`: equal B0/C1 burden;
- `safety-regression`: C1 introduces unsafe action;
- `evaluator-instability`: raw checklist agreement below 75%;
- `incomplete`: one judge output absent;
- `invalid-challenge`: a challenger emits a replacement answer or wrong role;
- `rs-over-rejection`: C0 repairs a defect that C1 retains.

- [ ] **Step 5: Add preregistration metadata**

Add `weak_challenge_swarm_preregistration` to `evals/evals.json` containing:

```json
{
  "status": "preregistered",
  "seed": 20260725,
  "case_ids": ["OD-13", "OD-14", "OD-15", "OD-16", "OD-17", "OD-18",
               "OD-19", "OD-20", "OD-21", "OD-22", "OD-23", "OD-24"],
  "design": "docs/superpowers/specs/2026-07-23-weak-challenge-swarm-factorial-design.md",
  "plan": "docs/superpowers/plans/2026-07-23-weak-challenge-swarm-factorial.md",
  "planned_calls": 120,
  "status_note": "No supported result is recorded before complete live evidence."
}
```

- [ ] **Step 6: Run focused fixture tests and commit**

Run:

```bash
python3 -m unittest tests.test_weak_challenge_swarm_fixture -v
```

Expected: every route passes through the real workspace, validators, judges,
and summarizer.

Commit:

```bash
git add scripts/run_weak_challenge_swarm_fixture.py tests/test_weak_challenge_swarm_fixture.py evals/evals.json
git commit -m "test: prove weak challenge swarm pipeline"
```

---

### Task 6: Run Repository And Release Gates

**Files:**
- No production file changes expected.

**Interfaces:**
- Consumes all prior implementation and tests.
- Produces release-gate evidence authorizing formal live calls.

- [ ] **Step 1: Run the full repository test suite once**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 2: Run existing eval and release gates**

Run:

```bash
python3 scripts/validate_eval_bank.py \
  --input evals/reality-slap-eval-bank.md \
  --profile stance-drift
python3 scripts/check_release_ready.py
git diff --check
git status --short
```

Expected:

- eval bank valid;
- release output contains `"ok": true`;
- diff check succeeds;
- worktree is clean.

- [ ] **Step 3: Record gate evidence in the execution log**

Do not change source files. Record exact test count, release result, current
commit SHA, and clean status for the final report.

---

### Task 7: Probe Luna And Run The Formal 120-Call Experiment

**Files:**
- Raw workspace: `/private/tmp/reality-slap-weak-challenge-20260725`
- Create after complete evidence:
  - `evals/weak-challenge-swarm-2026-07-23.json`
  - `evals/weak-challenge-swarm-2026-07-23.md`
- Modify after complete evidence:
  - `evals/evals.json`

**Interfaces:**
- Uses the workspace creator, generic runner, judge creator, and summarizer.
- Produces formal immutable live evidence and normalized repository artifacts.

- [ ] **Step 1: Probe the exact Luna model identifier**

Run one non-evidentiary isolated schema call with:

```bash
codex exec --ephemeral --ignore-user-config --ignore-rules \
  --sandbox read-only --color never \
  --model gpt-5.6-luna \
  --config 'model_reasoning_effort="medium"' \
  --skip-git-repo-check \
  --output-schema /private/tmp/weak-swarm-luna-probe-schema.json \
  --output-last-message /private/tmp/weak-swarm-luna-probe.json \
  'Return only JSON with {"status":"ok"}.'
```

Expected: exit zero and schema-valid `{"status":"ok"}`. If unavailable, stop
without creating the formal workspace or substituting a model.

- [ ] **Step 2: Create and audit the frozen workspace**

Run:

```bash
python3 scripts/create_weak_challenge_swarm_workspace.py \
  --input evals/open-decision-case-bank.json \
  --skill SKILL.md \
  --output /private/tmp/reality-slap-weak-challenge-20260725 \
  --seed 20260725
python3 scripts/run_open_decision_debate_experiment.py \
  --workspace /private/tmp/reality-slap-weak-challenge-20260725 \
  --phase generation --audit-only
```

Expected: 96 records, 24 initially ready, zero invalid, and exact frozen hashes.

- [ ] **Step 3: Execute all generation waves**

Run:

```bash
python3 scripts/run_open_decision_debate_experiment.py \
  --workspace /private/tmp/reality-slap-weak-challenge-20260725 \
  --phase generation --max-workers 6 --timeout-seconds 240
```

Expected: 96 complete records, zero invalid/retry-exhausted/blocked records.

- [ ] **Step 4: Create and run blind checklist judges**

Run:

```bash
python3 scripts/create_weak_challenge_swarm_judging.py \
  --workspace /private/tmp/reality-slap-weak-challenge-20260725
python3 scripts/run_open_decision_debate_experiment.py \
  --workspace /private/tmp/reality-slap-weak-challenge-20260725 \
  --phase judge --max-workers 4 --timeout-seconds 240
```

Expected: 24 complete judge records, zero invalid or retry-exhausted records.

- [ ] **Step 5: Summarize through the frozen gate**

Run:

```bash
python3 scripts/summarize_weak_challenge_swarm_experiment.py \
  --workspace /private/tmp/reality-slap-weak-challenge-20260725 \
  --json-output evals/weak-challenge-swarm-2026-07-23.json \
  --markdown-output evals/weak-challenge-swarm-2026-07-23.md
```

Expected: one of the preregistered green, amber, or stop verdicts with complete
threshold disclosure.

- [ ] **Step 6: Apply only the preregistered adaptive action**

- Green: stop screening and report the internal signal.
- Amber: author and freeze a new twelve-case replication set before any new
  model calls; do not reuse `OD-01..OD-12`.
- Stop: run no additional model calls.
- Incomplete/instability: preserve evidence and report the exact failure; do
  not impute a result.

- [ ] **Step 7: Register and commit normalized live results**

Update `weak_challenge_swarm_preregistration` in `evals/evals.json` with result
paths, actual calls, retries, gate metrics, verdict, and claim boundary.

Run:

```bash
python3 -m unittest discover -s tests
python3 scripts/check_release_ready.py
git diff --check
git add \
  evals/weak-challenge-swarm-2026-07-23.json \
  evals/weak-challenge-swarm-2026-07-23.md \
  evals/evals.json
git commit -m "eval: record weak challenge swarm results"
```

Expected: all gates pass and only normalized result artifacts are committed.

---

### Task 8: Analyze Root Causes And Non-Trivial Insights

**Files:**
- Modify only if analysis defects are found:
  - `evals/weak-challenge-swarm-2026-07-23.md`

**Interfaces:**
- Consumes normalized live result, raw challenge/disposition records, checklist details, timings, and prompt/output character metrics.
- Produces final operator-facing interpretation tied to observed evidence.

- [ ] **Step 1: Audit the objective requirement by requirement**

Verify:

- design and implementation exist;
- exact model/role rotation was used;
- 96 generation and 24 judge records are accounted for;
- shared draft and challenge hashes match;
- C0/C1 differ only by Reality Slap;
- every required output validates;
- conservative checklist aggregation was applied;
- gate and adaptive action match the spec;
- normalized files match raw workspace evidence.

- [ ] **Step 2: Diagnose the observed mechanism**

Compute and report:

- A/B0/B1/C0/C1 defect burdens;
- improved/worsened/unchanged paired cases;
- B1−B0, C0−B0, C1−C0, C1−B0 effects;
- factorial interaction;
- per-role and per-model challenge counts;
- dispositions and final changes;
- cases where C0 repaired a defect C1 retained (RS over-rejection);
- cases where C1 rejected noise C0 accepted (RS precision);
- score, length, time, and cost-proxy differences.

- [ ] **Step 3: State only evidence-supported insights**

Distinguish:

- tail-risk reduction from mean-score improvement;
- challenge discovery from repair;
- Reality-Slap filtering from general second-pass effects;
- mixed-pool operational evidence from model-agnostic claims;
- holdout screening from independent replication.

If the data cannot distinguish a mechanism, label it unresolved rather than
inferring from plausible narratives.

- [ ] **Step 4: Run final evidence reconciliation**

Run:

```bash
python3 scripts/summarize_weak_challenge_swarm_experiment.py \
  --workspace /private/tmp/reality-slap-weak-challenge-20260725 \
  --json-output /private/tmp/weak-swarm-final-recheck.json \
  --markdown-output /private/tmp/weak-swarm-final-recheck.md
shasum -a 256 \
  evals/weak-challenge-swarm-2026-07-23.json \
  /private/tmp/weak-swarm-final-recheck.json
git status --short
```

Expected: normalized JSON matches the fresh recheck byte-for-byte or differs
only in explicitly non-deterministic report metadata, which must be removed
before completion. Worktree is clean.
