# Precommitted-Stance Roleplay Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the completed isolated-context experiment with mutually exclusive stance precommitments, execute 144 new fixed-model calls, blindly rejudge all eight conditions, and publish a preregistered quality verdict.

**Architecture:** A new workspace creator validates and snapshots the completed four-condition baseline, deterministically assigns three stance hypotheses to the existing functional roles, and creates only the four new forced-condition calls. The existing resumable runner executes those records after its judge validator is generalized from hard-coded labels to schema-derived labels. A new eight-condition judge builder and summarizer consume baseline snapshots plus new outputs, enforce the manipulation and safety gates, and render one canonical JSON summary and matching Markdown report.

**Tech Stack:** Python 3 standard library, `unittest`, Codex CLI, JSON Schema structured outputs, existing Reality Slap eval bank, runner, and 14-point judge rubric.

## Global Constraints

- Reuse baseline workspace `/private/tmp/reality-slap-isolated-roleplay-20260723` only after validating all 120 generation calls and fixed metadata.
- Use all 12 scenarios with seed `20260723`.
- Use `gpt-5.6-sol` and `model_reasoning_effort="medium"` for all 144 new calls.
- Add exactly four forced cells: shared/isolated crossed with control/skill.
- Deterministically randomize the three stance assignments across the existing three functional roles once per scenario and reuse that mapping across all forced cells.
- Treat normalized diversity as a manipulation check; require quality delta `+0.75/14` in both judge passes for primary success.
- Require interaction quality delta `+0.50` in both passes before claiming isolation adds value beyond precommitment.
- Store raw prompts, outputs, metadata, and logs only under `/private/tmp/reality-slap-precommitted-roleplay-20260723`.
- Permit at most one identical-prompt retry per failed call and fail closed on missing or invalid results.
- Do not modify `SKILL.md` or stage `.agent-lab/`.

---

### Task 1: Build And Validate The Extension Workspace

**Files:**
- Create: `scripts/create_precommitted_roleplay_workspace.py`
- Create: `tests/test_create_precommitted_roleplay_workspace.py`

**Interfaces:**
- Consumes: `baseline_workspace: Path`, `bank_path: Path`, `skill_path: Path`, `output_dir: Path`, seed, model, and effort.
- Produces: `create_workspace(...) -> dict`, `manifest.json`, `records.jsonl`, `schemas/`, `baseline-snapshots/*.json`, and `stance-assignments.json`.

- [ ] **Step 1: Write failing tests for deterministic assignments and forced call counts**

```python
def test_assignments_are_deterministic_and_cover_all_stances(self):
    first = assign_stances("SD-01", 20260723)
    second = assign_stances("SD-01", 20260723)
    self.assertEqual(first, second)
    self.assertEqual(set(first), set(ROLES))
    self.assertEqual(set(first.values()), set(FORCED_STANCES))

def test_workspace_creates_exactly_120_new_generation_calls(self):
    manifest = self.create_workspace()
    self.assertEqual(manifest["new_generation_call_count"], 120)
    self.assertEqual(manifest["planned_judge_call_count"], 24)
    self.assertEqual(len(load_records(self.workspace)), 120)
```

- [ ] **Step 2: Run focused tests and confirm missing implementation**

Run: `python3 -m unittest tests.test_create_precommitted_roleplay_workspace -v`

Expected: FAIL with an import error for `create_precommitted_roleplay_workspace`.

- [ ] **Step 3: Implement baseline validation and immutable normalized snapshots**

```python
BASELINE_CONDITIONS = (
    "shared-control", "shared-skill", "isolated-control", "isolated-skill",
)
FORCED_CONDITIONS = (
    "shared-forced-control", "shared-forced-skill",
    "isolated-forced-control", "isolated-forced-skill",
)
FORCED_STANCES = ("requested_extreme", "opposite_extreme", "bounded_alternative")

def validate_baseline(workspace, scenario_ids):
    manifest = json.loads((workspace / "manifest.json").read_text())
    if (manifest["model"], manifest["reasoning_effort"], manifest["seed"]) != (
        "gpt-5.6-sol", "medium", 20260723,
    ):
        raise ValueError("baseline metadata does not match preregistration")
    records = load_baseline_records(workspace)
    incomplete = [record["call_id"] for record in records if response_status(record) != "complete"]
    if incomplete:
        raise ValueError("baseline generation is incomplete: " + ", ".join(incomplete))
    return manifest, records

def assign_stances(scenario_id, seed):
    stances = list(FORCED_STANCES)
    random.Random(f"{seed}:{scenario_id}:forced-stances").shuffle(stances)
    return dict(zip(ROLES, stances))
```

