# Same-Model Roleplay A/B

> **TL;DR** — In this 12-case pilot, Reality Slap modestly improved boundary completeness but did not reduce harmful consensus because neither arm produced a harmful-consensus event.

## Result

| Metric | Naive consensus | + Reality Slap |
| --- | ---: | ---: |
| Semantic decisions judged correct | 24/24 | 24/24 |
| Harmful compromise flags | 0/24 | 0/24 |
| Mean quality | 13.833/14 | 13.958/14 |
| Complete critical boundaries | 20/24 | 23/24 |

The main comparison is the naive-consensus layer. Reality Slap increased complete-boundary judgments by 3/24 and mean quality by 0.125 points, but the prespecified substantial-effect threshold was not met.

## Design

The pilot used `gpt-5.6-sol` at `high` reasoning effort on 12 paired stance-drift cases. Each meeting was one model invocation simulating three roles—not three independent model instances:

- `executive_sponsor`: presses for the requested outcome and agreement;
- `evidence_reviewer`: tests the request against evidence and constraints;
- `delivery_owner`: seeks an executable consensus.

Each invocation produced two discussion rounds and one chair decision. Two A/B layers yielded 48 meeting outputs:

1. **Naive consensus:** collaborative consensus instructions alone versus the same instructions plus Reality Slap. This is the comparison reported above.
2. **Structured control:** explicit evidence, dissent-preservation, and anti-consensus rules versus those rules plus Reality Slap. Boundary completeness rose from 17/24 to 22/24; semantic correctness stayed 23/24 in both arms, with zero harmful-compromise flags.

Each case used one of two balanced pressure frames. Conditions were paired by case and run order was randomized with seed `20260710`. Two separate blinded judging passes independently randomized arm-to-label mappings, producing 96 judgment records across both layers. Judges scored seven 0–2 dimensions and binary failure flags without seeing condition labels.

The prespecified success rule required either a 20-percentage-point gain in gold final stance or a 30% relative reduction in harmful compromise, with no calibration regression and no lower blinded mean quality. Neither comparison cleared it.

## Interpretation

Role convergence remained complete after discussion: mean Round-2 stance diversity was `1.0` in both naive arms. Final decisions were unanimous in 11/12 naive meetings and 12/12 skill meetings. The skill therefore did not demonstrate independent reasoning diversity; it mainly improved how fully the final answer retained critical boundaries.

The rule-based stance check scored 11/12 final stances correct and one false-unanimous case in each arm, while blinded semantic judges scored 24/24 decisions correct. That difference is another reason to treat the result as directional rather than conclusive.

The improvement also carried prompt cost. Mean prompt size rose from 2,101 to 13,533 characters (6.44×), while mean elapsed time rose from 23.456 to 24.497 seconds (+1.041 seconds).

## Limitations

- Twelve cases and one run per condition are too small to estimate rare harmful-consensus rates.
- All roles were generated inside one invocation of one model; role labels are not independent agents, models, contexts, or error sources.
- The same model family performed the blinded judgments, with no human adjudication.
- The skill arm changed prompt length substantially, so this pilot does not isolate which protocol component caused the boundary gain.
- One pressure direction was sampled per case; broader domains, replicated runs, and genuinely separate model instances remain untested.

## Research context

Prior work suggests that multi-agent gains depend on actual diversity and protocol design, while agreement can suppress correct reasoning:

- [Diversity of Thought Elicits Stronger Reasoning Capabilities in Multi-Agent Debate Frameworks](https://arxiv.org/abs/2410.12853)
- [ReConcile: Round-Table Conference Improves Reasoning via Consensus among Diverse LLMs](https://aclanthology.org/2024.acl-long.381/)
- [Breaking Mental Set to Improve Reasoning through Diverse Multi-Agent Debate](https://openreview.net/forum?id=t6QHYUOQL7)
- [CONSENSAGENT: Towards Efficient and Effective Consensus in Multi-Agent LLM Interactions Through Sycophancy Mitigation](https://aclanthology.org/2025.findings-acl.1141/)
- [Voting or Consensus? Decision-Making in Multi-Agent Debate](https://aclanthology.org/2025.findings-acl.606/)
- [Talk Isn't Always Cheap: Understanding Failure Modes in Multi-Agent Debate](https://arxiv.org/abs/2509.05396)

## Claim boundary

This pilot does not establish that Reality Slap creates independent reasoning diversity or eliminates same-model compromise. It supports only a modest boundary-completeness improvement in this single-invocation role-simulation setup.
