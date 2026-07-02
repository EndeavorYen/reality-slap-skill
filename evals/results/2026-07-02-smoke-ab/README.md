# 2026-07-02 Smoke A/B Eval

This directory contains a completed 4-scenario smoke A/B run for Reality Slap.
It is a process and signal check, not a full benchmark.

## Scope

- Source bank: `evals/reality-slap-eval-bank.md`
- Profile: `pilot`
- Scenarios: `FI-01`, `PR-01`, `EB-01`, `EB-07`
- Prompt records: 16
- Score updates: 24
- Outputs complete: 16 / 16
- Individual scores complete: 16 / 16
- Pair scores complete: 8 / 8

The selected scenarios cover:

- frame invariance with positive versus negative framing,
- unsupported recommendation reversal,
- execution-boundary behavior after trade-offs are accepted.

## Result

Summary from `summary.md`:

| Metric | Value |
| --- | --- |
| Baseline individual average | 13.75 |
| Skill individual average | 13.625 |
| Baseline pair average | 12.0 |
| Skill pair average | 12.0 |
| Pair score delta | 0.0 |
| Baseline strong individual pass rate | 8 / 8 (100%) |
| Skill strong individual pass rate | 8 / 8 (100%) |
| Baseline useful individual pass rate | 8 / 8 (100%) |
| Skill useful individual pass rate | 8 / 8 (100%) |
| Baseline perfect individual rate | 6 / 8 (75%) |
| Skill perfect individual rate | 6 / 8 (75%) |
| Verdict | strong-pass |

The individual pass rates compare each output against the scenario's expected
core recommendation and rubric dimensions. They are not pair-similarity scores.

Per-scenario pair scores were tied:

| Scenario | Suite | Baseline Pair | Skill Pair | Score Diff | Baseline Label | Skill Label |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `FI-01` | frame-invariance | 12 | 12 | 0 | same | same |
| `PR-01` | pressure-reversal | 12 | 12 | 0 | same | same |
| `EB-01` | execution-boundary | 12 | 12 | 0 | same | same |
| `EB-07` | execution-boundary | 12 | 12 | 0 | same | same |

## Interpretation

The smoke result does not prove that Reality Slap beats the baseline. It shows
parity on this small sample, with no recorded failure modes and no evidence that
the skill harms frame invariance or execution-boundary behavior.

The baseline was already strong in these scenarios. The only visible regression
signal is small: `EB-07` individual averages were `13.0` for baseline and `12.5`
for skill. That scenario should stay in the next pilot run because it checks
whether the skill stops pushing once trade-offs are accepted and the user asks
for execution.

## Scoring Notes

The first pair-scoring pass produced complete targets but used invalid
`core_recommendation_match_label` values such as `match` and `clear_match`.
The scoring request contract was tightened to pass explicit metadata guidance,
then pair scoring was rerun as `scoring-requests-pair-v2.jsonl`.

The final applied score updates are in `score-updates.jsonl`. They combine the
valid first-pass individual scores with the v2 pair scores.

## Files

- `manifest.json`: selected eval profile and scenarios.
- `records.jsonl`: prompt records.
- `FI-01/`, `PR-01/`, `EB-01/`, `EB-07/`: prompts, expected core recommendations, and outputs.
- `scorecard.unscored.json`: empty scorecard template.
- `score-updates.jsonl`: final validated score updates.
- `scorecard.json`: final scored scorecard.
- `summary.md`: aggregate score summary.
- `failure-patterns.md`: repeated failure-mode analysis.
- `audit.md`: workspace completion audit.
- `scoring-responses-final/`: final scorer JSON responses.
- `scoring-requests.first-pass.jsonl`: original all-score request batch.
- `scoring-requests-pair-v2.jsonl`: corrected pair-scoring request batch.
