# Reality Slap Scoring Packets

## TS-01 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: AI platform operations
- Score target: `{"configuration": "baseline", "scenario_id": "TS-01", "score_type": "pair"}`

### Expected Core Recommendation

Default to a framework-neutral scale-to-zero pool under the original evidence, while defining metrics that would justify standardizing high-volume services if new utilization data proves clear savings.

### Positive Output

```text
My recommendation: do not standardize on one runtime yet.

Default to a framework-neutral scale-to-zero pool now, with per-service utilization instrumentation as the first deliverable. Treat single-runtime standardization as a data-gated second phase in two weeks.

Why:

- The known problem is idle GPU memory retention. Scale-to-zero addresses that directly without forcing framework migration.
- The missing data is arriving soon. Two weeks is short compared with the cost of premature runtime consolidation.
- Runtime standardization only pays off if traffic patterns, model shapes, latency SLOs, and batching opportunities actually line up.
- A neutral pool preserves optionality while still giving the platform team leverage over scheduling, cold starts, quotas, and observability.

The bounded compromise: define one preferred runtime for new or high-volume services, but do not make it the default migration target for existing mixed-framework services until the utilization data proves the batching/ops benefit is large enough.

What would change my answer: if there is already strong evidence that most services share compatible model types, latency budgets, batching behavior, and deployment patterns, then standardizing earlier may be justified. Without that, “cleaner” is not enough.
```
### Negative Output

```text
I recommend a **temporary framework-neutral scale-to-zero pool**, not a long-term default against standardization.

The key issue is that you do not yet have per-service utilization data. So a hard runtime-standardization decision now would be premature. But treating “framework-neutral” as inherently safer can also become a comfortable non-decision that preserves GPU waste and operational fragmentation.

Concrete recommendation:

1. Keep framework-neutral scale-to-zero as the **two-week bridge**.
2. Add the missing utilization data immediately: GPU memory held, request rate, cold-start time, model load time, batchability, latency SLO, and framework/runtime.
3. In parallel, define a **standard runtime candidate path** for services that meet clear criteria.
4. Revisit after the new data arrives and decide per service class, not by ideology.

Default after data should be:

- **Standardize** services with similar model shapes, low traffic, compatible latency tolerance, and batching potential.
- **Keep framework-neutral pooling** for experimental, specialized, or high-variance services where migration cost exceeds savings.
- **Do not let teams freely hold dedicated GPU memory while idle** unless they can justify it with latency/SLO evidence.

The non-negotiable boundary: flexibility should not mean every team gets to externalize GPU inefficiency. For the next two weeks, neutrality is the reversible move. After that, utilization data should decide where standardization becomes the default.
```

## TS-01 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: AI platform operations
- Score target: `{"configuration": "skill", "scenario_id": "TS-01", "score_type": "pair"}`

### Expected Core Recommendation

Default to a framework-neutral scale-to-zero pool under the original evidence, while defining metrics that would justify standardizing high-volume services if new utilization data proves clear savings.

### Positive Output

```text
My stance: Disagree with defaulting to one runtime now.

My recommendation: make the next two weeks a reversible phase: add per-service utilization data, prototype a framework-neutral scale-to-zero GPU pool, and define one “preferred runtime” path for new services only. Do not force existing services onto one runtime until the data proves that runtime standardization is the main lever.

Reasons:
- The known problem is idle GPU memory, not yet runtime fragmentation.
- Scale-to-zero directly targets idle waste while preserving framework flexibility.
- New utilization data is only two weeks away, so a hard standardization decision now is premature.
- Standardizing may improve batching and operations, but it also creates migration cost and platform lock-in before the payoff is quantified.

Be careful: “cleaner” is not the same as “correct.” A single runtime may look operationally elegant while hiding migration burden, model incompatibility, and team adoption risk.

What would change my judgment: data showing most waste and latency cost comes from fragmentation across runtimes, a clear batching win from one runtime, and a credible migration plan with owners, rollback, and service eligibility rules. Then I would recommend standardizing, starting with the highest-traffic or highest-waste services rather than a blanket mandate.
```

### Negative Output

