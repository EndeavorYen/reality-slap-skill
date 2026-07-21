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
It is the complete repair workflow. Do not load overlapping repair workflow skills
unless the user explicitly invoked them or higher-priority instructions require it.

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

## Root Cause Before Repair: One Pass

Keep a straight-line repair to three action groups:

1. In one read-only action, inspect only the named or owning files and reproduce
   the failure. Reuse an existing focused reproduction when one is provided.
   Use the provided reproduction command exactly. If none is provided, select one
   runner from the test file; do not probe alternatives. Do not enumerate unrelated
   files. Identify the root-cause evidence and what would disprove it.
2. Make the smallest correct production patch for that cause. Report unrelated
   findings without fixing them.
3. In one verification action, run the same focused check once, inspect the diff,
   and stop. Do not repeat an unchanged passing check or reread unchanged evidence.

This runs the focused proof once before and once after the patch.

Run the full test suite only when it is necessary for the changed behavior or
repository release policy, and run it once. Prevent generated test artifacts when
the supplied runner supports it. Do not spend a repair loop cleaning harmless
generated artifacts.

Do not present a workaround as a root-cause fix. A temporary mitigation must be
named as temporary and must not close the goal. Do not silently add retries,
abstractions, compatibility work, dependency upgrades, public API changes, or
fixes for pre-existing failures.

Stop when two consecutive repair loops add no new evidence or effective change.
Disproving a root-cause hypothesis counts as new evidence; rereading files,
restating the hypothesis, and rerunning an unchanged check do not.

## Exception Checkpoint

Do not emit a checkpoint on a straight-line repair. Emit one only before entering
a second repair loop, or when stopping for a blocker or scope drift:

```text
Progress: <new evidence or effective change> | Scope: OK / Drift | Decision: Continue / Stop | Next: <one action>
```

If scope is `Drift`, stop and report what would require the user to expand the
goal.

Complete only when the focused proof is current and the user-visible problem is
fixed. Report the fix, proof, and residual risk briefly. If blocked, report the
exact missing prerequisite. Do not narrate every attempt.
