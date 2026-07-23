# Multi-model deliberation: findings and product decision

Date: 2026-07-23

## Executive conclusion

The original hypothesis was:

> Giving multiple models different roles or directions, then letting them
> debate, should materially improve the final answer by broadening the search
> space and reducing a strong model's blind spots.

The experiments did **not** support that claim as a reliable end-to-end
effect. Separate calls, mutually exclusive role commitments, generic
self-evaluation, and cheap question swarms all failed to demonstrate a stable
quality advantage over a strong direct answer. The final preregistered
tournament produced no valid champion.

A narrower mechanism did survive:

> External questions can reveal issues that the main model did not mention,
> but discovery does not guarantee that the final model will adopt, prioritize,
> or correctly resolve them.

That distinction changes the product decision. Multi-model deliberation should
not be the default command architecture. The current operating default is one
direct Sol-xhigh Reality Slap answer (`DX`). One Terra-high question-only
challenge (`T1`) remains a possible premium escalation for unusually
high-stakes or cross-domain decisions, but its net quality gain is unproven.
The two-Luna pipeline (`L2`) is not a production candidate.

Reality Slap also has a narrower role than originally proposed. It is useful
for preserving evidence boundaries, stance consistency, and residual
guardrails. It is not a convergence algorithm, a completeness oracle, or a
substitute for a missing challenge.

## How the hypothesis evolved

The research moved through four increasingly narrow hypotheses:

1. **Simulated debate:** one model playing several roles might broaden
   reasoning.
2. **Independent debate:** isolated calls and precommitted opposing roles might
   create genuine diversity that shared context suppressed.
3. **Challenge, not debate:** weaker models might cheaply generate objections
   and questions without needing to agree or synthesize.
4. **Cost-bounded challenge:** a small set of cheap question-only critics,
   followed by one strong Reality Slap decision, might beat a strong direct
   answer on quality per credit.

The first, second, and fourth hypotheses were not supported. The third
identified a real intermediate effect—issue discovery—but not a reliable
improvement in the final decision.

## Evidence chain

| Stage | Question tested | Result | What it changed |
| --- | --- | --- | --- |
| Same-call roleplay | Does Reality Slap make one model's simulated roles produce safer consensus? | Mean quality rose only from 13.833 to 13.958/14; boundary completeness rose 20/24 to 23/24; harmful compromise was 0/24 in both arms. | Reality Slap modestly improved boundaries, but the run did not show independent diversity or safer consensus. |
| Isolated role calls | Was shared context suppressing disagreement? | Isolation reduced mean unique stances by 0.083 and dissent by 0.083; quality rose only 0.125/14. Verdict: `isolation-not-supported`. | Separate calls alone do not create useful cognitive independence. |
| Mutually exclusive commitments | Do supporter, opponent, and third-way roles improve the chair's answer? | Manipulation failed; forced roles averaged 2.604 unique stances with only a 0.625 all-three rate. Isolated forced-role quality changed by -0.104/14. Verdict: `inconclusive`. | Prompt labels can manufacture visible opposition without guaranteeing complete substantive coverage. |
| Weak challenge swarm | Can external question-only critics improve a Sol-medium draft? | Against neutral self-revision, defect burden fell 28 to 4 and mean score rose 4.417/21. Most gain came from the external challenges; Reality Slap reduced burden only 5 to 4 on top. | Strong positive mechanism signal, but against a weak baseline and with 5.76× summed call time, 7.17× prompt characters, and 1.64× answer length. It justified confirmation, not productization. |
| Cheap challenger screen | Can two Luna-low calls approximate one Terra-high call? | On four screening cases, two Luna calls recovered 95.1% of Terra's unique hidden-item coverage for 68.1% of challenger credits. Four Luna calls cost 144.1% of Terra and duplicated more questions. | More critics are not monotonic; two Luna calls earned a larger confirmation test. |
| Cheap challenger confirmation | Is two-Luna challenge production-safe? | Aggregate burden tied 22–22, but Luna missed a delayed-writer recovery constraint that Terra found. Verdict: `safety-regression`. | Splitting lenses can miss constraints that live between specialties; no critic owns cross-lens completeness. |
| Ledger and direct-effort replay | Can a source ledger fix adoption, or can Sol high/xhigh replace challengers? | The ledger raised mean score but added one defect, leaked process language, and was the most expensive path. Direct high/xhigh cost roughly half as much as the pipelines but had more defects in this reused diagnostic. | Audit scaffolds can improve presentation while degrading safety. The direct-vs-pipeline comparison required a fresh holdout. |
| Self-evaluation pilot | Does `請自評` or structured private review improve Sol-medium? | Generic self-evaluation changed burden 9 to 10 at +15.7% cost. Structured review changed 10 to 10 at +3.2%. Luna pre-mortem changed 10 to 11 at +25.4%. | More private reasoning and more tokens are not monotonic quality controls. A found issue can still be omitted by the final answer. |
| Fresh final tournament | Which practical architecture wins: DX, L2, or T1? | No preregistered champion. L2 failed opponent-context stability. Neither pipeline reduced defect burden versus DX. DX cost 45.240900 credits, L2 73.426290, and T1 79.444513. | Use DX as a post-hoc operating default, retain T1 only as an unproven premium escalation, and remove L2 from the shortlist. |

