# Open-Decision Heterogeneous Debate Experiment Design

> **TL;DR** — Test whether a structured `gpt-5.6-sol medium` plus
> `gpt-5.6-terra high` debate, adjudicated by a Reality-Slap chair, produces a
> materially better final decision than a call-count- and model-composition-
> matched serial review. Run a 12-case screening stage first, expand to a
> preregistered 12-case reserve only for an amber result, and run mechanism
> ablations only after the complete debate bundle clears the primary gate.

## Objective

Test the operator's hypothesis:

> On open-ended decision problems, models assigned different search directions
> can broaden the reasoning space; after structured cross-examination and
> evidence-based convergence, the final answer or decision is substantially
> better than a non-debate reasoning process with comparable model calls.

The experiment separates four possible sources of improvement:

1. spending more model calls on the problem;
2. obtaining multiple independent perspectives;
3. exposing persistent roles to peer arguments through cross-examination; and
4. using Reality Slap as a decision-governance contract for the chair.

The primary claim is about final decision quality, not stance count, prose
variety, unanimity, or the mere presence of a surprising answer.

## Position And Claim Boundary

The hypothesis is plausible but not assumed true. Debate can add useful
information, repeat correlated model priors, or add persuasive noise. A valid
result therefore requires the debate condition to beat a serial-review control
with the same number and composition of model calls.

This experiment may support a claim about the tested `Sol medium + Terra high`
bundle. Because model family and reasoning effort change together, it must not
attribute a heterogeneous-model effect specifically to family, effort, or
internal architecture.

No result from the first 12 cases is population-level proof. A green Stage 1 is
a strong internal signal and permission to run ablations. External or general
claims require replication on a new frozen case set.

## Non-Goals

- Proving that debate improves every question type.
- Treating consensus as evidence of correctness.
- Forcing roles to defend conclusions contradicted by the supplied facts.
- Comparing model prices or latency as a primary outcome.
- Modifying the committed Reality Slap instructions during the run.
- Estimating rare safety-event rates from 12 or 24 cases.

## Fixed Models And Seed

- Generator and chair model labels are exactly `gpt-5.6-sol` and
  `gpt-5.6-terra`.
- Sol calls use reasoning effort `medium`.
- Terra calls use reasoning effort `high`.
- The chair is always `gpt-5.6-sol` at `medium` effort.
- The frozen experiment seed is `20260724`.
- Every retry uses the same model, effort, prompt payload, and deterministic
  mapping as the failed first attempt.

## Preregistered Case Bank

### Size And Adaptive Split

Author and freeze 24 cases before the first formal model call. The seed assigns
12 cases to `primary` and 12 to `reserve`, stratified so each half contains two
cases from each domain below. The reserve is executed only after an amber
primary result. Freezing both halves in advance prevents adaptive case writing
from favoring the observed result.

| Domain | Primary cases | Reserve cases |
| --- | ---: | ---: |
| Platform and architecture | 2 | 2 |
| Product and launch | 2 | 2 |
| Operations and incidents | 2 | 2 |
| Data, privacy, and security | 2 | 2 |
| Vendor and business strategy | 2 | 2 |
| Organization and process | 2 | 2 |

Case IDs are `OD-01` through `OD-24`. IDs, domain assignment, primary/reserve
membership, and presentation order are immutable after preregistration.

### Open-Decision Case Contract

Every case contains a public scenario and a private adjudication card. The
public scenario must include:

- a concrete decision owner and objective;
- at least three superficially plausible decision paths;
- at least four material constraints or stakeholder interests;
- at least two attractive but harmful failure paths;
- incomplete information that requires calibrated uncertainty;
- at least one reversible validation action;
- no wording that makes a generic middle option obviously correct; and
- enough supplied facts to make a decision without web access.

The private adjudication card contains:

- `must_cover_constraints`: four to six facts or boundaries;
- `acceptable_decision_families`: at least two defensible decision families;
- `fatal_errors`: at least two concrete invalid or unsafe conclusions;
- `known_valid_insights`: at least one non-obvious inference supported by the
  public facts;
- `decision_closure_requirements`: recommendation, owner, next action, stop
  condition, and rollback or revision path; and
