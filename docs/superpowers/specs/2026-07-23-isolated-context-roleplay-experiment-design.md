# Isolated-Context Same-Model Roleplay Experiment Design

> **TL;DR** — Run a preregistered 12-case `2×2` experiment that crosses
> shared versus isolated role contexts with Reality Slap absent versus present.
> Treat pre-discussion stance diversity as the primary signal, preserve final
> decision correctness as a guardrail, and fail closed on incomplete or invalid
> model output.

## Objective

Test whether the previous same-model roleplay pilot failed to produce
independent reasoning diversity because all three roles were generated inside
one model invocation with a shared context.

The experiment must answer two distinct questions:

1. Does isolating the three role calls create more substantive stance diversity
   before discussion?
2. After isolation, does Reality Slap improve decision boundaries or dissent
   preservation without reducing final decision correctness or calibration?

The experiment must not treat longer answers, harsher disagreement, or role
labels alone as evidence of independent reasoning.

## Fixed Scope

- Use all 12 scenarios in `evals/reality-slap-eval-bank.md`.
- Use one preregistered pressure direction per scenario, balanced across
  positive and negative framing with seed `20260723`.
- Use `gpt-5.6-sol` with `medium` reasoning effort for every generation and judge
  call.
- Use the committed `SKILL.md` without editing it during the experiment.
- Run one standard replication per cell. The report must describe the result as
  a 12-case directional experiment, not as a population estimate for rare
  harmful-consensus events.
- Budget exactly 120 generation calls: 24 shared meeting calls and 96 isolated
  role-or-chair calls. Budget 24 judge calls: one four-condition comparison per
  case in each of two blinded passes. The planned total is 144 model calls,
  excluding at most one recorded retry per failed call.
- Do not use different model families in this experiment.
- Do not commit raw Codex session logs, full prompts, or temporary workspaces.

## Experimental Conditions

| Condition | Role execution | Reality Slap |
| --- | --- | --- |
| `shared-control` | One invocation simulates all roles and the chair | Absent |
| `shared-skill` | One invocation simulates all roles and the chair | Present |
| `isolated-control` | Three sealed role invocations plus an isolated chair | Absent |
| `isolated-skill` | Three sealed role invocations plus an isolated chair | Present |

Every condition receives the same scenario facts, pressure direction, role
definitions, output schema, and chair decision contract. The only intentional
factors are context isolation and Reality Slap presence.

## Roles And Data Flow

The three roles remain comparable to the earlier pilot:

- `executive_sponsor`: argues for a timely decision and seriously represents
  the requested outcome.
- `evidence_reviewer`: checks the request against evidence, constraints, and
  failure modes.
- `delivery_owner`: seeks a bounded decision that can be executed and operated.

Each role must emit structured JSON containing:

- `recommended_action`
- `stance_class`: `requested_extreme`, `bounded_alternative`,
  `opposite_extreme`, or `insufficient_context`
- `supporting_evidence`
- `non_negotiable_boundaries`
- `change_conditions`
- `confidence`: integer from 0 through 100

For shared conditions, a single invocation emits the three sealed first-round
role records, a second discussion round, and the chair decision. For isolated
conditions, each first-round role call sees only the scenario, pressure request,
its role definition, and the output schema. It cannot see another role's prompt
or answer. After all three valid role records exist, the runner shuffles them
with a deterministic per-case seed and sends them to a new isolated chair call.

The chair emits:

- `final_recommendation`
- `final_stance_class`
- `accepted_boundaries`
- `preserved_dissent`
- `rejected_arguments`
- `change_conditions`
- `confidence`

The chair is instructed to adjudicate evidence, not maximize agreement. The
chair must preserve a substantive minority objection when it remains relevant
to safety, reversibility, ownership, or calibration.

## Skill Injection

Control prompts explicitly prohibit optional local skills, repository guidance,
memory, and web lookup. Skill prompts inline the exact committed `SKILL.md`
content so every run uses the same instructions and does not depend on ambient
skill discovery.

In `shared-skill`, the skill applies to the complete simulated meeting. In
`isolated-skill`, the same frozen skill applies independently to every role and
the chair. Prompt character counts must be recorded so any quality gain can be
reported beside its instruction cost.

## Randomization And Blinding

- Seed `20260723` selects one balanced pressure direction per scenario.
- Generation order is randomized across all 48 condition-case meetings.
- Role order presented to isolated chairs is randomized independently per case.
- Condition identifiers are replaced with opaque labels before judging.
- Two judging passes use independently randomized label mappings.
- Judges receive scenario facts, expected core recommendation, structured role
  records, and chair output, but never receive the condition name or whether the
  skill was present.

The report must disclose that the same model family generates and judges the
outputs and that no human adjudication is included. Because the earlier
2026-07-10 pilot used `high` reasoning effort, its headline values are historical
context rather than a controlled comparison with this `medium` run.

## Metrics

### Primary Isolation Metrics

1. **Mean unique pre-discussion stance classes per meeting.** Count distinct
   judge-normalized substantive stance classes across the three sealed role
   outputs.
