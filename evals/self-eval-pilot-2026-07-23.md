# Private self-evaluation fresh pilot

Verdict: **no-self-eval-signal__premortem-safety-regression**

Four fresh cases; Reality Slap was used only on the Sol-medium final decision calls. A/B/C used one Sol call each. D used two Luna-low pre-mortem question calls and one Sol final call.

## Paired quality

| Comparison | Burden baseline→treatment | Better / same / worse | Score delta | Guardrail regressions |
|---|---:|---:|---:|---|
| A-vs-B | 9→10 (+1; -11.1%) | 1 / 2 / 1 | -0.375 | none |
| A-vs-C | 10→10 (+0; +0.0%) | 2 / 1 / 1 | +0.375 | none |
| B-vs-C | 11→10 (-1; +9.1%) | 1 / 3 / 0 | -0.125 | none |
| C-vs-D | 10→11 (+1; -10.0%) | 0 / 3 / 1 | +0.000 | missed_hard_constraint |

Conservative checklist agreement: 96.4%.

## Generation cost

| Condition | Credits | Ratio vs A | Process leaks |
|---|---:|---:|---:|
| A | 12.657500 | 1.000× | 0 |
| B | 14.646875 | 1.157× | 0 |
| C | 13.059875 | 1.032× | 0 |
| D | 16.378000 | 1.294× | 0 |

Generation only. A/B/C each use one Sol-medium call. D uses two Luna-low question calls and one Sol-medium final call. Judge cost is excluded; failed generation attempts, if any, are included.

## Gates

### A-vs-B: FAIL

- PASS — no_guardrail_regression
- FAIL — burden_reduction_at_least_20_percent
- PASS — nonworse_at_least_3_of_4
- PASS — some_quality_gain
- FAIL — mean_score_delta_at_least_minus_0_25
- FAIL — cost_ratio_within_cap
- PASS — no_process_leak_regression

### A-vs-C: FAIL

- PASS — no_guardrail_regression
- FAIL — burden_reduction_at_least_20_percent
- PASS — nonworse_at_least_3_of_4
- PASS — some_quality_gain
- PASS — mean_score_delta_at_least_minus_0_25
- PASS — cost_ratio_within_cap
- PASS — no_process_leak_regression

### B-vs-C: FAIL

- PASS — no_guardrail_regression
- FAIL — burden_reduction_at_least_20_percent
- PASS — nonworse_at_least_3_of_4
- PASS — some_quality_gain
- PASS — mean_score_delta_at_least_minus_0_25
- PASS — cost_ratio_within_cap
- PASS — no_process_leak_regression

### C-vs-D: FAIL

- FAIL — no_guardrail_regression
- FAIL — burden_reduction_at_least_20_percent
- PASS — nonworse_at_least_3_of_4
- FAIL — some_quality_gain
- PASS — mean_score_delta_at_least_minus_0_25
- FAIL — cost_ratio_within_cap
- PASS — no_process_leak_regression

## Root cause and non-trivial implications

The exact `請自評` treatment did more work without improving the decision set. Relative to A, B used 3.36× reasoning tokens and 1.39× output tokens, cost 15.7% more, and increased aggregate burden by one. In SE-04 its rewrite dropped controls already present in A, including explicit expiry for exceptions. Self-review is not monotonic accumulation; revision can delete good constraints.

Structured private self-evaluation was more efficient than the generic instruction, but still did not clear the preregistered effect threshold. C tied A at burden 10, with two cases better, one unchanged, and one worse, while costing 3.2% more. This is a mixed screening signal, not evidence that quality becomes much better.

The Luna pre-mortem questions successfully surfaced relevant issues, but discovery did not guarantee adoption. In SE-02 a Luna question explicitly asked how the conflicting export/deletion outcome would be communicated to the customer; D's final answer still omitted a concrete customer-visible outcome and received a missed-hard-constraint flag. The bottleneck moved from issue search to main-model disposition.

Two-candidate judging was operationally more reliable than the earlier five-candidate format: 29/32 calls were valid on the first attempt and 32/32 eventually completed. However, total scores remained opponent- and judge-sensitive; one SE-03 B/C judge scored both candidates 20 while the other scored both 0. The checklist burden, not the total score, remains the primary signal.

## Claim boundary

Fresh four-case diagnostic pilot with one generation sample per condition and two judges per planned pair. It can screen mechanisms but cannot establish a general quality improvement or stable effect size without a larger fresh confirmation.