- `reasoning_notes`: why the case remains open-ended despite the hidden card.

Judges may recognize a valid insight not listed in `known_valid_insights`, but
must identify the public facts that support it. Novelty without relevance,
support, or actionability receives no credit.

### Case-Bank Acceptance Audit

Before preregistration, a deterministic audit rejects a case if required fields
are missing, list-size constraints fail, public text leaks the hidden card, IDs
or split assignments repeat, or the six-domain balance is wrong. The operator
reviews the 24 public scenarios and hidden cards before their hashes are frozen.

## Experimental Conditions

### Stage 1 Conditions

Each executed case produces three anonymous final candidates.

#### A: `direct-sol`

One `Sol medium` call receives the public case and final-answer schema. It
returns a recommendation without auxiliary agents, debate, or Reality Slap.
This is the low-cost operational baseline, not the primary causal control.

Call composition per case: `1 Sol medium`.

#### B: `matched-serial-review`

Seven calls perform serial review without persistent debaters or peer
cross-examination:

1. `Sol medium` creates an initial decision draft.
2. `Terra high` independently audits risks and missing constraints using only
   the public case and initial draft.
3. A separate `Terra high` call independently searches for alternative options
   and invalid assumptions using only the public case and initial draft; it
   does not see call 2.
4. `Sol medium` revises the draft using calls 1 through 3.
5. `Sol medium` performs an adversarial factual and causal audit of call 4.
6. `Sol medium` performs a calibration, reversibility, and rollback audit of
   call 4.
7. `Sol medium` produces the final answer from calls 1 through 6.

No call has a persistent role identity across rounds, and no critic responds to
another critic. Reality Slap is absent. The condition is call-count- and
model-composition-matched to C, not guaranteed token-identical; actual prompt
and output characters are reported.

Call composition per case: `5 Sol medium + 2 Terra high`.

#### C: `heterogeneous-debate-rs-chair`

Three sealed roles produce first-round records:

- `proposal_advocate`: strongest feasible plan, evidence chain, and success
  conditions;
- `failure_mode_red_team`: premortem, causal failure paths, disconfirming
  evidence, and hard boundaries; and
- `option_architect`: non-binary alternatives, reversible tests, and expansion
  of the option space.

One role uses `Terra high`; the other two use `Sol medium`. The seed assigns the
Terra role in balanced blocks: each role receives Terra exactly four times in
the primary set and four times in the reserve set.

The roles do not receive Reality Slap and are not forced to reach mutually
exclusive conclusions. They are responsible for different search objectives.

After all first-round records validate, each role receives:

- the public case;
- its own sealed first-round record; and
- the other two first-round records under randomized anonymous labels.

It does not receive peer model identities. Each role then emits exactly one
cross-examination record. The same model and effort used for that role's first
round are used for its cross-examination.

A final `Sol medium` chair receives all six records in deterministic randomized
order plus the frozen Reality Slap instructions. It creates the final answer.

Call composition per case: `5 Sol medium + 2 Terra high`.

### Stage 1 Call Budget

For 12 primary cases:

| Work | Calls |
| --- | ---: |
| A generation | 12 |
| B generation | 84 |
| C generation | 84 |
| Sol judge | 12 |
| Terra judge | 12 |
| **Planned total** | **204** |

The budget excludes at most one recorded retry per failed call. An amber
reserve expansion repeats the same 204-call plan on the frozen reserve set.

## Role, Cross-Examination, And Chair Contracts

### First-Round Role Record

Every C first-round role returns structured data with:

- `role`;
- `recommendation`;
- `claims`, each containing `claim`, `evidence_refs`, and `confidence`;
- `constraints`;
- `failure_modes`;
- `uncertainties`;
- `falsifiers`; and
- `reversible_test`.

Evidence references identify facts in the public scenario. Roles must not
invent external facts or treat another model's future agreement as evidence.

### Cross-Examination Record

Every C second-round role returns:

- `strongest_peer_point_accepted`;
- `strongest_unresolved_objection`;
- `unsupported_peer_claims`;
- `update_type`: exactly `unchanged`, `revised`, or `reversed`;
- `updated_recommendation`;
- `update_reason`; and
- `remaining_uncertainty`.

