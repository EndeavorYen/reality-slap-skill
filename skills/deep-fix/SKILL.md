---
name: deep-fix
description: Use only when explicitly invoked to fix one problem with a smallest-patch, root-cause workflow and a hard stop after two no-evidence loops.
metadata:
  execution:
    durable_goal:
      required: true
      constraints:
        - >-
          Fix one user-visible problem with the smallest correct patch.
        - >-
          Stop after two consecutive repair loops add no new evidence.
---

# Deep Fix

Use this skill only when explicitly invoked as `$deep-fix`. It is one bounded
workflow for one real repair, not a broad cleanup or a longer planning response.

## One Repair Contract

Runtimes with durable-goal support should atomically create or reuse one goal
before loading this skill. Explicit `$deep-fix` invocation counts as a request
to set that goal. Reuse a matching active goal instead of creating another one.

Fix one user-visible problem. Before changing production behavior, lock:

- the problem the user will observe as fixed;
- the smallest reproduction or current evidence;
- the focused test or check that will prove completion;
- unrelated work that must not be changed.

Do not broaden the goal. Report unrelated findings without fixing them.

## Root Cause Before Repair

1. Reproduce the failure with the smallest representative case.
2. Trace the failure to its owning layer.
3. State the root-cause hypothesis and what evidence would disprove it.
4. Write or update the smallest focused failing test.
5. Implement the smallest correct patch for that cause.

Do not present a workaround as a root-cause fix. A temporary mitigation must be
named as temporary and must not close the goal.

## Five Rules

1. Keep one user-visible problem as the goal.
2. Find the root cause before changing production behavior.
3. Make the smallest correct patch. Report unrelated findings without fixing them.
4. Run the focused test first. Run the full test suite only when it is necessary
   for the changed behavior or repository release policy, and run it once.
5. Stop when two consecutive repair loops add no new evidence or effective change.
   Disproving a root-cause hypothesis counts as new evidence.

## One-Line Checkpoint

After supporting the root cause, after the first focused test result, and before
claiming completion, write exactly one compact checkpoint:

```text
Progress: <new evidence or effective change> | Scope: OK / Drift | Decision: Continue / Stop | Next: <one action>
```

If scope is `Drift`, stop and report what would require the user to expand the
goal. Do not silently add retries, abstractions, compatibility work, dependency
upgrades, public API changes, or fixes for pre-existing failures.

Complete only when the focused proof is current and the user-visible problem is
fixed. Report the fix, proof, and residual risk briefly. If blocked, report the
exact missing prerequisite. Do not narrate every attempt.