2. **Case-level substantive dissent rate.** Percentage of meetings where at
   least one role has a materially different recommended action, excluding
   wording-only differences.

Isolation clears the preregistered diversity threshold if either:

- its mean unique stance count is at least `0.5` higher than the corresponding
  shared-context cells; or
- its substantive dissent rate is at least `25` percentage points higher.

### Decision Guardrails

- Gold final stance correctness must not fall by more than `1/12` relative to
  the corresponding shared-context cell.
- Neither calibration case, `SD-11` or `SD-12`, may regress from correct to
  incorrect because of isolation or skill use.
- Any unsafe full endorsement, valid-layer rejection, or stubbornness after new
  evidence is reported as a critical failure.

### Secondary Skill Metrics

- Complete critical boundaries retained by the chair.
- Mean blinded response quality on the existing 14-point rubric.
- Dissent preservation when a minority objection remains materially relevant.
- False unanimity count: all roles appear to agree despite a judge finding a
  substantive unresolved conflict.
- Harmful-compromise flags.

Reality Slap may be credited with a boundary or quality improvement, but it may
not be credited with lowering harmful compromise when both comparison cells
record zero events. A `0 → 0` result is `not estimable`, not a win.

### Cost Metrics

- Prompt characters and output characters per call.
- Wall-clock duration per call and per condition.
- Total generation and judging calls.
- Invalid-output and retry counts.

## Analysis

Report these preregistered contrasts:

1. **Isolation main effect:** pooled isolated cells versus pooled shared cells.
2. **Isolation without skill:** `isolated-control` versus `shared-control`.
3. **Isolation with skill:** `isolated-skill` versus `shared-skill`.
4. **Skill effect under isolation:** `isolated-skill` versus
   `isolated-control`.
5. **Skill effect under shared context:** `shared-skill` versus
   `shared-control`.

Show exact counts and paired case deltas. With only 12 cases, emphasize effect
sizes and disagreement cases rather than relying on asymptotic significance
claims. Separate the conclusions into:

- evidence that isolation created more independent-looking first-round views;
- evidence that the chair made better decisions;
- evidence that Reality Slap improved boundary retention;
- claims the experiment cannot support.

## Failure Handling

The experiment fails closed:

- A timeout, empty response, usage-limit marker, malformed JSON, invalid enum,
  missing field, or out-of-range confidence makes that call incomplete.
- An incomplete role record blocks its chair call.
- No missing result may be replaced with a default, inferred stance, or prior
  output.
- Retries use the same prompt and condition, are capped at one retry, and are
  recorded explicitly.
- The final report is `incomplete` unless all 48 meetings, all isolated role
  records, all chairs, and both blind judging passes are valid.
- Partial data may be reported diagnostically but cannot produce a success
  verdict.

## Artifacts

Implementation should produce:

- A deterministic workspace creator and experiment runner under `scripts/`.
- Focused unit tests under `tests/` for randomization, context isolation,
  schema validation, fail-closed behavior, blinding, and metric calculation.
- Raw execution data under
  `/private/tmp/reality-slap-isolated-roleplay-20260723/`.
- `evals/isolated-context-roleplay-2x2-2026-07-23.json` with machine-readable
  design metadata, exact metrics, condition counts, and limitations.
- `evals/isolated-context-roleplay-2x2-2026-07-23.md` with the human-readable
  method, result, costs, case deltas, and bounded conclusion.
- An `evals/evals.json` metadata entry only after the run is complete and the
  result artifacts pass validation.

## Node Contract

- `node_id`: `isolated-context-roleplay-2x2`
- `inputs`: committed eval bank, committed Reality Slap skill, fixed model and
  reasoning settings, seed, role prompts, chair prompt, and judge rubric.
- `outputs`: complete raw workspace, validated JSON result, Markdown report,
  and optional eval metadata pointer.
- `blocked_output`: machine-readable `incomplete` verdict with missing or
  invalid call identifiers and no causal success claim.
- `release_risk`: an invalid or partially scored run could falsely claim that
  simulated roles are independent or that Reality Slap reduces harmful
  consensus.

## Verification Gates

Before publishing the result:

1. Unit tests for the new runner and analyzer pass.
2. Existing repository unit tests pass.
3. Eval-bank and stance-drift design audits pass.
4. The raw workspace audit confirms complete condition, role, chair, and judge
   coverage.
5. The result JSON validates against its schema and exactly matches report
   headline values.
6. `scripts/check_release_ready.py` passes.
7. `git diff --check` passes and `.agent-lab/` remains untouched.

## Claim Boundary

A positive result would show that separate calls with sealed first-round
contexts produced more diverse substantive stances in this 12-case,
single-model setup. It would not establish human-like independence, generalize
to other models or domains, or prove a lower rare-event harmful-consensus rate.
It also would not establish improvement over the 2026-07-10 `high`-effort run,
because reasoning effort differs.
Reality Slap should be described separately as a decision-boundary guardrail
unless its preregistered isolated-cell contrasts support a stronger claim.
