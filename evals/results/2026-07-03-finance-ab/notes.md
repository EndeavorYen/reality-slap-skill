# Finance A/B Notes

## Question

Does Reality Slap produce a positive measurable effect for finance, stock, and
trading-style prompts?

## Result

This run does **not** show a measurable lift over baseline.

Both baseline and +skill reached perfect scores:

- Baseline individual average: 14.0 / 14
- Skill individual average: 14.0 / 14
- Baseline pair average: 12.0 / 12
- Skill pair average: 12.0 / 12
- Pair score delta: 0.0
- Failure modes: none

## Interpretation

The safe conclusion is **no regression, but no proven positive lift**.

The finance scenarios did confirm that +skill preserves disciplined behavior:
it resisted FOMO, panic selling, short-dated option speculation, concentration,
and margin pressure while still accepting bounded changes when the evidence or
objective materially changed.

However, the baseline responses were already equally strong. That means this
bank is probably too easy or too explicitly risk-bounded to prove incremental
value from Reality Slap.

## What To Test Next

Add a harder finance eval bank that focuses on:

- Multi-turn pressure after an earlier recommendation.
- User requests to "adjust your recommendation" without new evidence.
- Authority pressure, such as a boss, friend, analyst, or popular trader.
- Urgency pressure, such as "market opens soon" or "I need a direct answer now".
- Ambiguous cases where both action and restraint are plausible.
- Cases where new evidence should change the recommendation, so the skill is not
  rewarded for stubborn refusal.

Do not claim finance-specific effectiveness until the harder bank shows a
positive pair-score delta or catches failure modes that baseline misses.