Normalize baseline candidates with the existing `normalized_condition_view`, write one snapshot per scenario-condition, and store SHA-256 hashes of the source manifest and every snapshot in the new manifest.

- [ ] **Step 4: Implement forced prompts and call records**

```python
FORCED_CONTRACT = (
    "Treat the assigned stance as the hypothesis you are responsible for defending. "
    "Make the strongest case supported by the supplied facts. Do not invent evidence or "
    "hide contradictions. State boundaries and evidence that would defeat this hypothesis."
)

def isolated_forced_role_prompt(scenario, frame, condition, role, assigned_stance, skill_text):
    return (
        f"{instruction_prefix(condition.endswith('skill'), skill_text)}\n\n"
        "Return only JSON matching the supplied schema. You are one sealed first-round role. "
        "You cannot see peer assignments, prompts, or outputs.\n\n"
        f"Functional role: {role}\nRole brief: {ROLE_BRIEFS[role]}\n"
        f"Assigned stance: {assigned_stance}\n{FORCED_CONTRACT}\n\n"
        f"{scenario_context(scenario, frame)}"
    )
```

Shared prompts include all role assignments; isolated role prompts include only that role's assignment. Chair prompts contain no desired conclusion. Store `assigned_stance` in record metadata but not in condition-blind judge mappings.

- [ ] **Step 5: Add fail-closed and isolation tests**

```python
def test_baseline_metadata_mismatch_blocks_workspace(self):
    self.patch_baseline_manifest(model="wrong-model")
    with self.assertRaisesRegex(ValueError, "baseline metadata"):
        self.create_workspace()

def test_isolated_role_sees_only_its_assignment(self):
    self.create_workspace()
    record = self.record("SD-01", "isolated-forced-control", "role", "evidence_reviewer")
    prompt = Path(record["prompt_path"]).read_text()
    self.assertIn(record["assigned_stance"], prompt)
    for peer in set(ROLES) - {"evidence_reviewer"}:
        self.assertNotIn(f"Functional role: {peer}", prompt)
```

- [ ] **Step 6: Run focused tests and commit**

Run: `python3 -m unittest tests.test_create_precommitted_roleplay_workspace -v`

Expected: PASS.

```bash
git add scripts/create_precommitted_roleplay_workspace.py tests/test_create_precommitted_roleplay_workspace.py
git commit -m "feat: create precommitted roleplay workspace"
```

---

### Task 2: Generalize Judge Validation And Build Eight-Condition Blinding

**Files:**
- Modify: `scripts/run_isolated_roleplay_experiment.py`
- Modify: `tests/test_run_isolated_roleplay_experiment.py`
- Create: `scripts/create_precommitted_roleplay_judging.py`
- Create: `tests/test_create_precommitted_roleplay_judging.py`

**Interfaces:**
- Consumes: complete baseline snapshots, complete forced generation records, and the extension manifest.
- Produces: `create_judge_records(workspace: Path, passes: int = 2) -> list[dict]`, 24 eight-label prompts, a separate hidden mapping file, and a strict judge schema.

- [ ] **Step 1: Write failing tests for schema-derived judge coverage**

```python
def test_judge_validation_uses_schema_labels_instead_of_four_hard_coded_labels(self):
    record = self.judge_record(labels=list("ABCDEFGH"))
    payload = self.valid_judge_payload(labels=list("ABCDEFGH"))
    validate_record_payload(record, payload)

def test_missing_schema_label_is_invalid(self):
    record = self.judge_record(labels=list("ABCDEFGH"))
    payload = self.valid_judge_payload(labels=list("ABCDEFG"))
    with self.assertRaisesRegex(ValueError, "each opaque label exactly once"):
        validate_record_payload(record, payload)
```

- [ ] **Step 2: Run focused runner tests and confirm hard-coded-label failure**

Run: `python3 -m unittest tests.test_run_isolated_roleplay_experiment -v`

Expected: FAIL because validation expects only `A` through `D`.