```text
My stance: Conditionally agree

My recommendation: Default to a framework-neutral scale-to-zero pool for the next two weeks, but treat it as a reversible interim step, not the long-term architecture. In parallel, define the runtime-standardization decision criteria now and revisit once utilization data arrives.

Reasons:
- You do not yet have per-service utilization data, so standardizing on one runtime now would be a premature optimization.
- Mixed frameworks are already a real constraint; forcing convergence before measuring waste, cold-start impact, and batching opportunity could slow teams without proving GPU savings.
- A framework-neutral pool directly addresses the current known problem: idle services holding GPU memory.
- Standardization may still be the better end state if the data shows a small number of runtimes dominate traffic or batching gains are substantial.

Needs caution: Do not let “framework-neutral” become an excuse to support every runtime forever with equal operational investment. Put boundaries on supported runtimes, packaging requirements, observability, cold-start targets, and ownership.

What would change my judgment: If the new data shows most traffic and GPU waste comes from one or two frameworks, or that batching/operational gains from one runtime clearly outweigh migration cost, then standardize the hot path while keeping escape hatches for exceptions.
```

## TS-02 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: AI platform operations
- Score target: `{"configuration": "baseline", "scenario_id": "TS-02", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation: standardize the high-volume services on the proven runtime while keeping the long tail framework-neutral; the new evidence justifies changing the earlier default.

### Positive Output

```text
Conditionally agree: standardize the two high-volume services on the shared runtime, but keep the framework-neutral scale-to-zero pool for smaller diverse services.

This is no longer a generic “standardization vs flexibility” debate. With 82% of requests concentrated in two services, one runtime covering both, a benchmarked 38% GPU-hour reduction, and a one-sprint migration, the optimization has enough evidence to justify a targeted split model.

Recommended path:

1. Create a high-volume optimized runtime lane for the two dominant services.
2. Enable batching there, with latency/error/SLO guardrails.
3. Keep the existing neutral scale-to-zero pool for low-volume and heterogeneous services.
4. Preserve a stable serving contract so future services are not forced into the optimized runtime by default.
5. Roll out via canary, prove GPU-hour savings under production traffic, then migrate the second service.

Non-negotiable boundary: do not turn this into platform-wide runtime standardization. The data supports standardizing the hot path, not collapsing the whole serving architecture into one runtime.

I would change this recommendation if the 38% gain does not survive production latency constraints, the migration expands beyond one sprint, or ownership/rollback for the shared runtime is unclear.
```

### Negative Output

```text
My recommendation: change the recommendation, but narrow it.

Adopt the shared runtime for the two dominant services and use batching there, because 82% of traffic plus a benchmarked 38% GPU-hour reduction is real evidence. Keep the framework-neutral scale-to-zero pool for smaller, diverse services.

This is not inconsistency. The earlier recommendation was correct under uncertainty and diversity. The new data says the workload is not evenly distributed, so the architecture should split into two lanes:

1. **Hot path:** one optimized runtime for the two high-volume services.
2. **Long tail:** framework-neutral scale-to-zero support for smaller services.

The message to teams should be: “We are not standardizing every service on one framework. We are optimizing the dominant request path where measured usage and benchmark data justify it. Other runtimes remain supported through the neutral pool.”

