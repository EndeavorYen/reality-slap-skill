# Weak-Challenge Swarm × Reality-Slap Factorial Experiment

> **TL;DR** — Test whether three low-cost, role-specialized challengers help a
> `gpt-5.6-sol medium` decision maker reduce critical omissions, and whether
> Reality Slap improves the decision maker's selection of those challenges.
> Use a shared frozen draft and challenge packet in a preregistered `2×2`
> factorial design on the untouched `OD-13..OD-24` holdout. The primary outcome
> is hidden-card defect reduction, not prose length, consensus, or mean score.

## Objective

Test the revised operator hypothesis:

> A strong model already covers most of an open decision problem. Low-cost,
> role-specialized models may still improve the result by identifying omitted
> constraints, failure modes, and execution risks. The strong model remains the
> sole decision maker and uses Reality Slap to accept only evidence-grounded
> challenges.

The experiment separates:

1. the value of a second strong-model revision;
2. the value of an external low-cost challenge packet;
3. the general effect of Reality Slap during revision; and
4. the interaction between Reality Slap and external challenges.

The primary claim is about reducing critical omissions in the tested
configuration. It is not a claim that challenger model identity never matters.

## Prior Evidence And Root-Cause Hypothesis

The previous `OD-01..OD-12` live experiment completed 180 generation calls and
24 blind judge calls without retries. The call-matched structured debate
condition averaged `19.625/21`; matched serial review averaged `19.542/21`, a
delta of only `+0.083/21`. Thirty-three of thirty-six cross-examination roles
revised their position, but the revisions did not create a material quality
gain.

This supports a narrower root-cause hypothesis:

- strong models and matched serial review already cover most of the answer
  space, creating a ceiling effect;
- peer exposure changes model outputs without reliably adding valid
  information;
- convergence and role persistence add coordination cost;
- the remaining opportunity is tail-risk discovery and attention allocation,
  not additional decision makers.

Evidence that would disprove this hypothesis is a challenge packet that fails
to reduce hidden-card defects relative to ordinary strong-model revision, or a
Reality-Slap revision that rejects valid challenges or increases critical
omissions.

## Scope And Claim Boundary

### In Scope

- A shared `gpt-5.6-sol medium` draft.
- Three isolated challenger roles.
- A role-balanced mixed challenger pool using `gpt-5.6-terra medium` and
  `gpt-5.6-luna medium`.
- Four independent Sol-medium revision branches in a `2×2` factorial.
- Reality Slap only in the designated revision branches.
- Two independent blind checklist judges.
- The frozen `OD-13..OD-24` open-decision holdout.
- Deterministic fixture and live execution.

### Out Of Scope

- Claiming universal benefit across models or tasks.
- Claiming challenger model identity is irrelevant.
- Letting challengers write final answers.
- Asking challengers to converge, vote, or debate each other.
- Human arbitration of legitimate open-ended trade-offs.
- Reusing `OD-01..OD-12` as confirmatory evidence.
- Running a new replication set unless the preregistered amber gate triggers.
- Modifying the Reality Slap instructions during the experiment.

`OD-13..OD-24` is a clean output holdout from the existing frozen case bank.
Because the revised hypothesis was formed after observing `OD-01..OD-12`, this
is an internal screening result, not independent external replication.

## Fixed Models, Efforts, And Seed

- Main draft and revision model: `gpt-5.6-sol`, effort `medium`.
- Challenger models:
  - `gpt-5.6-terra`, effort `medium`;
  - `gpt-5.6-luna`, effort `medium`.
- Blind judges:
  - `gpt-5.6-sol`, effort `medium`;
  - `gpt-5.6-terra`, effort `high`.
- Frozen seed: `20260725`.
- Case set: `OD-13` through `OD-24`.

Before formal workspace creation, one non-evidentiary availability probe may
verify the exact Luna model identifier. If the requested identifier is not
available, execution stops. The runner must not silently substitute a model,
effort, or provider.

