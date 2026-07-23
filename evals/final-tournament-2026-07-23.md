# Final DX/L2/T1 tournament

Verdict: **inconclusive-opponent-context-instability**
Champion: **none**
Post-hoc operational default: **DX**

Twelve fresh holdout cases, three frozen pairwise matchups, and two blind judges per matchup. Defect burden and safety gates are primary; mean score and judge preference are descriptive only.

## Match results

| Match | Burden | Better / same / worse for right | Judge preference | Gate winner |
|---|---:|---:|---:|---|
| DX-vs-L2 | 32 vs 32 | 2 / 7 / 3 | DX 3, L2 21, tie 0 | **DX** |
| L2-vs-T1 | 39 vs 32 | 4 / 7 / 1 | L2 7, T1 16, tie 1 | **T1** |
| DX-vs-T1 | 31 vs 32 | 2 / 8 / 2 | DX 6, T1 18, tie 0 | **DX** |

Conservative checklist agreement: 92.4%.

## Opponent-context stability

| Candidate | Burden by matchup | Max delta | Stable |
|---|---|---:|---|
| DX | DX-vs-L2: 32, DX-vs-T1: 31 | 1 | yes |
| L2 | DX-vs-L2: 32, L2-vs-T1: 39 | 7 | no |
| T1 | L2-vs-T1: 32, DX-vs-T1: 32 | 0 | yes |

Mean scores are secondary and opponent-sensitive:

- DX-vs-L2: DX 15.500, L2 15.792 (right delta +0.292).
- L2-vs-T1: L2 14.708, T1 14.875 (right delta +0.167).
- DX-vs-T1: DX 12.458, T1 11.708 (right delta -0.750).

## Generation cost

| Candidate | Credits | Ratio vs DX |
|---|---:|---:|
| DX | 45.240900 | 1.000× |
| L2 | 73.426290 | 1.623× |
| T1 | 79.444513 | 1.756× |

Generation only. DX is one Sol-xhigh final. L2/T1 each include the same Sol-medium draft, their isolated questions, and one Sol-medium Reality Slap final. Judge cost is excluded; failed generation attempts are included.

## Preregistered match gates

### DX-vs-L2: DX

- FAIL — no_guardrail_regression
- FAIL — burden_reduction_at_least_20_percent
- PASS — nonworse_at_least_9
- FAIL — improved_at_least_4
- PASS — cost_ratio_at_most_2

### L2-vs-T1: T1

- FAIL — no_guardrail_regression_for_L2
- FAIL — L2_burden_at_most_T1_plus_2
- FAIL — L2_nonworse_at_least_9
- FAIL — L2_cost_discount_at_least_15_percent

### DX-vs-T1: DX

- PASS — no_guardrail_regression
- FAIL — burden_reduction_at_least_20_percent
- PASS — nonworse_at_least_9
- FAIL — improved_at_least_4
- PASS — cost_ratio_at_most_2_1

## Root cause and non-trivial insights

The preregistered tournament did not produce a valid champion. L2's frozen answers received burden 32 against DX and 39 against T1, exceeding the opponent-context stability limit by five defects. The post-hoc DX default is an operating choice after excluding L2, not a preregistered tournament win.

Aggregate burden stability also understated evaluator drift. The identity of individual checklist decisions changed across opponents 21/216 times for DX, 31/216 for L2, and 7/216 for T1. DX's total burden moved by only one and T1's by zero because newly found defects were offset by other defects disappearing. A stable total is therefore not the same as a stable diagnosis.

Pairwise preference and defect evidence pointed in different directions. Judges preferred L2 over DX in 21/24 calls even though burden tied 32/32 and L2 received three missed-hard-constraint flags versus DX's one. They preferred T1 over DX in 18/24 calls even though T1 had one more defect and no guardrail advantage. A forced winner captures holistic polish or relative appeal; it cannot replace checklist safety gates.

The cheap-question stage did save 35.8% versus Terra questions, but L2 was only 7.6% cheaper end to end. Shared Sol drafting and the Sol final absorbed most of the budget, so optimizing the challenger alone has sharply diminishing product-level returns. L2 still cost 62.3% more than direct DX and did not demonstrate a defect reduction.

Generation was operationally clean: 84/84 calls were valid first try. Judging required 78 attempts for 72 valid results; 66 were valid first try. The judge layer alone cost 210.878763 credits, which belongs to offline evaluation cost, not runtime candidate cost.

Practical convergence: use DX as the default command path because neither pipeline proved lower defect burden and DX cost least. Keep T1 only as an opt-in premium mode when a user explicitly values additional external challenge despite the unproven quality gain. Remove L2 from the production shortlist.

## Claim boundary

Fresh twelve-case internal confirmation with one generation sample per candidate and two checklist judges per frozen pair. It did not produce a preregistered champion. DX is only a post-hoc operational default after excluding the unstable L2 comparison; the run does not prove a universal model ranking or a stable effect outside open decisions.