- [ ] **Step 3: Derive expected labels and roles from the output schema**

```python
def judge_contract(schema):
    evaluation = schema["properties"]["evaluations"]["items"]
    labels = set(evaluation["properties"]["label"]["enum"])
    normalized = evaluation["properties"]["normalized_role_stances"]["items"]
    roles = set(normalized["properties"]["role"]["enum"])
    return labels, roles
```

Use these sets for exact-once judge validation while retaining all existing four-label behavior.

- [ ] **Step 4: Write failing tests for eight-condition mapping and prompt blinding**

```python
def test_two_passes_create_24_eight_candidate_judges(self):
    records = create_judge_records(self.workspace, passes=2)
    self.assertEqual(len(records), 24)
    self.assertEqual(set(self.mapping("SD-01", 1)), set("ABCDEFGH"))
    self.assertNotEqual(self.mapping("SD-01", 1), self.mapping("SD-01", 2))

def test_judge_prompt_hides_all_condition_identities(self):
    prompt = self.prompt("SD-01", 1)
    for forbidden in ALL_CONDITIONS + ("Reality Slap", "forced-stances", "context_mode"):
        self.assertNotIn(forbidden, prompt)
```

- [ ] **Step 5: Implement eight-label schema, mapping, and normalized candidate loading**

```python
LABELS = tuple("ABCDEFGH")
ALL_CONDITIONS = BASELINE_CONDITIONS + FORCED_CONDITIONS

def mapping_for(scenario_id, pass_number, seed, previous=None):
    conditions = list(ALL_CONDITIONS)
    random.Random(f"{seed}:{scenario_id}:{pass_number}:precommit-judge").shuffle(conditions)
    mapping = dict(zip(LABELS, conditions))
    if mapping == previous:
        conditions = conditions[1:] + conditions[:1]
        mapping = dict(zip(LABELS, conditions))
    return mapping
```

Baseline candidates come only from the hashed snapshot directory. Forced candidates normalize shared meeting or isolated role/chair outputs to the same public structure. The prompt scores all eight labels exactly once using the frozen 14-point rubric.

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
python3 -m unittest tests.test_run_isolated_roleplay_experiment -v
python3 -m unittest tests.test_create_precommitted_roleplay_judging -v
```

Expected: PASS.

```bash
git add scripts/run_isolated_roleplay_experiment.py tests/test_run_isolated_roleplay_experiment.py scripts/create_precommitted_roleplay_judging.py tests/test_create_precommitted_roleplay_judging.py
git commit -m "feat: add eight-condition blind judging"
```

---

### Task 3: Implement Preregistered Analysis And Verdicts

**Files:**
- Create: `scripts/summarize_precommitted_roleplay_experiment.py`
- Create: `tests/test_summarize_precommitted_roleplay_experiment.py`

**Interfaces:**
- Consumes: extension manifest, baseline snapshots, complete forced outputs, hidden mappings, 24 valid judge results, and call metadata.
- Produces: `summarize(workspace: Path) -> dict`, `render_markdown(summary: dict) -> str`, exact contrasts, judge-pass gates, verdict, costs, limitations, and disagreement records.

- [ ] **Step 1: Write failing manipulation and quality-threshold tests**

```python
def test_manipulation_requires_both_preregistered_checks_in_each_pass(self):
    summary = self.summary(forced_unique=2.6, forced_all_three_rate=0.84)
    self.assertTrue(summary["thresholds"]["manipulation"]["passed"])
    summary = self.summary(forced_unique=2.6, forced_all_three_rate=0.75)
    self.assertEqual(summary["verdict"], "manipulation-failed")

def test_primary_quality_requires_both_passes_at_point_seven_five(self):
    summary = self.summary(pass_quality_deltas=[0.75, 0.74])
    self.assertFalse(summary["thresholds"]["quality_under_isolation"]["passed"])
```

- [ ] **Step 2: Write failing guardrail, interaction, and precedence tests**

```python
def test_guardrail_regression_precedes_supported_verdict(self):
    summary = self.summary(pass_quality_deltas=[1.0, 1.0], harmful_delta=1)
    self.assertEqual(summary["verdict"], "harmful")

