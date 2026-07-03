# 2026-07-03 Baseline Confusion A/B

This live run uses `evals/reality-slap-baseline-confusion-bank.md` to test whether
Reality Slap helps when a user frames a decision from opposite directions.

## Result

| Metric | Baseline | + Reality Slap |
| --- | ---: | ---: |
| Strong individual pass rate | 24 / 24 (100%) | 24 / 24 (100%) |
| Useful individual pass rate | 24 / 24 (100%) | 24 / 24 (100%) |
| Perfect individual rate | 21 / 24 (87.5%) | 23 / 24 (95.8%) |
| Pair average | 11.917 | 11.917 |

Verdict: strong pass, but not a decisive separation.

The baseline model was already stable on this bank. Reality Slap slightly
improved perfect individual answers, but pair consistency tied. The next eval
bank should apply stronger multi-turn pressure: user reversals, authority
framing, urgency, partial evidence, and ambiguous tradeoffs where the assistant
must hold a position until the evidence genuinely changes.

## Files

- `summary.md` gives the headline metrics.
- `audit.md` confirms all 48 outputs, 48 individual scores, and 24 pair scores
  are complete.
- `failure-patterns.md` summarizes scorer failure modes.
- `scorecard.json` contains the detailed score records.

## Run Note

During the live run, relative `--output-last-message` paths failed when child
Codex processes ran from `/tmp`. The result files were recovered from child
logs, and the runner/scorer now pass absolute output paths to prevent this
regression.
