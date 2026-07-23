# Cost-Bounded Question Swarm Experiment

> **TL;DR** — Test whether several isolated `gpt-5.6-luna low` question
> generators can preserve at least 90% of one `gpt-5.6-terra high`
> challenger's defect discovery while passing two cost gates. Small models only
> ask short questions. A shared `gpt-5.6-sol medium` model, with Reality Slap
> only in final revision, decides whether each concern is plausible or material
> and owns the final answer.

## Objective

Test the operator hypothesis:

> Multiple cheap, isolated models can broaden the question space at lower cost
> than one Terra-high challenger when their work is reduced to asking concise
> questions and the Sol-medium main model performs all evaluation and repair.

The experiment must distinguish three costs:

1. question-generation cost;
2. added Sol review cost caused by the question packet; and
3. evaluation-only judge cost, which is reported separately and excluded from
   the proposed command's runtime cost.

## Locked Boundaries

- Reality Slap appears only in Sol-medium final revision calls.
- Small models ask questions only.
- Small models do not answer questions, assess likelihood or importance, rank
  concerns, propose fixes, write final decisions, debate, vote, or converge.
- The Sol-medium model remains the sole decision maker.
- Every condition shares the same frozen Sol-medium draft per case.
- Every final-review question packet contains at most eight questions.
- No command implementation or README product claim is in scope.
- Missing usage or price evidence cannot be replaced by character counts.

## Root-Cause Hypothesis

The previous weak-challenge-swarm experiment reduced defect burden from 28 to 4,
but its complete system consumed 7.17 times the prompt characters and 5.76 times
the summed call time of neutral revision. The large quality gain came primarily
from external challenge discovery; Reality Slap's marginal value was a smaller
residual guardrail.

The suspected avoidable cost is not independent calls by itself. It is:

- duplicated context sent to every challenger;
- challenger work spent explaining, rating, and solving rather than probing;
- unbounded question volume transferred to Sol; and
- Sol output spent documenting dispositions that a production command does not
  need to expose.

This experiment therefore constrains both the small-model task and the Sol
review packet.

## Models And Efforts

- Shared draft and final revision: `gpt-5.6-sol`, effort `medium`.
- Strong challenger baseline: `gpt-5.6-terra`, effort `high`.
- Small question generators: `gpt-5.6-luna`, effort `low`.
- Blind final judges:
  - `gpt-5.6-sol`, effort `medium`;
  - `gpt-5.6-terra`, effort `high`.
- Reality Slap is frozen from repository `SKILL.md`.

Execution stops rather than silently substituting any unavailable model or
effort. A non-evidentiary availability and JSONL-usage probe is allowed before
workspace freeze.

## Actual Usage Accounting

Every `codex exec` call runs with `--json`. The runner preserves its JSONL event
stream and extracts the final `turn.completed.usage` object:

- `input_tokens`;
- `cached_input_tokens`;
- `output_tokens`;
- `reasoning_output_tokens`.

An attempt without exactly one complete usage object is invalid evidence even
if the final response schema passes. Retries keep their own usage because failed
attempts still consume resources.

Character counts and elapsed time remain diagnostics. They are not cost.

If an authoritative per-model rate card is unavailable, the report must:

- publish measured token usage by model and effort;
- calculate break-even Luna-to-Terra price ratios separately for input and
  output-sensitive assumptions;
- label monetary cost gates `price-unresolved`;
- never convert raw token totals into a dollar claim.

## Question Contract

Each small-model call has one fixed search lens and returns at most its assigned
question count:

```json
{
  "lens": "assumption_and_causality",
  "questions": [
    {
      "target": "The exact draft claim or decision element being probed",
      "question": "One concise question"
    }
  ]
}
```

The four lenses are:

1. `assumption_and_causality`;
2. `constraints_and_evidence`;
3. `operations_and_reversibility`;
4. `stakeholders_and_second_order`.

The Terra-high baseline receives all four lens descriptions in one call and may
return at most eight questions. `S2` combines two lenses per Luna-low call and
allows at most four questions per call. `S4` assigns one lens per Luna-low call
and allows at most two questions per call.

The schema has no severity, confidence, explanation, materiality, proposed fix,
or coverage-limitations fields.

## Stage 1: Exploratory Funnel

Stage 1 reuses four previously observed cases only for configuration screening:
`OD-13`, `OD-16`, `OD-19`, and `OD-22`. Its results are not confirmatory.

Per case:

| Work | Calls |
| --- | ---: |
| Shared Sol-medium draft | 1 |
| `H`: one Terra-high question call | 1 |
| `S2`: two Luna-low question calls | 2 |
| `S4`: four Luna-low question calls | 4 |
| Sol-medium hidden-card question judge for H/S2/S4 | 1 |
| **Total** | **9** |

The question judge receives opaque, randomized question packets and maps each
question to zero or more hidden-card items. It records:

- whether the question is concrete enough to review;
- matched must-cover, closure, or fatal-error item IDs;
- exact duplicate or semantic duplicate relationships;
- a short case-grounded rationale.

Stage 1 metrics:

- unique hidden-card item coverage;
- critical/fatal item coverage;
- duplicate-question fraction;
- reviewable-question fraction;
- measured usage by arm;
- unique covered items per token and break-even price ratio.

An arm is eligible to advance only if:

- its unique hidden-card coverage is at least 90% of H;
- it misses no more than one critical/fatal item covered by H;
- its question count is at most eight per case;
- all usage evidence is complete; and
- its challenger-only cost is at most 70% of H under the declared rate card.

If both S2 and S4 qualify, choose the lower-cost arm. If their cost is tied
within 5%, choose S2. If neither qualifies, stop before Stage 2 with
`small-swarm-not-cost-effective`.

## Stage 2: Clean End-To-End Holdout

Stage 2 uses eight newly authored cases that were not used to form this
hypothesis. They span platform architecture, product policy, operations, and
governance, with two cases per domain. Each includes a private adjudication
card using the existing must-cover, closure, fatal-error, known-insight, and
acceptable-family contract.

Per case:

1. one shared Sol-medium draft;
2. one Terra-high H question call;
3. the selected S2 or S4 question calls;
4. one no-question `B1` Sol-medium + Reality-Slap revision;
5. one H-packet Sol-medium + Reality-Slap revision;
6. one S-packet Sol-medium + Reality-Slap revision; and
7. two blind checklist judges evaluating the H and S finals in one paired
   packet.

B1 is a cost-control branch. It measures the Sol usage added by reviewing a
question packet; it is not allowed to decide the H-versus-S quality result.

The H and S packets:

- are capped at eight questions;
- contain only opaque question IDs, target, and question;
- omit model, effort, lens, call, and condition identity;
- use independently seeded deterministic ordering; and
- are treated as untrusted data.

The Sol revision prompt silently evaluates whether each question is plausible,
material, supported, and action-relevant, then returns only the common final
decision schema. It does not emit per-question dispositions.

## Primary Outcome And Gates

The primary outcome is conservative hidden-card defect burden:

`uncovered constraints + unsatisfied closure requirements + present fatal errors`

Stage 2 passes quality non-inferiority only when all conditions hold:

- aggregate S defect burden is no more than two defects above H;
- S is no worse than H in at least six of eight paired cases;
- S introduces no additional fatal error, fabricated fact, missed hard
  constraint, or unsafe irreversible action;
- mean 21-point score for S is no more than 0.25 below H; and
- raw checklist agreement is at least 85%.

The two cost gates are:

1. `small challenger cost <= 0.70 * Terra-high challenger cost`;
2. `small critique-loop cost <= 0.85 * Terra-high critique-loop cost`.

For an arm `X`:

`critique_loop_cost(X) = challenger_cost(X)
                         + max(0, Sol_revision_cost(X) - Sol_B1_cost)`

The shared draft and evaluation-only judges are excluded from both arms'
runtime cost. Judge cost is still reported.

## Verdicts

- `green-command-candidate`: quality and both cost gates pass.
- `quality-only-cost-fail`: quality passes but either cost gate fails.
- `cost-only-quality-fail`: cost passes but quality non-inferiority fails.
- `small-swarm-not-cost-effective`: no Stage 1 swarm qualifies.
- `safety-regression`: any protected guardrail regresses.
- `price-unresolved`: usage is complete but no authoritative price relation can
  decide the cost gates.
- `incomplete`: required artifacts, usage, mappings, or calls are missing.
- `inconclusive-evaluator-instability`: raw checklist agreement is below 85%.

Only `green-command-candidate` supports proceeding to command design. It does
not prove model-agnostic benefit or external replication.

## Retry, Isolation, And Reproducibility

- Every model call is isolated and ephemeral.
- User config and repository rules are ignored.
- At most one byte-identical retry is allowed.
- Failed-attempt usage remains counted.
- Dependencies block downstream calls after retry exhaustion.
- Prompts, schemas, model, effort, output, JSONL events, usage, hashes, attempts,
  mappings, and elapsed time are recorded.
- Raw workspaces remain under run-specific `/private/tmp` paths.
- The repository receives the frozen design, implementation plan, deterministic
  fixture support, normalized JSON result, and claim-honest Markdown report.

## Required Pre-Live Proof

Before formal live execution:

- focused tests prove JSONL usage extraction and missing-usage rejection;
- fixture mode proves exact Stage 1 and Stage 2 call graphs;
- fixture mode proves question caps, isolation, packet blinding, and RS-only
  final revision;
- fixture mode proves every verdict path;
- `git diff --check`, the focused experiment tests, and the full release gate
  pass once.