The planned heterogeneous open-decision debate was preregistered, but it is
not recorded as completed evidence. As the hypothesis narrowed, the live work
shifted to the question-only challenge architecture. The preregistration must
not be cited as a result.

## What was falsified

### 1. Debate did not produce a large, stable quality lift

The experiments do not support a general claim that more roles, more
opposition, or more model calls materially improve open-ended decisions.
Visible disagreement is not the same as coverage, and coverage is not the same
as a better final decision.

### 2. Context isolation was not the missing ingredient

The isolated-role experiment directly tested the proposed root cause. Separate
calls did not increase substantive stance diversity. The same underlying model
still converged on similar priors, even when transcripts were isolated.

### 3. Precommitted opposition was not enough

Supporter, opponent, and third-way prompts created more surface-level
opposition, but they did not reliably satisfy the manipulation check or improve
the chair's result. A role can defend its assigned stance without finding a new
fact, constraint, or causal path.

### 4. “請自評” was not a cheap quality multiplier

The generic self-evaluation prompt caused much more reasoning and output but no
quality gain. It sometimes rewrote away controls that were already correct.
Structured self-review was cheaper and less erratic, but still did not reduce
aggregate defect burden.

### 5. Cheap critics were not a safe Terra replacement

Two Luna calls looked attractive at the question-discovery stage, but the
production gate correctly failed on a missed hard constraint. In the fresh
end-to-end tournament, Luna saved 35.8% at the challenger stage but only 7.6%
overall because the Sol draft and final answer dominated total cost.

### 6. Pairwise preference was not a quality or safety metric

In the final tournament, judges strongly preferred L2 and T1 prose over DX
while checklist defect burden and guardrails did not improve. Preference can
reward completeness signals, length, and polish that do not close the actual
decision constraints.

## What survived

### Reality Slap is a guardrail, not a search engine

The strongest replicated Reality Slap evidence remains stance stability under
framing pressure. In deliberation experiments it sometimes improved boundary
completeness or removed a fabricated-fact regression. Its incremental effect
on top of external challenges was small and sub-additive.

Use it to:

- preserve the evidence boundary;
- resist pressure-driven reversals;
- state the recommendation, risk, and change-of-mind condition;
- review whether a surfaced objection should change the decision.

Do not claim that it:

- creates independent reasoning diversity;
- discovers every missing constraint;
- forces multiple agents to converge correctly;
- makes additional model calls monotonic improvements.

### External questions are useful as optional recall augmentation

Question-only challengers can find real omissions. They are most defensible
when the downside of a missed cross-domain dependency is high enough to justify
extra cost. Their output should be treated as untrusted leads, not requirements
that the final model must blindly include.

The final model must explicitly dispose each retained issue as:

- material and decision-changing;
- material but already mitigated;
- plausible but requiring evidence;
- irrelevant or duplicate.

The self-evaluation pilot showed why this matters: Luna found a
customer-communication issue, but the Sol final answer still omitted it.
Discovery without disposition is an incomplete pipeline.

