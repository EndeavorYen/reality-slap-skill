# Question-Swarm Screening Result

## Outcome

`S2` passed screening. Two isolated Luna-low question calls recovered 95.1% of
the unique hidden-item coverage of one Terra-high call and cost 68.1% as many
official Codex credits. `S4` failed both the critical-item and cost gates.

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

| Arm | Unique hidden items | Coverage vs H | Fatal items found | H fatal items missed | Duplicate rate | Credits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H | 41 | 100.0% | 5 | — | 0.0% | 3.713637 |
| S2 | 39 | 95.1% | 5 | 1 | 12.5% | 2.529690 |
| S4 | 41 | 100.0% | 4 | 2 | 28.1% | 5.350190 |

Every one of the 96 generated questions was reviewable. There were no failed
or retried generation calls.

`S4` demonstrates that more isolated critics do not produce monotonic
coverage. It matched H's aggregate item count, yet duplicated more questions
and missed two exact fatal items that H found. Fragmenting the same eight-slot
budget across four calls increased repeated context and reduced integrated
cross-lens reasoning.

## Cost boundary

The official OpenAI Codex rate card charges credits per million input, cached
input, and output tokens. Sol costs `125 / 12.5 / 750`, Terra
`62.5 / 6.25 / 375`, and Luna `25 / 2.5 / 150` credits for those token classes.
Reasoning output is a subset of output tokens and is not charged a second time.

- S2 cost 68.12% of H and passed the 70% challenger-cost gate.
- S4 cost 144.07% of H and failed the cost gate despite Luna's lower unit price.
- S2's break-even Luna/Terra multiplier was 41.10%; the official multiplier is
  40% for all three token classes.

Credits measure incremental Codex consumption, not subscription dollars.

## Provenance and boundary

- Experiment: `question-swarm-screening-20260723`
- Cases: `OD-13`, `OD-16`, `OD-19`, `OD-22`
- Generation calls: 32/32 complete
- Blind question judges: 4/4 complete
- Selected arm: `S2`
- Verdict: `screening-pass`

The paired eight-case confirmation result is recorded separately in
`question-swarm-cost-2026-07-23.md`.