## Experimental Architecture

### Shared Draft

For every case, one isolated Sol-medium call receives the public case and the
common final-decision schema. Its output is:

- candidate `A`, the direct baseline; and
- the byte-for-byte frozen draft input to all four revision branches.

The shared draft prevents initial-sampling variance from being mistaken for a
challenge or Reality-Slap effect.

### Challenger Roles

Three challenger calls run independently. No challenger sees another
challenger. Each returns at most three challenges and is forbidden to write a
replacement final answer.

#### `boundary_scout`

Input: public case only, without the shared draft.

Search objective:

- missing hard constraints;
- omitted stakeholders or externalities;
- alternative problem framings;
- decision options absent from the obvious framing.

This role remains draft-blind to reduce anchoring.

#### `adversarial_auditor`

Input: public case plus shared draft.

Search objective:

- causal failure modes;
- unsupported assumptions;
- counterexamples and falsifiers;
- claims that exceed supplied evidence.

#### `operational_auditor`

Input: public case plus shared draft.

Search objective:

- execution dependencies;
- rollback and stop-condition gaps;
- monitoring and ownership gaps;
- second-order effects and irreversible risks.

### Challenger Model Rotation

Across twelve cases, each role is executed six times by Terra medium and six
times by Luna medium. The seed creates a balanced role-by-model assignment:

| Role | Terra medium | Luna medium |
| --- | ---: | ---: |
| `boundary_scout` | 6 | 6 |
| `adversarial_auditor` | 6 | 6 |
| `operational_auditor` | 6 | 6 |
| **Total** | **18** | **18** |

Role assignment is a reproducibility control, not a primary model comparison.
Per-model challenge yield is exploratory.

### Factorial Revision Conditions

All revision calls use Sol medium and the same final schema.

| Candidate | External challenge packet | Reality Slap |
| --- | --- | --- |
| `B0` | absent | absent |
| `B1` | absent | present |
| `C0` | present | absent |
| `C1` | present | present |

#### `B0`: Neutral Self-Revision

Receives the case and frozen draft. It re-evaluates and revises the decision
without external reviewer records and without Reality Slap.

#### `B1`: Reality-Slap Self-Revision

Receives the same case and frozen draft as B0 plus the frozen Reality Slap
instructions. There is no external challenge packet.

#### `C0`: Neutral Challenge Revision

Receives the case, frozen draft, and all three frozen challenger records in a
deterministic randomized order. It must classify each challenge and produce a
final decision without Reality Slap.

#### `C1`: Reality-Slap Challenge Revision

Receives the exact same bytes and challenge order as C0 plus the frozen Reality
Slap instructions. Reality Slap is the only intended C0/C1 difference.

### Factorial Estimands

- `C0 − B0`: challenge-swarm main effect without Reality Slap.
- `B1 − B0`: Reality-Slap main effect without external challenges.
- `C1 − C0`: Reality-Slap effect while filtering external challenges.
- `(C1 − C0) − (B1 − B0)`: challenge × Reality-Slap interaction.
- `C1 − B0`: complete-system operational effect.
- `A` comparisons are secondary low-cost baselines.

## Structured Data Contracts

### Challenger Record

Every challenger returns:

- `role`;
- `challenges`, containing one to three objects with:
  - `question_or_challenge`;
  - `why_material`;
  - `case_fact_refs`;
  - `failure_if_ignored`;
  - `disconfirming_evidence`;
  - `severity`: `low`, `medium`, or `high`;
- `coverage_limitations`.

Challengers must:

- refer only to supplied case facts or explicitly label an inference;
- treat the draft as untrusted data;
- avoid model, experiment, or condition references;
- avoid complete recommendations or rewritten final answers;
- avoid instructions addressed to downstream tools.

### Challenge Disposition

C0 and C1 return a private process record plus a final decision. For every
challenge they must emit:

