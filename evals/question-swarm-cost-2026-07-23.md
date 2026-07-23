# Cost-Bounded Question-Swarm Confirmation Result

## Outcome

`S2` did **not** pass the production gate. Its ordinary quality was effectively
non-inferior to one Terra-high challenger, but it missed one hard constraint
that H caught. The fail-closed verdict is `safety-regression`.

The useful result is narrower: two Luna-low question calls can approach one
Terra-high challenger on broad decision quality, but the tested mechanism
cannot yet replace it safely or prove a cost saving.

## Frozen comparison

For each of eight new holdout cases:

1. Sol-medium produced one shared draft.
2. H used one isolated Terra-high call for at most eight questions.
3. S used two isolated Luna-low calls for four questions each.
4. Sol-medium revised the shared draft with Reality Slap applied only at this
   final review step.
5. Independent Sol-medium and Terra-high judges compared anonymous H/S answers
   against hidden checklists.

The no-question B1 revision was retained for review-cost accounting but was not
included in the H/S quality ranking.

## Quality gates

| Gate | Required | Observed | Result |
| --- | ---: | ---: | --- |
| Defect burden delta, S−H | ≤ +2 | 0 (22 vs 22) | pass |
| Non-worse cases | ≥ 6/8 | 7/8 | pass |
| Mean score delta, S−H | ≥ −0.25 | 0.000 (11.4375 vs 11.4375) | pass |
| Raw checklist agreement | ≥ 85% | 91.3% | pass |
| Guardrail regression | none | one extra missed hard constraint | **fail** |

Paired defect-burden outcomes:

| Case | S−H burden | Outcome |
| --- | ---: | --- |
| QS-01 | 0 | same |
| QS-02 | 0 | same |
| QS-03 | 0 | same |
| QS-04 | −1 | S better |
| QS-05 | +2 | S worse |
| QS-06 | −1 | S better |
| QS-07 | 0 | same |
| QS-08 | 0 | same |

Neither arm triggered a fatal error, fabricated fact, or unsafe irreversible
action. H had one missed-hard-constraint flag; S had two.

## Root cause

The decisive miss occurred in QS-05, database recovery after partial replica
corruption.

The Terra-high challenger asked how writes were frozen across every writer,
queue, retry worker, and external integration. The H revision then explicitly
quiesced those delayed-write paths before recovery. Neither Luna question call
raised that cross-system issue, and the S revision only kept traffic read-only;
it did not close the delayed-writer contamination path or fully define the
write-reenable sequence.

The no-question B1 answer also omitted this detail. Therefore the evidence does
not show that the Luna questions damaged an otherwise safe answer. It shows
that S2 failed to add a safety-relevant insight that the integrated Terra call
did add.

This exposes a mechanism boundary: splitting critics by lens increases local
variety, but nobody owns cross-lens completeness. A constraint can sit between
operations, evidence, and reversibility and be missed by both specialists.
Reality Slap cannot recover an absent challenge by itself; it disciplines the
main model's treatment of supplied claims and dissent, not exhaustive recall
of every operational dependency.

## Measured cost

| Work | H path | S path |
| --- | ---: | ---: |
| Challenger weighted tokens | 127,030 | 228,904 |
| Sol revision weighted tokens | 188,045 | 191,916 |
| Review increment over B1 | 8,231 | 12,102 |

S used 1.80 times as many challenger weighted tokens because two isolated calls
each reread the context. It satisfies the 70% challenger-cost target only if a
Luna token costs at most 38.85% of a Terra token.

For the full critique loop, the maximum Luna/Terra unit-price ratio that meets
the 85% target ranges from 42.71% to 46.61% as the Sol/Terra unit-price ratio
ranges from 2.0 to 0.25. No authoritative relative rate card was available, so
the monetary verdict remains `price-unresolved`.

Weighted tokens are input + output + reasoning-output tokens. Cached input is
recorded separately in the JSON artifact. Failed judge retries are experiment
overhead and are not counted as product-path cost.

## Evaluator repair

The initial run exposed a separate measurement defect: JSON schema validation
accepted content-free one-character explanations from one judge. A semantic
minimum was added for checklist explanations, critical explanations, summaries,
and pairwise rationales. Three affected judge outputs were rerun under the same
blind prompts. One retry then failed score-sum consistency, so that single
judge received a third recorded attempt. The final evidence is complete at
56/56 generation calls and 16/16 valid judge calls.

This repair materially changed the apparent burden result from S being worse by
seven defects to equal aggregate burden. It is a warning that structured output
is not automatically valid evaluation evidence.

## Non-trivial implications

1. **Model substitution is not the main cost lever.** Repeating a long context
   can outweigh the cheaper model. Prompt compaction, shared-prefix caching, or
   fewer calls matter before adding more critics.
2. **More critics are not monotonic.** In screening, S4 doubled S2's challenger
   tokens, raised duplicate questions from 12.5% to 28.1%, and missed more exact
   fatal items.
3. **Question-only critique works as recall augmentation, not assurance.** Its
   value is the union of issues surfaced; an unsurfaced constraint remains the
   main model's responsibility.
4. **The next mechanism should add ownership, not another persona.** A generic
   main-model constraint ledger, checked against the original brief before
   Reality Slap review, directly targets the observed failure without another
   model call.

## Verdict and next test

Do not productize the tested S2 mechanism as a Terra-high replacement.

The smallest justified follow-up is `S2 + main constraint ledger`: preserve the
same two Luna calls and eight-question cap, but require Sol to verify every
explicit source constraint independently of the question packet before applying
Reality Slap. Compare that variant against the frozen H outputs on a fresh
holdout. Separately test a single Luna-low eight-question call to determine
whether the second full-context call buys enough diversity to justify its cost.

Claim boundary: internal eight-case holdout; no authoritative dollar rate card;
the result supports mechanism selection, not a general model-quality claim.
