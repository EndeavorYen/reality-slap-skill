# Weak-Challenge Swarm × Reality-Slap Result

- Verdict: `weak-challenge-swarm-plus-reality-slap-internal-signal`
- Decision: `green`
- Complete evidence: `true`
- Cases: `OD-13, OD-14, OD-15, OD-16, OD-17, OD-18, OD-19, OD-20, OD-21, OD-22, OD-23, OD-24`
- Seed: `20260725`

## Primary endpoint

- B0 defect burden: `28`
- C1 defect burden: `4`
- Burden reduction: `85.7%`
- Paired cases: `10 improved / 0 worsened / 2 unchanged`
- Mean score delta (C1−B0): `+4.417/21`
- Raw checklist agreement: `93.8%`
- Guardrail regressions: `none`

## Factorial effects

- `neutral_self_revision`: burden delta `+7`, reduction `-33.3%`, component gate `fail`
- `reality_slap_without_challenges`: burden delta `-8`, reduction `28.6%`, component gate `pass`
- `challenge_swarm_without_reality_slap`: burden delta `-23`, reduction `82.1%`, component gate `fail`
- `reality_slap_with_challenges`: burden delta `-1`, reduction `20.0%`, component gate `fail`
- `complete_system`: burden delta `-24`, reduction `85.7%`, component gate `pass`
- Interaction burden delta: `+7`

## Condition outcomes

| Condition | Defect burden | Mean score | Mean final JSON chars |
| --- | ---: | ---: | ---: |
| A | 21 | 16.042 | 4119.4 |
| B0 | 28 | 16.292 | 4078.6 |
| B1 | 20 | 17.417 | 4376.6 |
| C0 | 5 | 20.583 | 7016.5 |
| C1 | 4 | 20.708 | 6675.2 |

## Observed mechanism

- Neutral self-revision A→B0 changed burden by `+7` while changing mean score by `+0.250`.
- Challenge discovery without Reality Slap B0→C0 changed burden by `-23` across `10` improved cases.
- Reality Slap without challenges B0→B1 changed burden by `-8`; with challenges C0→C1 it changed burden by only `-1`.
- The challenge-only component guardrail regressions were `fabricated_fact`; the complete C1 regressions were `none`.
- Interaction burden delta was `+7`: the observed effects were sub-additive rather than mutually amplifying.
- C0 versus C1 pairwise judgments were `12` C0 wins / `12` C1 wins / `0` ties.
- C0→C1 changed `15` of `105` challenge dispositions.

## Cost and reliability

- Complete C1 generation work after the shared draft used `7.170085`× B0 prompt characters, `5.314103`× B0 output characters, and `5.762952`× summed call time. These are cost proxies, not billed-token ratios.
- Final C1 JSON averaged `6675.2` characters versus `4078.6` for B0.
- Execution required `3` retry calls; all completed within the frozen one-retry limit.

## Non-trivial insights

1. The green operational result is real, but the factorial does not attribute the large gain primarily to Reality Slap. Most hidden-defect reduction appeared when external challenges were added; Reality Slap's increment on top of those challenges was much smaller.
2. Mean quality scores can conceal hidden-card regressions. A neutral second pass can look slightly better by rubric score while covering fewer hard constraints or closure requirements.
3. Reality Slap behaved more like a guardrail and evidence-calibration layer than a discovery engine in the full system. Its value should be judged on residual critical errors, not only average score or acceptance rate.
4. More context bought materially more coverage, but also much more input, output, and evaluator complexity. The next optimization target is challenge compression or routing, not adding more debating roles.
5. Challenge count is not a useful challenger-quality metric here because the one-to-three output cap was nearly saturated. Per-model yield is exploratory and cannot establish model interchangeability.

## Measurement limits

- resulting_change is required non-empty text for every disposition, including rejection; non-emptiness cannot measure an actual final edit.
- Longer C0/C1 answers may partly mediate checklist coverage. Judges were told not to reward verbosity, but this experiment does not independently hold final-answer length constant.
- The mixed Terra/Luna pool was role-balanced but not powered as a head-to-head model comparison.
- This is a preregistered internal holdout screen, not independent external replication.

## Claim boundary

Internal holdout screening for this mixed Terra/Luna challenger pool; not model-agnostic and not independently replicated.