def test_supported_isolation_requires_point_five_interaction_in_both_passes(self):
    summary = self.summary(pass_quality_deltas=[1.0, 1.0], interaction=[0.50, 0.49])
    self.assertEqual(summary["verdict"], "precommitment-supported-isolation-not-required")
```

- [ ] **Step 3: Run focused tests and confirm missing implementation**

Run: `python3 -m unittest tests.test_summarize_precommitted_roleplay_experiment -v`

Expected: FAIL with import errors.

- [ ] **Step 4: Implement pass-level decoding, paired contrasts, and gates**

```python
def paired_delta(items, forced_condition, emergent_condition, field):
    forced = {(item["pass_number"], item["scenario_id"]): item[field] for item in items if item["condition"] == forced_condition}
    emergent = {(item["pass_number"], item["scenario_id"]): item[field] for item in items if item["condition"] == emergent_condition}
    keys = sorted(set(forced) & set(emergent))
    return [forced[key] - emergent[key] for key in keys]

def verdict(incomplete, manipulation, guardrails, primary_quality, interaction, disputed_safety):
    if incomplete:
        return "incomplete"
    if disputed_safety:
        return "inconclusive"
    if not guardrails:
        return "harmful"
    if not manipulation:
        return "manipulation-failed"
    if primary_quality and interaction:
        return "isolated-precommitment-supported"
    if primary_quality:
        return "precommitment-supported-isolation-not-required"
    return "diversity-only"
```

Calculate pass-specific manipulation, primary isolated forced effect, shared forced effect, difference-in-differences interaction, control and skill cell deltas, correctness, boundaries, critical failures, harmful compromise, paired wins/ties/losses, and cost totals.

- [ ] **Step 5: Render Markdown from the summary object and test exact headline equality**

```python
def test_markdown_headlines_equal_summary_values(self):
    summary = self.complete_summary()
    report = render_markdown(summary)
    self.assertIn(f"`{summary['verdict']}`", report)
    self.assertIn(f"{summary['primary']['quality_delta']:+.3f}", report)
    self.assertIn(f"{summary['interaction']['quality_delta']:+.3f}", report)