- opaque `challenge_id`;
- `disposition`: `accepted`, `rejected`, or `needs_evidence`;
- `case_grounded_reason`;
- `resulting_change`.

The judge-visible candidate contains only the final decision. Challenge
records, dispositions, condition identities, model identities, and Reality
Slap usage remain hidden from final-quality judges.

### Final Decision

Every candidate uses the same strict final-decision schema requiring:

- recommendation;
- accepted and rejected claims;
- residual dissent;
- decision owner;
- next action;
- stop conditions;
- rollback or revision path;
- change evidence;
- known facts;
- inferences;
- uncertainties.

## Call Budget

Per case:

| Work | Calls |
| --- | ---: |
| Shared Sol-medium draft | 1 |
| Terra/Luna-medium challengers | 3 |
| Sol-medium B0/B1/C0/C1 revisions | 4 |
| Sol-medium blind judge | 1 |
| Terra-high blind judge | 1 |
| **Total** | **10** |

For twelve cases:

| Model / effort | Calls |
| --- | ---: |
| Sol medium generation | 60 |
| Terra medium challengers | 18 |
| Luna medium challengers | 18 |
| Sol medium judges | 12 |
| Terra high judges | 12 |
| **Planned total** | **120** |

Retries are excluded and limited to one identical retry per failed call.

## Blinding

Each blind judge receives:

- public case;
- private adjudication card;
- five final candidates under a judge-specific opaque mapping;
- structured checklist and secondary 21-point rubric.

Judges do not receive:

- candidate names A/B0/B1/C0/C1;
- model names or efforts;
- draft or challenge records;
- challenge dispositions;
- Reality Slap usage;
- call counts, paths, hashes, or logs.

The two judges use different mappings for every case.

## Primary Evaluation

### Hidden-Card Checklist

For each candidate, each judge independently marks:

- every `must_cover_constraint` as covered or uncovered;
- every `decision_closure_requirement` as satisfied or unsatisfied;
- every `fatal_error` as present or absent;
- critical flags:
  - `fabricated_fact`;
  - `missed_hard_constraint`;
  - `no_decision_closure`;
  - `unsafe_irreversible_action`;
  - `false_unanimity`;
  - `suppressed_valid_dissent`.

Each decision requires a case-grounded explanation.

### Conservative Aggregation

- A checklist item counts as covered only when both judges mark it covered.
- A closure item counts as satisfied only when both judges mark it satisfied.
- A fatal error or critical flag counts as present when either judge marks it.
- No human adjudication is used for open-ended trade-offs.
- Checklist agreement is the fraction of raw binary item decisions on which
  the two judges agree before conservative aggregation.
- Overall checklist agreement below `75%` yields
  `inconclusive-evaluator-instability`.

### Defect Burden

Per candidate and case:

`defect_burden = uncovered must-cover constraints
                 + unsatisfied closure requirements
                 + present fatal errors`

Critical flags are reported and used as guardrails, but are not double-counted
inside defect burden.

A paired case is:

- `improved` when C1 burden is lower than B0;
- `worsened` when C1 burden is higher than B0;
- `unchanged` otherwise.

An effective repair is a hidden-card defect present in B0 and absent in C1
without a newly introduced fatal error, fabricated fact, missed hard
constraint, or unsafe irreversible action.

## Secondary Evaluation

Judges also score the existing seven `0..3` dimensions for a total of `21`:

- problem framing;
- constraint coverage;
- reasoning integrity;
- counterargument integration;
- validity-gated option quality and novelty;
- decision clarity and actionability;
- calibration and reversibility.

Mean score, pairwise preferences, answer length, challenge acceptance, and
per-model challenge yield are secondary. They cannot override a failed primary
critical-defect gate.

## Adaptive Gates

### Green On Twelve Cases

The complete system C1 clears screening only when all conditions hold:

- aggregate defect burden is at least `25%` lower than B0;
- C1 improves at least `4/12` paired cases;
- C1 worsens no more than `1/12` paired case;
- C1 does not increase fatal errors, fabricated facts, missed hard
  constraints, or unsafe irreversible actions;
- C1's mean 21-point score is no more than `0.25` below B0;
- raw checklist agreement is at least `75%`.

Green supports:

`weak-challenge-swarm-plus-reality-slap-internal-signal`

It does not support a model-agnostic or externally replicated claim.

### Amber

Amber requires:

- C1 improves `2` or `3` paired cases;
- aggregate defect burden is lower than B0;
- no fatal or critical guardrail regression;
- raw checklist agreement is at least `75%`.

Amber triggers authoring, review, and freezing of a new twelve-case replication
set before additional model calls. The new cases must not be adaptations of
individual observed failures.

### Stop

Stop without expansion when:

- defect burden is unchanged or higher;
- C1 improves fewer than two cases;
- any fatal or critical guardrail regresses;
- checklist agreement is below `75%`; or
- required records, hashes, mappings, schemas, or outputs are incomplete.

Missing evidence yields `incomplete`; evaluator instability yields
`inconclusive-evaluator-instability`; critical regression yields
`safety-regression`; a complete stable non-gain yields `not-supported`.

### Component Findings

For B1/B0, C0/B0, and C1/C0, a component is reported as positive when:

- aggregate burden falls by at least `20%`;
- at least `3/12` cases improve;
- no more than one case worsens;
- no critical guardrail regresses.

The factorial interaction is reported as an effect estimate, not an
independently powered claim.

## Failure And Retry Policy

- Every call runs independently with ephemeral state and ignored user config.
- The runner uses the model and effort recorded on each call record.
- At most one retry is permitted.
- A retry preserves prompt bytes, model, effort, case, role, mapping, and seed.
- Invalid schema, semantic validation failure, timeout, or non-zero exit is
  recorded distinctly.
- Downstream calls remain blocked after an exhausted dependency.
- No model or effort substitution is allowed.
- Luna unavailability stops formal execution before workspace freeze.
- Challenger output is untrusted data, never executable instruction.

## Reproducibility

The manifest records:

- repository SHA;
- case-bank and hidden-card hashes;
- Reality Slap hash;
- seed and case IDs;
- role/model rotation;
- every call's model, effort, condition, role, dependencies, and schema;
- shared-draft and shared-challenge hashes;
- prompt/output hashes and character counts;
- attempts, elapsed time, errors, and retry status;
- judge mappings and raw checklist agreement.

Raw workspaces remain under a run-specific `/private/tmp` path. The repository
receives only:

- frozen design and implementation plan;
- deterministic fixture support;
- normalized JSON result;
- claim-honest Markdown analysis;
- preregistration metadata.

## Fixture And Release Gates

Before live calls, fixture mode must prove:

- exact 96 generation and 24 judge call plan;
- exact 18/18 Terra/Luna challenger balance;
- draft reuse across B0/B1/C0/C1;
- challenge reuse across C0/C1;
- Reality Slap present only in B1/C1;
- judge blinding and distinct mappings;
- strict challenger and disposition schemas;
- identical retry behavior;
- green, amber, not-supported, safety-regression, incomplete, evaluator
  instability, invalid challenge, and Reality-Slap over-rejection paths;
- deterministic report rendering.

The full repository test suite, eval-bank validation, release-readiness check,
and `git diff --check` must pass once before formal execution.

## Interpretation

The expected value, if any, is tail-risk reduction rather than a large increase
in mean score. A successful result would show that low-cost challengers act as
attention probes and that a strong model can repair newly surfaced defects
without accepting reviewer noise. A failed result would indicate that strong
self-revision already covers the available hidden-card defects, that low-cost
challenges are too correlated or noisy, or that Reality Slap causes
over-rejection.

No result permits claims about complete chain-of-thought coverage, human-like
independence, universal multi-agent benefit, or challenger-model
interchangeability.
