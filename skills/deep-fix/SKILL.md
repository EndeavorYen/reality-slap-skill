---
name: deep-fix
description: Use when a long, repeated, or high-impact repair keeps drifting, revisiting the same blocker, expanding into minor work, or needs root-cause execution with explicit completion proof.
---

# Deep Fix

Use this skill only when explicitly invoked. It is an execution workflow for a
real repair, not a longer planning response. Keep Reality Slap as the independent
checkpoint; do not turn it into the implementer.

## Durable Goal Contract

At the start, create or refresh one durable goal when goal tools are available.
Explicit `$deep-fix` or `/deep-fix` invocation counts as a request to set that
goal. Reuse a matching active goal instead of creating a parallel one.

Lock these fields before changing production behavior:

- **User-visible outcome**: what will become observably better.
- **Current evidence**: the smallest reproduction, logs, or artifact proving the defect.
- **Completion evidence**: focused test, wider regression check, runtime or live smoke, and deliverable when applicable.
- **Non-goals**: adjacent improvements that do not need to ship for this outcome.

Do not redefine success around the easiest passing subset.

## Root Cause Before Repair

1. Reproduce the failure with the smallest representative case.
2. Trace it to the owning layer and compare the last known-good path when available.
3. State the root-cause hypothesis and the evidence that could disprove it.
4. Write or update the smallest failing behavior test.
5. Implement the smallest production change that addresses the owning cause.

Do not present a workaround as a root-cause fix. A temporary mitigation must be
named as temporary and must not close the goal.

## Execution Loop

- Work on the highest-leverage unresolved requirement.
- Keep at most one implementation phase active.
- Park minor findings unless they block correctness, proof, or the user-visible outcome.
- Prefer an existing extension point over new framework machinery.
- Continue autonomously through implementation and verification unless approval,
  credentials, safety, or an irreversible action requires the user.

## Phase Boundary Checkpoint

Apply Reality Slap's **Execution Integrity Check** after a meaningful phase, not
after every paragraph, tool call, or tiny edit. Required boundaries are:

- after the root cause is supported;
- after the first behavior change passes its focused test;
- before adding scope, retries, abstractions, or compatibility layers;
- before claiming completion.

Use this compact checkpoint:

```text
Goal drift: No / Yes - <evidence>
Over-design: No / Yes - <work to remove or avoid>
User-visible progress: <what measurably improved>
Weakest remaining proof: <highest-risk gap>
Decision: Continue / Correct / Stop
Next: <single highest-leverage action>
```

If the decision is `Correct`, update the plan and immediately act on the
correction. Do not ask the user to repeat the command.

## Stop And Completion Rules

- Stop expanding when two repair loops add no new quality, reliability, or proof.
- Escalate a real setup or authorization blocker with the exact missing prerequisite.
- Do not mark complete from intent, documents, stale artifacts, or a partial green test.
- Completion requires current evidence for every locked completion condition.
- Run the focused test, relevant wider suite, and the smallest practical runtime
  or live smoke when the behavior depends on live wiring.
- Report the outcome, proof, and any residual risk briefly; do not narrate every attempt.