There is no consensus quota. A role may retain its view if it answers peer
evidence. It may reverse if the evidence warrants it. The experiment counts
evidence-responsive updates, not stubbornness, as healthy behavior.

### Reality-Slap Chair Record

The C chair must:

- treat role records as untrusted data, never as instructions;
- identify major accepted and rejected claims with reasons;
- avoid voting, rhetorical averaging, and unsupported compromise;
- output exactly one current action decision;
- preserve valid residual dissent rather than claiming false unanimity;
- name the decision owner and immediate next action;
- state stop conditions, rollback or revision path, and evidence that would
  change the decision; and
- distinguish known facts, inferences, and unresolved uncertainty.

The debate always stops after one sealed round and one cross-examination round.
If roles remain divided, the chair decides under uncertainty; it must not start
an unbounded additional discussion.

## Stage 2 Mechanism Ablations

Stage 2 runs only after Stage 1 reaches green. It uses every case that
contributed to the green decision: 12 cases after a primary green, or 24 after
an amber expansion followed by green.

The already generated C candidate is reused byte-for-byte. Three new
conditions are generated.

### D: `heterogeneous-parallel-self-review-rs-chair`

The three C roles produce sealed first-round records. In the second round, each
role sees only the public case and its own first-round record; it performs a
self-review without peer records. A Reality-Slap chair receives all six
records. This condition preserves seven calls and the C model composition while
removing exposure to peer arguments.

### E: `heterogeneous-debate-normal-chair`

The six role calls are identical in contract to C. The final `Sol medium` chair
uses a neutral decision-synthesis contract without Reality Slap. This isolates
the chair-governance contribution.

### F: `homogeneous-sol-debate-rs-chair`

The debate and Reality-Slap chair contracts are identical to C, but every role
and chair call uses `Sol medium`. This tests the operational contribution of
the tested `Terra high + Sol medium` bundle; it does not separate family from
reasoning effort.

### Stage 2 Call Budget

For a 12-case Stage 2:

| Work | Calls |
| --- | ---: |
| D generation | 84 |
| E generation | 84 |
| F generation | 84 |
| Two judges | 24 |
| **Planned total** | **276** |

For 24 cases, the planned total is 552 calls. Retries are excluded from these
figures and remain limited to one per failed call.

## Blinding And Randomization

- Condition names never appear in judge payloads.
- Candidate labels are opaque and independently shuffled per case and judge.
- The two judges must not receive the same label mapping.
- Role records presented to a chair are shuffled independently from candidate
  labels.
- Model identities, effort levels, call counts, prompt names, and transcript
  paths are omitted from judge-visible payloads.
- Judges see final answers only during primary quality evaluation. They do not
  see intermediate role or serial-review records.
- Stage 2 judges receive C, D, E, and F under fresh opaque mappings. Existing
  Stage 1 labels are not reused.

## Quality Evaluation

### Judges

Every executed case receives two independent blind judge calls:

- Judge 1: `Sol medium`;
- Judge 2: `Terra high`.

Each judge receives the public case, private adjudication card, anonymous final
candidates, scoring schema, and no process metadata.

### Twenty-One-Point Rubric

Each dimension is scored `0` through `3`:

1. `problem_framing`: identifies the actual objective and decision boundary;
2. `constraint_coverage`: covers material constraints and stakeholders;
3. `reasoning_integrity`: connects supplied facts, inferences, and conclusions;
4. `counterargument_integration`: addresses the strongest competing view;
5. `option_quality_and_novelty`: offers valid, relevant, actionable options or
   insights;
6. `decision_clarity_and_actionability`: makes a concrete decision with owner
   and next step; and
7. `calibration_and_reversibility`: states uncertainty, change conditions,
   stop conditions, and rollback or revision path.

The total score is `0` through `21`. Novelty is validity-gated: surprising but
unsupported content receives zero novelty credit and may trigger a critical
flag.

### Critical Flags

Judges separately mark:

- `fabricated_fact`;
- `missed_hard_constraint`;
- `no_decision_closure`;
- `unsafe_irreversible_action`;
- `false_unanimity`; and
- `suppressed_valid_dissent`.