### Strong direct reasoning is the best current default

The final tournament did not prove that DX had universally higher quality. It
did show that neither more expensive pipeline established lower defect burden,
while DX was materially cheaper and had stable aggregate burden across its two
matches. That is enough for an operating default, not a model-ranking claim.

## Root causes and non-trivial insights

### 1. Strong-model ceiling changes the value of debate

A strong main model already covers many obvious pro, con, and alternative
considerations. Weak critics often repeat considerations already latent in the
draft. Their marginal value is concentrated in rare missing constraints, so
average gains shrink while context and synthesis cost remain.

This means the useful question is not “Did the critics say more?” It is:

> Did they find a material issue the strong model would otherwise miss, and did
> the final answer resolve it correctly?

### 2. Diversity of prompts is not independence of evidence

Isolated calls reduce transcript leakage, but they do not change shared model
priors, training data, or likely abstractions. Precommitted roles diversify
arguments more reliably than conclusions, and can turn the experiment into
position defense rather than information search.

### 3. The bottleneck moved from discovery to disposition

Once critics can cheaply generate many questions, the expensive and difficult
work moves back to the main model: deduplicating, checking plausibility,
ranking materiality, tracing interactions, and deciding what changes the
answer. More questions can therefore increase the main model's burden without
increasing correctness.

### 4. Revision is non-monotonic

Every rewrite is an opportunity to add a missing control and an opportunity to
delete a correct one. Generic self-evaluation, source ledgers, and challenge
packets all produced examples where more process or more reasoning did not
produce a safer final answer.

The correct baseline is therefore the original strong answer, not an assumed
inferior draft that must be rewritten.

### 5. Critic fragmentation creates coverage gaps

Specialized critics improve local variety but can miss constraints spanning
several lenses. The database-recovery miss involved operations, reversibility,
queues, integrations, and evidence at once. One integrated Terra challenger
found it; two specialized Luna calls did not.

Adding more critics is not the direct fix. Four Luna calls increased duplicate
rate and cost without monotonic fatal-item coverage.

### 6. Reality Slap and external challenge are sub-additive

In the weak-swarm factorial, the challenge swarm removed 23 defects relative
to neutral revision, while Reality Slap removed only one additional defect on
top of the swarm. Both mechanisms partly target unsupported claims and missed
boundaries, so their benefits overlap.

The product should budget for the incremental value of each layer, not add
their standalone effect sizes.

### 7. Cheap unit prices do not imply a cheap system

Luna costs 40% of Terra per token under the recorded Codex rate card, but two
Luna calls repeat the draft and instructions. More importantly, the Sol draft
and final synthesis dominate end-to-end cost. Optimizing only the challenger
stage produced a 35.8% local saving but just a 7.6% total saving in the final
tournament.

The relevant metric is end-to-end credits per accepted decision, including
retries and final synthesis—not critic price.

### 8. Evaluation relativity can reverse the apparent result

The same frozen H/S outputs received burden 22/22 in one evaluation and 17/14
in a later five-candidate replay. In the final tournament, L2's same frozen
answers received burden 32 against DX and 39 against T1. Even DX and T1, whose
aggregate totals were stable, had 21/216 and 7/216 checklist decisions change
across opponents.

High agreement within one judge packet does not prove context-independent
measurement. Aggregate stability can also hide offsetting item-level flips.

### 9. Safety checklists and preference answer different questions

Pairwise judges can prefer a longer, more comprehensive-sounding answer while
anchored checks reveal equal or worse defects. Preference is useful for
presentation quality after safety and cost gates pass. It should not choose
the safe architecture.

### 10. Structured output is not automatically valid evidence

One judge returned schema-valid but content-free explanations. Enforcing
semantic minimums and rerunning affected calls materially changed the apparent
burden result. Mechanical JSON validity is only the first evaluation gate.

## Cost summary

The recorded official Codex credit rates per one million tokens were:

| Model | Input | Cached input | Output |
| --- | ---: | ---: | ---: |
| Sol | 125 | 12.5 | 750 |
| Terra | 62.5 | 6.25 | 375 |
| Luna | 25 | 2.5 | 150 |