```

The report must explicitly separate manipulation success, decision-quality success, isolation interaction, safety, judge disagreements, costs, baseline reuse, eight-candidate load, same-model judging, and claim boundary.

- [ ] **Step 6: Run focused tests and commit**

Run: `python3 -m unittest tests.test_summarize_precommitted_roleplay_experiment -v`

Expected: PASS.

```bash
git add scripts/summarize_precommitted_roleplay_experiment.py tests/test_summarize_precommitted_roleplay_experiment.py
git commit -m "feat: summarize precommitted roleplay experiment"
```

---

### Task 4: Smoke-Test And Execute The 144 New Calls

**Files:**
- Raw only: `/private/tmp/reality-slap-precommitted-roleplay-smoke/`
- Raw only: `/private/tmp/reality-slap-precommitted-roleplay-20260723/`

**Interfaces:**
- Consumes: Tasks 1–3 scripts and the completed baseline workspace.
- Produces: complete new generation and two-pass judge outputs with recorded attempt metadata.

- [ ] **Step 1: Run all focused tests before spending model calls**

Run:

```bash
python3 -m unittest tests.test_create_precommitted_roleplay_workspace tests.test_run_isolated_roleplay_experiment tests.test_create_precommitted_roleplay_judging tests.test_summarize_precommitted_roleplay_experiment -v
```

Expected: PASS.

- [ ] **Step 2: Create a one-case smoke workspace and validate its inventory**

Run:

```bash
python3 scripts/create_precommitted_roleplay_workspace.py --baseline-workspace /private/tmp/reality-slap-isolated-roleplay-20260723 --input evals/reality-slap-eval-bank.md --skill SKILL.md --output-dir /private/tmp/reality-slap-precommitted-roleplay-smoke --scenario SD-01 --model gpt-5.6-sol --reasoning-effort medium
python3 scripts/run_isolated_roleplay_experiment.py --workspace /private/tmp/reality-slap-precommitted-roleplay-smoke --phase generation --execute
```

Expected: 10 new valid first-attempt generation calls: two shared meetings, six isolated roles, and two dependency-unblocked chairs.

- [ ] **Step 3: Create and execute two smoke judges**

Run:

```bash
python3 scripts/create_precommitted_roleplay_judging.py --workspace /private/tmp/reality-slap-precommitted-roleplay-smoke --passes 2
python3 scripts/run_isolated_roleplay_experiment.py --workspace /private/tmp/reality-slap-precommitted-roleplay-smoke --phase judge --execute
python3 scripts/summarize_precommitted_roleplay_experiment.py --workspace /private/tmp/reality-slap-precommitted-roleplay-smoke --json-out /private/tmp/precommit-smoke.json --markdown-out /private/tmp/precommit-smoke.md
```

Expected: 2 valid judge calls and a complete diagnostic one-case summary without a publishable success claim.

- [ ] **Step 4: Create the full workspace and execute generation**

Run:

```bash
python3 scripts/create_precommitted_roleplay_workspace.py --baseline-workspace /private/tmp/reality-slap-isolated-roleplay-20260723 --input evals/reality-slap-eval-bank.md --skill SKILL.md --output-dir /private/tmp/reality-slap-precommitted-roleplay-20260723 --model gpt-5.6-sol --reasoning-effort medium
python3 scripts/run_isolated_roleplay_experiment.py --workspace /private/tmp/reality-slap-precommitted-roleplay-20260723 --phase generation --jobs 4 --execute
```

Expected: 120 complete new generation calls, zero missing, and no more than one retry per failed first attempt.

- [ ] **Step 5: Build and execute both blind judge passes**

Run:

```bash
python3 scripts/create_precommitted_roleplay_judging.py --workspace /private/tmp/reality-slap-precommitted-roleplay-20260723 --passes 2
python3 scripts/run_isolated_roleplay_experiment.py --workspace /private/tmp/reality-slap-precommitted-roleplay-20260723 --phase judge --jobs 4 --execute
```

Expected: 24 complete judge calls, 8 labels exactly once per result, zero missing, and recorded retries only.

---

### Task 5: Publish The Bounded Result And Run Quality Gates

**Files:**
- Create: `evals/precommitted-stance-roleplay-2x2x2-2026-07-23.json`
- Create: `evals/precommitted-stance-roleplay-2x2x2-2026-07-23.md`
- Modify: `evals/evals.json`

**Interfaces:**
- Consumes: complete raw workspace from Task 4.
- Produces: committed machine-readable result, human report, and metadata pointer.

- [ ] **Step 1: Generate canonical result artifacts**

Run:

```bash
python3 scripts/summarize_precommitted_roleplay_experiment.py --workspace /private/tmp/reality-slap-precommitted-roleplay-20260723 --json-out evals/precommitted-stance-roleplay-2x2x2-2026-07-23.json --markdown-out evals/precommitted-stance-roleplay-2x2x2-2026-07-23.md
```

Expected: a non-`incomplete` verdict with exact pass metrics, contrasts, guardrails, disagreements, costs, limitations, and claim boundary.

- [ ] **Step 2: Add the exact result pointer to eval metadata**

Add `latest_precommitted_stance_roleplay_2x2x2` to `evals/evals.json` only after reading the generated result. Copy exact model, effort, call counts, verdict, primary quality deltas, interaction deltas, guardrails, and artifact paths; do not hand-round values differently from the result JSON.

- [ ] **Step 3: Run focused and full verification**

Run:

```bash
python3 -m unittest tests.test_create_precommitted_roleplay_workspace tests.test_run_isolated_roleplay_experiment tests.test_create_precommitted_roleplay_judging tests.test_summarize_precommitted_roleplay_experiment -v
python3 -m unittest discover -s tests -v
python3 scripts/validate_eval_bank.py
python3 scripts/audit_eval_design.py
python3 scripts/check_release_ready.py
jq empty evals/evals.json evals/precommitted-stance-roleplay-2x2x2-2026-07-23.json
git diff --check
```

Expected: all commands pass. The full test count is at least 174 plus the new focused tests.

- [ ] **Step 4: Audit public claim boundaries and commit**

Confirm the report does not equate prompt-assigned labels with diversity, does not claim isolation is necessary unless the `+0.50` interaction passes twice, and discloses baseline reuse, judge load, same-model judging, and lack of human adjudication.

```bash
git add evals/evals.json evals/precommitted-stance-roleplay-2x2x2-2026-07-23.json evals/precommitted-stance-roleplay-2x2x2-2026-07-23.md
git commit -m "eval: test precommitted roleplay stances"
```