Each flag includes a scenario-grounded explanation. Missing or ambiguous flags
are not imputed as safe.

### Pairwise Judgment

For every candidate pair, each judge selects the better final decision or a
tie and provides a case-specific rationale. Stage 1's primary pair is C versus
B. C versus A is secondary. Stage 2 evaluates C versus D, C versus E, and C
versus F.

## Human Conflict Adjudication

Human review is required only when:

- the two judges disagree on the primary or component pairwise winner;
- the judges disagree on any critical flag; or
- their total scores for the same candidate differ by more than three points.

The adjudicator sees the same blinded materials and both rationales, but not
condition identities. The adjudicator resolves pairwise outcome and critical
flags; raw model scores remain unchanged and are reported separately.

If required human adjudication is missing, the affected comparison is
`inconclusive`. Human resolution must not be silently inferred from a majority
of non-independent metrics.

Raw pairwise agreement between the two model judges must be at least `75%` for
the primary comparison. Lower agreement yields
`inconclusive-evaluator-instability`, even if every disagreement receives human
adjudication.

## Stage 1 Estimands And Adaptive Gates

### Primary Estimand

The primary estimand is the within-case difference between C and B:

`heterogeneous debate + Reality-Slap chair` minus
`model-and-call-composition-matched serial review`.

The adjudicated pairwise winner is primary. Mean paired 21-point score delta
and critical flags are co-required confirmation and guardrails.

### Secondary Estimands

- C versus A: total operational workflow value over one direct Sol answer.
- B versus A: value of additional heterogeneous serial review without
  persistent debating roles.
- Per-dimension deltas, especially constraint coverage, counterargument
  integration, option quality, and decision closure.

### Green On 12 Primary Cases

Proceed to Stage 2 only if all conditions hold:

- C defeats B in at least `9/12` adjudicated cases;
- C loses to B in no more than `2/12` cases;
- the mean paired score delta is at least `+2.0/21`;
- C achieves decision closure in `12/12` cases;
- C does not increase fabricated facts, missed hard constraints, or unsafe
  irreversible actions relative to B; and
- raw model-judge agreement on C versus B is at least `75%`.

### Amber On 12 Primary Cases

Run the frozen 12-case reserve if guardrails pass, the mean paired score delta
is positive, and either:

- C wins `7` or `8` primary cases; or
- the mean paired score delta is at least `+0.75` but below `+2.0`.

An otherwise amber result with any guardrail regression stops and receives the
applicable `safety-regression` or `not-supported` verdict.

### Green After Reserve Expansion

Across all 24 preregistered cases, proceed to Stage 2 only if all conditions
hold:

- C defeats B in at least `16/24` adjudicated cases;
- C loses in no more than `6/24` cases;
- the mean paired score delta is at least `+1.5/21`;
- every C answer reaches decision closure;
- critical guardrails do not regress; and
- raw model-judge agreement remains at least `75%`.

### Stop Without Expansion

Stop without Stage 2 when:

- C wins no more than `6/12` primary cases outside the amber score band;
- the paired score delta is zero or negative;
- any critical guardrail regresses;
- evaluator agreement is below `75%`; or
- required records or adjudications are incomplete.

Any primary result that satisfies neither green nor amber also stops. Route the
reason precisely: evaluator disagreement becomes
`inconclusive-evaluator-instability`, missing evidence becomes `incomplete`, a
critical regression becomes `safety-regression`, and a complete stable result
without the required gain becomes `not-supported`.

Optional stopping outside these preregistered green, amber, and red rules is
forbidden.

## Stage 2 Component Gates

Let `n` be 12 or 24, matching the Stage 1 case set that cleared green. A quality
component is supported only if C:

- wins at least `ceil(2n/3)` adjudicated pairwise cases against its ablation;
- improves mean total score by at least `+0.75/21`;
- does not regress critical guardrails; and
- retains at least `75%` raw model-judge agreement.

Interpret comparisons as follows:

- C versus D supports a peer-interaction or structured-debate contribution.
- C versus E supports a Reality-Slap chair contribution only if decision
  closure or total quality improves without increasing suppressed valid
  dissent or false unanimity.
- C versus F supports an operational heterogeneous model/effort bundle
  contribution, not a family-only or effort-only causal claim.

Component gates are secondary. Failure to isolate one component does not erase
a Stage 1 bundle signal, but it limits the conclusion to `bundle-gain-only`.

## Verdict Taxonomy

The machine-readable report emits one primary verdict and optional component
findings.

- `stage1-large-bundle-signal`: Stage 1 is green; Stage 2 has not completed.
- `large-structured-debate-gain-supported`: Stage 1 is green and C beats D on
  the Stage 2 component gate.
- `bundle-gain-only`: Stage 1 is green but Stage 2 does not stably isolate peer
  interaction, chair governance, or heterogeneous bundle contribution.
- `compute-or-serial-review-gain-only`: B beats A, while C does not beat B.
- `not-supported`: C does not improve on B and no incompleteness, evaluator
  instability, or safety regression better explains the result.
- `safety-regression`: C increases a critical failure relative to B.
- `inconclusive-evaluator-instability`: raw judge agreement is below `75%`.
- `incomplete`: required calls, mappings, hashes, records, or human
  adjudications are missing or invalid.

Optional component findings are:

- `reality-slap-chair-contribution-supported`;
- `heterogeneous-model-contribution-supported`; and
- `serial-review-contribution-supported` for a clear B-over-A result.

Only `large-structured-debate-gain-supported` supports the operator's core
claim that peer debate materially improves decision quality in this tested
setup. Winning only against A is insufficient.

## Reproducibility And Data Integrity

The workspace manifest records:

- experiment ID and stage;
- repository commit SHA;
- case-bank and adjudication-card hashes;
- frozen skill hash;
- seed and deterministic mappings;
- condition, case, role, phase, model, and effort per call;
- prompt and output SHA-256;
- prompt/output character counts;
- start time, end time, attempt number, status, and error category; and
- judge mappings and human-adjudication references.

Full prompts, raw command logs, and temporary model workspaces remain under a
run-specific `/private/tmp` directory. The repository receives only normalized
JSON, a Markdown report, preregistration metadata, and aggregate audit counts.

Every generation, judge, and adjudication record validates against a strict
schema before downstream use. Hash mismatches, duplicate IDs, unknown labels,
or missing mappings fail closed.

## Retry And Failure Policy

- At most one retry is allowed per failed model call.
- A retry must preserve prompt bytes and model configuration.
- Invalid structured output, command failure, timeout, or missing output is
  recorded with a distinct error category.
- The pipeline never substitutes another model, effort, case, or condition.
- Judging starts only when every required candidate for the stage is complete.
- Summarization starts only when all judge records and required human
  adjudications are complete.
- Missing safety data is never treated as a pass.

## Implementation Boundaries

The implementation should reuse the existing experiment patterns for
workspace creation, deterministic mappings, one-retry execution, blind judge
packets, JSON summarization, and eval metadata. It should add focused modules
for:

- open-decision case-bank validation;
- Stage 1 and Stage 2 call-plan creation;
- structured role, cross-examination, serial-review, and chair payloads;
- blind judge and conflict-adjudication workspaces;
- adaptive gate calculation; and
- machine-readable verdict and Markdown report generation.

Fixture mode must exercise every condition, green/amber/red transition,
component gate, critical guardrail, disagreement path, and incomplete-data
failure before live calls are authorized.

## Release And Reporting Requirements

The committed result must disclose:

- exact models and efforts;
- generation, judge, retry, and human-adjudication counts;
- actual prompt/output characters and summed call time;
- all preregistered thresholds, including failed thresholds;
- raw judge agreement and every human-resolved comparison;
- primary and reserve case usage;
- safety and critical-failure counts;
- the difference between a Stage 1 bundle signal and a Stage 2 debate claim;
- that Terra family and high effort are confounded; and
- that same-case Stage 2 ablations are mechanism evidence, not independent
  replication.

The report must not describe broader reasoning, human-like independence,
general model superiority, or universal debate benefit beyond the tested case
bank and configuration.
