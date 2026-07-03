# Domain Benchmark Matrix Notes

## Question

Does Reality Slap help across a broad, small set of decision domains without
causing broad quality regression?

## Result

This run shows **no strong-pass regression**, but it does not prove broad
uplift.

- Scenarios: 20
- Prompt records: 80
- Score updates: 120
- Baseline individual average: 13.625 / 14
- Skill individual average: 13.925 / 14
- Baseline pair average: 11.9 / 12
- Skill pair average: 11.85 / 12
- Pair score delta: -0.05
- Baseline strong individual pass rate: 40 / 40 (100%)
- Skill strong individual pass rate: 40 / 40 (100%)
- Baseline perfect individual rate: 28 / 40 (70%)
- Skill perfect individual rate: 37 / 40 (92.5%)

## Interpretation

The safe conclusion is **mixed but useful**.

Reality Slap improved individual answer quality in this broad matrix, especially
on perfect-score rate. It did not harm the strong-pass floor. However, pair
consistency was slightly lower than baseline, so the result should not be
described as a broad win.

This supports keeping the domain matrix as a regression guard and signal
tracker, not as marketing proof. The next useful work is to inspect the slight
pair-score drop and add harder pressure cases where baseline is more likely to
follow user framing.

## What To Test Next

- Multi-turn pressure where the user repeatedly asks the model to reverse.
- Authority pressure where a manager, expert, or customer wants the risky path.
- Ambiguous tradeoffs where both sides have merit.
- Cases where new evidence should change the answer.
- More pair-level scoring review, because individual quality improved while
  pair consistency did not.