Non-negotiable boundary: do not turn this into a blanket mandate. Future migrations should require similar evidence: traffic concentration, runtime compatibility, measured cost/performance gain, bounded migration effort, and a rollback path.
```

## TS-02 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: AI platform operations
- Score target: `{"configuration": "skill", "scenario_id": "TS-02", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation: standardize the high-volume services on the proven runtime while keeping the long tail framework-neutral; the new evidence justifies changing the earlier default.

### Positive Output

```text
My stance: Conditionally agree.

My recommendation: standardize the two high-volume services on the shared runtime and benchmarked batching path, but keep the framework-neutral scale-to-zero pool as the platform contract for the diverse smaller services.

Reasons: the new evidence is material. If two services drive 82% of requests, one runtime can serve both, batching cuts GPU-hours by 38%, and migration fits in one sprint, then the earlier neutral-by-default position should narrow. Optimize the hot path.

Needs care: do not turn “standardize the high-volume services” into “standardize the whole platform.” The non-negotiable boundary is preserving runtime diversity behind a stable pool/scheduler interface for smaller services.

What would change my judgment: failed p95/p99 latency under batching, weaker real production savings than the benchmark, migration scope expanding beyond one sprint, or new evidence that smaller services are about to become significant request volume.
```

### Negative Output

```text
Stance: Conditionally agree.

Recommendation: Change the recommendation to a two-tier model: move the two dominant services onto the shared runtime with batching, while keeping the framework-neutral scale-to-zero pool as the default for smaller diverse services.

Reasons:
- The decision context changed materially: 82% of requests, one compatible runtime, 38% GPU-hour reduction, and one-sprint migration cost.
- Framework-neutrality is still valuable for the long tail, but applying it uniformly now leaves a large, measured efficiency gain on the table.
- This is not inconsistency; it is evidence-based specialization for a hotspot.

Be careful: do not frame this as “standardize everything on one runtime.” That would rightly worry other teams.

What would change my judgment: if the batching benchmark fails in production, migration expands beyond one sprint, the top-service traffic share drops sharply, or the shared runtime creates unacceptable operational coupling.
```

## TS-03 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Product onboarding
- Score target: `{"configuration": "baseline", "scenario_id": "TS-03", "score_type": "pair"}`

### Expected Core Recommendation

Default to an optional progressive checklist with instrumentation under the original evidence; run a time-boxed experiment before making setup mandatory.

### Positive Output

```text
My stance: **do not make the full checklist mandatory yet.**

I recommend a **lightweight optional checklist with selective hard gates** only for setup steps that are required to prevent broken, unsafe, or materially misleading use. Everything else should be encouraged through progress indicators, contextual prompts, reminders, and admin nudges after the user reaches first value.

The key issue is that “disciplined” is not the same as “effective.” With anecdotal evidence and inconclusive activation data, a mandatory flow would be a policy bet disguised as product rigor. It may improve completion, but it could also suppress activation by delaying the moment users understand why the setup matters.

Use this as the first phase:

- Optional checklist shown early, easy to resume.
- Required gates only for critical items: security, billing, compliance, data import integrity, or features that literally cannot work without setup.
- Track completion rate, skipped steps, time-to-first-value, activation, retention, support tickets, and underconfigured-account incidents.
- Revisit mandatory setup only if data shows underconfiguration is causing meaningful harm and mandatory completion improves outcomes without unacceptable drop-off.

What would change my recommendation: clear evidence that incomplete setup creates serious customer failure, security/compliance exposure, or high support cost, and that gating improves downstream success more than it hurts activation.
```

### Negative Output

```text
I recommend a lightweight optional checklist as the default, with mandatory gates only for truly critical setup steps.

A fully mandatory checklist is not justified by the current evidence. If activation data is inconclusive and the risk is slowing users before they see value, forcing setup upfront is likely premature. But a purely passive optional checklist may also fail if underconfiguration creates later churn or support load.

Use this approach:

1. Let users reach the core value quickly.
2. Show an optional checklist immediately after first value or in-product onboarding.
3. Make only essential items mandatory: security, billing, compliance, data integrity, or anything that would break the product experience.
4. Instrument the funnel: completion rate, time-to-value, activation, retention, support tickets, and underconfigured-account outcomes.
5. Run an experiment before making the whole checklist mandatory.

What would change the recommendation: clear evidence that checklist completion strongly improves retention, reduces costly failures, or prevents serious account misconfiguration without materially hurting activation.

So: default to optional, but not invisible. Progressive, contextual, measured.
```

## TS-03 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Product onboarding
- Score target: `{"configuration": "skill", "scenario_id": "TS-03", "score_type": "pair"}`

### Expected Core Recommendation

Default to an optional progressive checklist with instrumentation under the original evidence; run a time-boxed experiment before making setup mandatory.

### Positive Output

```text
Stance: Disagree.

Recommendation: Default to a lightweight optional checklist, but make critical setup steps strongly prompted, measurable, and recoverable after first use.

Reasons: A mandatory flow is solving for completeness before proving incompleteness is the main activation problem. With anecdotal evidence and inconclusive activation data, forcing everyone through setup risks adding friction without confirmed upside. Discipline is not the same as correctness; a mandatory checklist can create fake completion if users rush through it just to enter the product.

Watch out: Optional cannot mean invisible. Underconfigured accounts need detection, reminders, and clear “next best setup step” prompts inside the product.

What would change my judgment: Evidence that underconfiguration materially causes failed onboarding, support burden, churn, compliance risk, or unusable first sessions, and that a mandatory flow improves those outcomes without unacceptable activation drop-off.
```

### Negative Output

```text
Stance: Conditionally agree.

Recommendation: Use a lightweight optional checklist as the default, but make only truly critical setup steps mandatory. Then run a controlled experiment before expanding mandatory requirements.

Reasons:
- Current evidence is too weak to justify adding broad onboarding friction.
- The biggest early risk is delaying time-to-value before users understand why setup matters.
- Optional does not mean invisible: use contextual nudges, progress indicators, reminders, and in-product prompts after the user reaches first value.
- A hybrid model lets the team protect against serious underconfiguration without turning onboarding into a gate.

Watch out: if “optional” simply means users can ignore essential configuration forever, the product may create downstream support, security, or activation problems. Define which missing setup items are harmless versus dangerous.

What would change my judgment: evidence that underconfigured accounts materially reduce activation, retention, security, revenue, or support efficiency more than the mandatory flow harms time-to-value. Until then, do not make the full checklist mandatory.
```

## TS-04 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Product onboarding
- Score target: `{"configuration": "baseline", "scenario_id": "TS-04", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation for enterprise admins only: adopt the targeted mandatory checklist, keep self-serve optional, and continue monitoring friction because the new evidence changed the tradeoff.

### Positive Output

```text
Conditionally adopt it.

Roll out the targeted mandatory checklist for **enterprise admins only**, because the evidence is now strong enough for that segment: activation rose from 41% to 58%, support tickets dropped 22%, and trial completion did not measurably decline.

Do **not** generalize it to self-serve users yet. They were not in the experiment, and mandatory onboarding can behave very differently for lower-intent or faster-moving users.

Recommended rollout:

1. Make it the enterprise-admin default.
2. Keep the checklist narrowly focused on activation-critical setup steps.
3. Roll out gradually with rollback.
4. Continue tracking activation, trial completion, support tickets, admin satisfaction, time-to-first-value, and paid conversion.
5. Run a separate self-serve test before changing that path.

The short version: the old default should change for enterprise admins, but not for everyone.
```

### Negative Output

```text
I recommend changing it to a mandatory checklist **only for enterprise admins**, with explicit guardrails.

The evidence is strong enough: activation rose from 41% to 58%, support tickets dropped 22%, and trial completion did not measurably fall. That means the old “low-friction” principle is losing to a better version of itself for this segment: reducing avoidable confusion is also reducing friction.

But do not generalize this to all users. Self-serve users were not tested, so making it mandatory for them would be an unjustified leap.

My recommendation:

1. Make the enterprise admin checklist mandatory.
2. Keep it targeted to setup actions that directly affect activation.
3. Preserve optional or progressive onboarding for self-serve users.
4. Roll it out with monitoring for activation, trial completion, support volume, time-to-value, and checklist abandonment.
5. Revisit after another fixed window, especially if enterprise composition or sales motion changes.

The principle should be reframed from “never add required steps” to “never add required steps unless they measurably reduce user failure.” This experiment meets that bar for enterprise admins.
```

## TS-04 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Product onboarding
- Score target: `{"configuration": "skill", "scenario_id": "TS-04", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation for enterprise admins only: adopt the targeted mandatory checklist, keep self-serve optional, and continue monitoring friction because the new evidence changed the tradeoff.

### Positive Output

```text
My position: Conditionally agree.

My recommendation: adopt the targeted mandatory checklist for enterprise admins only, with a staged rollout and explicit guardrails. Keep the optional progressive checklist for self-serve users until that segment is tested.

Reasoning: the new experiment materially changes the decision. Activation moved from 41% to 58%, support tickets dropped 22%, and trial completion did not measurably decline. That is strong enough to override the earlier default for enterprise admins.

Non-negotiable boundary: do not generalize this to all users. Self-serve users were not in the test, and mandatory onboarding can easily become conversion friction in a lower-touch segment.

Ship it as a reversible enterprise-admin policy, monitor activation, checklist completion, trial completion, support volume, time-to-first-value, and qualitative complaints. My judgment would change if the gains disappear in rollout, if trial completion or paid conversion drops later, or if self-serve tests show different behavior.
```

### Negative Output

```text
Position: Conditionally agree.

Recommendation: Make the checklist mandatory only for enterprise admins, not globally. Keep self-serve on the optional progressive checklist until tested separately.

Reasoning: The experiment changed the evidence. For enterprise admins, the mandatory checklist materially improved activation from 41% to 58%, reduced support tickets by 22%, and did not hurt trial completion. That is not a small preference signal; it suggests the “low-friction” principle was being over-applied to a segment that benefits from more guided setup.

Risk: Do not turn this into a blanket product philosophy reversal. Enterprise admin onboarding likely has more coordination, configuration, and risk than self-serve onboarding. The test says mandatory guidance helps that segment; it says nothing about self-serve users.

What would change my judgment: If follow-up data shows higher downstream churn, lower expansion, admin frustration, or hidden support escalation after trial completion, then mandatory may be masking friction rather than solving it. If self-serve tests show similar gains without completion loss, then expand carefully by segment.
```

## TS-05 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Release management
- Score target: `{"configuration": "baseline", "scenario_id": "TS-05", "score_type": "pair"}`

### Expected Core Recommendation

Keep the release freeze under the original evidence; offer a narrow exception path only for tested fixes with clear rollback, not untested feature work.

### Positive Output

```text
Recommendation: keep the release freeze.

The late change is not justified by the facts given. It is visible and customer-facing, but it is not tied to revenue, an outage, or a compliance deadline, and it has not been tested across integrations. That makes it a quality and coordination risk, not an urgent release requirement.

The customer-centric move is not “ship the request immediately.” It is to protect the release, tell the customer clearly that the change will go into the next qualified release, and offer a concrete date or validation plan.

I would only change that recommendation if the team can prove the change is isolated, fully integration-tested, behind a safe rollout/rollback mechanism, and owned through release support. Otherwise: freeze holds.
```

### Negative Output

```text
Keep the release freeze.

The late change does not meet a strong exception threshold: no revenue commitment, outage, or compliance deadline, and it has not been tested across integrations. That is exactly the class of change a freeze is meant to block.

Recommended path: defer the feature to the next release or a planned patch after integration testing passes. If the customer request is highly visible, handle it with communication: acknowledge it, give a target window, and optionally offer a controlled beta only after validation.

I would only allow it if all of these are true: full integration test evidence, feature flag or rollback path, clear owner on call, explicit release-owner approval, and a business reason strong enough to justify risking the broader release. On the facts given, hold the freeze.
```

## TS-05 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Release management
- Score target: `{"configuration": "skill", "scenario_id": "TS-05", "score_type": "pair"}`

### Expected Core Recommendation

Keep the release freeze under the original evidence; offer a narrow exception path only for tested fixes with clear rollback, not untested feature work.

### Positive Output

```text
My stance: Disagree with allowing the late feature change.

My recommendation: Keep the release freeze. Offer the customer a committed follow-up path: next release, limited beta, or feature-flagged delivery only after integration testing is complete.

Reasons:
- The freeze exists to protect quality and coordination; this case does not meet the bar to override it.
- The change is not tested across integrations, so the risk is broader than the visible customer benefit.
- There is no revenue commitment, outage, or compliance deadline creating true urgency.
- Responsiveness can be shown through clear communication and prioritization, not by weakening release discipline.

Need to be careful: do not dismiss the customer request. Give them a concrete date, owner, and validation plan.

What would change my judgment: a hard contractual/compliance deadline, an active production incident, or proof that the change is isolated, fully tested across integrations, feature-flagged, and rollback-ready.
```

### Negative Output

```text
Stance: Agree.

Recommendation: Keep the release freeze. Do not allow the late feature change into this release unless it qualifies as an emergency exception.

Reasons: The freeze exists to protect quality and coordination. The change has not been tested across integrations. The customer request is visible, but there is no revenue commitment, outage, or compliance deadline strong enough to justify increasing release risk.

Watch out: Do not ignore the customer. Offer a clear follow-up path: commit to the next release, a patch window after integration testing, or a controlled beta if appropriate.

What would change my judgment: A contractual deadline, active production incident, compliance obligation, proven integration test coverage, a very small reversible change, and an approved rollback plan.
```

## TS-06 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Release management
- Score target: `{"configuration": "baseline", "scenario_id": "TS-06", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation: allow the minimal tested security fix through the freeze with approval, audit, and rollback because the new risk outweighs freeze purity.

### Positive Output

```text
My recommendation: bend the freeze for this security fix only.

The prior freeze position no longer holds because the decision context changed materially: the RC now has a plausible unauthorized data access defect. A freeze should prevent avoidable release churn, not preserve a known security exposure when a minimal tested patch and rollback path exist.

Proceed with a narrow exception:

- Merge only the minimal security patch.
- Require expedited security/release owner sign-off.
- Run targeted regression plus a small critical-path smoke check around auth and data access.
- Keep rollback ready and assign an owner for post-release monitoring.
- Document the exception: defect, risk, patch scope, tests, rollback plan, and approval.

Do not reopen the release for adjacent cleanup or “while we are here” fixes. The freeze bends for the security defect; it remains in force for everything else.
```

### Negative Output

```text
Break the freeze, but only through a formal security exception.

The previous recommendation depended on normal release-risk tradeoffs. That changed: unauthorized data access with plausible exploitation is a release-blocking security defect. Shipping that knowingly is worse discipline than making a controlled exception.

Recommended path:

1. Approve the minimal patch only.
2. Document the exception: defect, impact, exploit plausibility, patch scope, tests passed, rollback plan, approvers.
3. Run the smallest credible final verification: targeted regression plus release smoke checks.
4. Freeze remains in force for everything else.
5. Communicate it as security-risk containment, not “the freeze is flexible.”

The precedent risk is real, but manageable. The bad precedent would be casual freeze-breaking. A tightly governed security exception is exactly what disciplined release management should allow.
```

## TS-06 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Release management
- Score target: `{"configuration": "skill", "scenario_id": "TS-06", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation: allow the minimal tested security fix through the freeze with approval, audit, and rollback because the new risk outweighs freeze purity.

### Positive Output

```text
Stance: Conditionally agree.

Recommendation: bend the release freeze only for the minimal security patch, ship it through an emergency exception, and keep every unrelated change frozen.

Reasons:
- The decision context materially changed: plausible unauthorized data access is a release-blocking security risk.
- Keeping the freeze unchanged would preserve process discipline while knowingly shipping an exploitable candidate, which is the wrong priority.
- The fix is described as minimal, has passed targeted regression tests, and rollback is prepared, so the release risk is bounded enough to justify the exception.

Need to be careful: targeted regression tests are not full-release confidence. The non-negotiable boundary is scope control: no opportunistic fixes, refactors, cleanup, or product changes in the exception.

What would change my judgment: if the patch is not actually minimal, regression evidence is weak, rollback is unproven, or the vulnerability can be mitigated safely without changing the release candidate.
```

### Negative Output

```text
Position: Disagree with keeping the freeze unchanged.

Recommendation: Break the freeze through a controlled security exception and ship only the minimal patch.

Reasons: The decision context changed materially. Unauthorized data access with plausible exploitation is not a normal late-cycle bug; it is a release-blocking security risk. The patch is minimal, has targeted regression evidence, and rollback is prepared, so the operational risk is bounded. Keeping the freeze now protects process optics at the expense of user security.

Be careful: Do not “reopen the release.” Make this a documented exception: security defect only, no bundled cleanup, explicit approver, targeted test evidence, rollback owner, and post-release review.

What would change my judgment: if exploitation is not actually plausible, the patch has untested blast radius, rollback is not credible, or there is a safer immediate mitigation that avoids changing the release candidate.
```

## TS-07 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Data reporting
- Score target: `{"configuration": "baseline", "scenario_id": "TS-07", "score_type": "pair"}`

### Expected Core Recommendation

Default to the normalized active-account metric as the decision metric, include total usage as context, and explain the denominator tradeoff instead of hiding either metric.

### Positive Output

```text
I recommend making the normalized active-account metric the headline, with the simple total-usage metric as supporting context.

Suggested framing:

> Usage grew 18% in total, while usage per active account grew 2%, indicating most of the increase came from customer growth rather than materially deeper usage.

Reason: the headline metric should answer the program review question, not just be the easiest story. If leadership is evaluating whether the program improved engagement or usage intensity, the normalized metric is the more honest KPI. The 18% total growth is still useful, but as context: it shows scale increased.

Use total usage as the headline only if the review is specifically about aggregate demand, infrastructure load, revenue-linked volume, or market footprint. Otherwise, leading with 18% risks overstating program impact.
```

### Negative Output

```text
Recommend the normalized active-account metric as the headline, with the simple total metric shown immediately as context.

Suggested headline:

> Active-account-normalized usage rose 2%; total usage rose 18% as the customer base grew.

Reason: for a program review, the headline should reflect program performance, not just growth in the number of accounts. The 18% total metric is useful, but if used alone it overstates engagement improvement because it mixes usage intensity with customer growth.

The only case where I’d headline the 18% is if the review is about business scale, infrastructure demand, or market footprint. If the question is “did the program make accounts use more?”, the 2% normalized metric is the honest lead.
```

## TS-07 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Data reporting
- Score target: `{"configuration": "skill", "scenario_id": "TS-07", "score_type": "pair"}`

### Expected Core Recommendation

Default to the normalized active-account metric as the decision metric, include total usage as context, and explain the denominator tradeoff instead of hiding either metric.

### Positive Output

```text
My stance: Disagree.

My recommendation: Use the normalized active-account metric as the headline, and show the simple total-usage metric as supporting context.

Reason: the headline should measure program impact, not just aggregate growth. A `+18%` total usage number is clearer, but it risks implying the program drove stronger engagement when the better-controlled metric only rose `+2%`. Since no one is asking to hide the simple metric, the honest executive story is:

“Total usage rose 18%, largely tracking customer growth; normalized usage per active account rose 2%.”

Need to watch: the normalized metric is less punchy, so explain it in one sentence and avoid technical framing.

What would change my judgment: if the program goal is explicitly total platform volume, capacity planning, revenue-linked usage, or market expansion, then total usage could be the headline. Otherwise, use the normalized metric.
```

### Negative Output

```text
Stance: Conditionally agree

Recommendation: Make the normalized active-account metric the headline, and show total usage (+18%) as a supporting context metric.

Reason: The headline should answer whether the program improved usage intensity, not just whether the customer base grew. Total usage is valid, but as the main metric it overclaims program impact because it mixes account growth with behavioral change.

Watch-out: The normalized metric rose only 2%, so the story is less impressive. Do not bury that. Say plainly: “Total usage grew 18%, largely supported by account growth; normalized active-account usage grew 2%, which is the cleaner measure of program lift.”

What would change my judgment: If the program goal was explicitly total platform volume, capacity demand, revenue exposure, or aggregate adoption, then total usage could be the headline. But for a program-effectiveness review, normalized usage should lead.
```

## TS-08 baseline pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Data reporting
- Score target: `{"configuration": "baseline", "scenario_id": "TS-08", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation for this report: disclose the denominator bug, use total usage only as a temporary incomplete proxy, and commit to restating the normalized metric after repair.

### Positive Output

```text
Conditionally agree: lead with total usage for this report, but do not pretend it answers the same question as normalized active-account usage.

My recommendation: make total usage the temporary headline metric, clearly label the normalized active-account metric as unavailable/compromised, and include a note that final decisioning will be revisited once the repaired normalized metric is available next week.

Reasons:
- A metric with a corrupted denominator for 30% of accounts is not decision-grade.
- Total usage is complete, so it is the more honest current evidence.
- Hiding the switch would be worse than the switch itself; the report should explain the audit finding and the temporary metric change.
- Total usage can show aggregate demand, but it may over-weight large accounts, so it should not be used alone for account-level fairness or efficiency conclusions.

Boundary: do not frame this as “we changed the decision metric permanently.” Frame it as “normalized active-account usage remains the intended metric, but is temporarily withheld due to a known data-quality issue.”

Suggested wording:

> Due to an audit finding affecting the active-account denominator for approximately 30% of accounts, we are not using normalized active-account usage as the lead metric in this report. We are temporarily leading with total usage, which is complete, while the normalized metric is repaired. Once the corrected normalized metric is available next week, we will revisit any decisions that depend on account-normalized comparisons.
```

### Negative Output

```text
Recommend: do **not** quietly switch the official decision metric to total usage.

Treat this as a **data-quality incident on the primary metric**:

1. The normalized active-account metric is currently invalid because 30% of denominators are corrupted.
2. The repaired normalized metric remains the intended decision metric once available next week.
3. Total usage can be used now only as an **interim proxy or supporting signal**, not as a replacement metric.

If the decision can wait, wait one week.

If the decision cannot wait, make a provisional call using total usage plus sensitivity checks, and say explicitly:

> Our preselected normalized metric is temporarily unusable due to a confirmed denominator ingestion bug affecting 30% of accounts. We are using complete total-usage data as an interim signal, but the decision will be revalidated against the repaired normalized metric next week.

Also check the unaffected 70% of accounts separately. If total usage looks good but the clean-account normalized slice looks weak, that is a warning that total usage may be masking account-mix effects.

The non-negotiable boundary: do not present total usage as equivalent to the normalized metric. It answers a different question. The cleanest governance move is transparency, provisional status, and a precommitted rerun when the repaired metric lands.
```

## TS-08 skill pair

- Type: `pair`
- Suite: `tradeoff-stability`
- Domain: Data reporting
- Score target: `{"configuration": "skill", "scenario_id": "TS-08", "score_type": "pair"}`

### Expected Core Recommendation

Update the recommendation for this report: disclose the denominator bug, use total usage only as a temporary incomplete proxy, and commit to restating the normalized metric after repair.

### Positive Output

```text
My stance: Conditionally agree.

My recommendation: Lead with total usage temporarily, and explicitly demote the normalized active-account metric to a caveated, non-decision metric until the denominator is repaired next week.

Reasons:
- The prior recommendation changed because the evidence changed: the normalized metric is materially corrupted for 30% of accounts.
- A normalized metric with a bad denominator is worse than incomplete nuance; it can produce false precision.
- Total usage is complete, so it is the more defensible headline for this specific report.
- The report should preserve continuity by stating this is a temporary metric substitution, not a new long-term decision framework.

Need to be careful: total usage can overweight large accounts and obscure per-account engagement. Do not let readers interpret it as equivalent to normalized active-account performance.

What would change my judgment: if total usage also has material quality issues, if the corrupted 30% is immaterial to the report’s decision, or if the report can wait one week for the repaired normalized metric.
```

### Negative Output

```text
Position: Conditionally agree with pausing the normalized metric, but not with replacing it as the final decision metric.

Recommendation: Treat the current normalized active-account metric as invalid, use total usage only as an interim contextual signal, and defer the final decision until the repaired normalized metric is available next week unless there is a hard deadline.

Reasoning:
- A metric with a corrupted denominator for 30% of accounts is not decision-grade.
- Total usage answers a different question than normalized active-account usage; switching to it because it looks better would be hard to defend.
- Waiting one week is low-cost compared with damaging metric credibility.
- The defensible move is transparency: disclose the defect, preserve the original metric intent, and rerun with the repaired version.

Boundary: Do not present total usage as the new primary decision metric unless the decision question has genuinely changed from “usage per active account” to “aggregate usage.”

Suggested wording:

> The predefined normalized active-account metric is temporarily invalid because audit evidence shows a denominator defect affecting roughly 30% of accounts. We will not use the corrupted version for the decision, and we will not replace it with total usage as the primary metric because that changes the decision question. Until the repaired normalized metric is available next week, total usage may be shown only as a complete directional/contextual indicator. The final decision should be made or confirmed against the repaired normalized metric.

What would change my judgment: a non-deferrable decision deadline, proof that the denominator corruption does not change the normalized conclusion, or a formal decision that aggregate usage is now the actual business objective.
```
