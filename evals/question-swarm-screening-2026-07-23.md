# Question-Swarm Screening Result

## Outcome

`S2` advanced provisionally. Two isolated Luna-low question calls recovered
95.1% of the unique hidden-item coverage of one Terra-high call, while `S4`
failed the critical-item gate. Monetary cost was not declared because no
authoritative Luna/Terra rate card was available.

This is a screening result, not evidence that `S2` is production-ready.

## Frozen comparison

| Arm | Calls per case | Questions per case | Model / effort |
| --- | ---: | ---: | --- |
| H | 1 | 8 | Terra / high |
| S2 | 2 | 4 + 4 | Luna / low |
| S4 | 4 | 2 + 2 + 2 + 2 | Luna / low |

All calls were isolated, saw the same Sol-medium draft, and returned only
questions. Reality Slap was not present in challenger calls.

## Results

| Arm | Unique hidden items | Coverage vs H | Fatal items found | H fatal items missed | Duplicate rate | Weighted tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H | 41 | 100.0% | 5 | — | 0.0% | 63,444 |
| S2 | 39 | 95.1% | 5 | 1 | 12.5% | 112,302 |
| S4 | 41 | 100.0% | 4 | 2 | 28.1% | 230,393 |

Every one of the 96 generated questions was reviewable. There were no failed
or retried generation calls.

`S4` demonstrates that more isolated critics do not produce monotonic
coverage. It matched H's aggregate item count, yet duplicated more questions
and missed two exact fatal items that H found. Fragmenting the same eight-slot
budget across four calls increased repeated context and reduced integrated
cross-lens reasoning.

## Cost boundary

Weighted tokens are input + output + reasoning-output tokens; cached input is
reported separately in the JSON artifact and is not double-counted.

- S2 used 1.77 times H's weighted tokens. It meets the 70% challenger-cost gate
  only if a Luna token costs no more than 39.55% of a Terra token.
- S4 used 3.63 times H's weighted tokens. Its corresponding break-even ratio is
  19.28%.

These are break-even inequalities, not dollar-price claims.

## Provenance and boundary

- Experiment: `question-swarm-screening-20260723`
- Cases: `OD-13`, `OD-16`, `OD-19`, `OD-22`
- Generation calls: 32/32 complete
- Blind question judges: 4/4 complete
- Selected arm: `S2`
- Verdict: `price-unresolved-provisional-selection`

The paired eight-case confirmation result is recorded separately in
`question-swarm-cost-2026-07-23.md`.