Reasoning tokens are a subset of output tokens and were not charged twice.
Credits measure Codex consumption, not subscription dollars.

The fresh final-tournament candidate costs were:

| Candidate | Architecture | Credits | Relative to DX |
| --- | --- | ---: | ---: |
| DX | one Sol-xhigh Reality Slap answer | 45.240900 | 1.000× |
| L2 | Sol-medium draft + 2 Luna-low questions + Sol-medium final | 73.426290 | 1.623× |
| T1 | Sol-medium draft + 1 Terra-high question call + Sol-medium final | 79.444513 | 1.756× |

The offline judge layer cost another 210.878763 credits. That cost is
experiment overhead, not a product-path cost, but it matters when planning
future benchmark sizes.

## Product decision

If this research becomes a command or routing policy:

1. **Default:** direct strong-model Reality Slap answer. The current evidence
   selects DX as the operating default.
2. **Optional escalation:** one integrated Terra-high question-only challenge
   for decisions with high downside, cross-system interactions, or weak source
   coverage. Label this mode experimental until it beats DX on fresh,
   item-stable holdouts.
3. **Do not ship:** generic multi-role debate, forced supporter/opponent/third
   way debate, generic `請自評`, the source-ledger variant, or two-Luna swarm as
   a default path.
4. **Do not force convergence:** the final model should reject irrelevant or
   unsupported challenges. Convergence is an output property, not evidence of
   correctness.
5. **Cap challenge volume:** optimize for material, non-duplicate issues. A
   longer questionnaire increases synthesis cost and revision risk.

This is a routing recommendation, not an implemented model selector in the
current skill.

## Evaluation protocol for any future retest

A future claim that deliberation beats a direct answer should require:

1. fresh, hidden cases not used in prompt or mechanism development;
2. one frozen candidate answer per architecture before judging;
3. independent anchored checklist evaluation for each candidate, without a
   visible opponent;
4. item-level stability across at least two judge contexts or replications;
5. hard safety and fabricated-fact gates before pairwise preference;
6. end-to-end cost accounting, including retries and final synthesis;
7. answer-length reporting or length control;
8. explicit discovery-to-disposition scoring for every unique challenge;
9. multiple generation samples before claiming a stable effect size;
10. human adjudication for disputed safety-critical items.

Pairwise PK can remain a secondary presentation or usefulness test after the
anchored gates pass. It should not be the primary defect measurement.

## Claim boundary

These findings come from internal holdouts in one model family, mostly with
model-based judges and one generation sample per final-tournament candidate.
They do not prove that all multi-agent systems are ineffective, that Terra can
never outperform Sol, or that external challenge has no value.

They do reject the current broad product claim:

> Debate or cheap critic swarms reliably produce a much better answer than one
> strong Reality Slap call.

The evidence supports a more modest claim:

> External challenge can surface useful omissions in selected cases, but its
> net benefit is sparse, adoption is fallible, evaluation is context-sensitive,
> and the tested pipelines did not beat the strong direct default.

## Evidence index

- [Same-model roleplay A/B](../evals/same-model-roleplay-ab-2026-07-10.md)
- [Isolated-context roleplay 2×2](../evals/isolated-context-roleplay-2x2-2026-07-23.md)
- [Precommitted-stance roleplay 2×2×2](../evals/precommitted-stance-roleplay-2x2x2-2026-07-23.md)
- [Open-decision debate preregistration](superpowers/specs/2026-07-23-open-decision-debate-experiment-design.md)
- [Weak challenge swarm factorial](../evals/weak-challenge-swarm-2026-07-23.md)
- [Question-swarm screening](../evals/question-swarm-screening-2026-07-23.md)
- [Cost-bounded question-swarm confirmation](../evals/question-swarm-cost-2026-07-23.md)
- [Question-swarm ledger/direct replay](../evals/question-swarm-ledger-replay-2026-07-23.md)
- [Private self-evaluation pilot](../evals/self-eval-pilot-2026-07-23.md)
- [Final cost/quality tournament](../evals/final-tournament-2026-07-23.md)
- [Recorded Codex rate card](../evals/openai-codex-rate-card-2026-07-23.json)
- [Machine-readable evaluation index](../evals/evals.json)
