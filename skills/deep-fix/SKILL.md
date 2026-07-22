---
name: deep-fix
description: Use only when explicitly invoked to fix one explicit repair set in user order with smallest-patch, root-cause loops and a per-item hard stop after two no-evidence loops.
metadata:
  execution:
    durable_goal:
      required: true
      constraints:
        - >-
          Fix one explicit repair set with the smallest correct patches.
        - >-
          Stop an item after two consecutive repair loops add no new evidence.
---

# Deep Fix

Use this skill only when explicitly invoked as `$deep-fix`. It is one bounded
workflow for one explicit repair set, not a broad cleanup or a longer planning
response. It is the complete repair workflow. Do not load overlapping repair
workflow skills unless the user explicitly invoked them or higher-priority
instructions require it.

## One Repair-Set Contract

Runtimes with durable-goal support should atomically create or reuse one goal
before loading this skill. Explicit `$deep-fix` invocation counts as a request
to set that goal. Reuse a matching active goal instead of creating another one.

Treat one named problem as a one-item set. For multiple named problems, freeze an
ordered repair ledger before changing production behavior. For every item, lock:

- the user-visible outcome that will be fixed;
- the smallest reproduction or current evidence;
- the focused test or check that will prove completion;
- a `pending`, `fixed`, `blocked`, or `not-reproduced` status.

Process ledger items in user order. Do not add newly discovered peer items to the
ledger. Report unrelated findings without fixing them.

## Root Cause Before Repair: Per Item

For the current ledger item, keep a straight-line repair to three action groups:

1. In one read-only action, inspect only the named or owning files and reproduce
   the failure. Reuse an existing focused reproduction when one is provided.
   Use the provided reproduction command exactly. If none is provided, select one
   runner from the test file; do not probe alternatives. Do not enumerate unrelated
   files. Identify the root-cause evidence and what would disprove it.
   If the evidence does not reproduce the current item, make no production
   change, mark it `not-reproduced`, record the evidence, and continue to the next
   independent item.
2. For a reproduced item, make the smallest correct production patch for that
   cause.
3. In one verification action, run the same focused check once, inspect the diff,
   assign the item status, and continue to the next independent item. Do not
   repeat an unchanged passing check or reread unchanged evidence.

This runs each focused proof once before and once after the patch. When multiple
ledger items have one proven shared root cause, patch it once, then run every
affected item's focused proof before assigning their statuses.

Run the full test suite only when it is necessary for the changed behavior or
repository release policy, and run it once after the ledger. Prevent generated
test artifacts when the supplied runner supports it. Do not spend a repair loop
cleaning harmless generated artifacts.

## Scope Admission Gate

Change unlisted work only when evidence proves it is a required dependency of the
current named ledger outcome because omitting it would make the current named
outcome incorrect, directly introduce or worsen a security or data-loss defect in
that outcome, or make that outcome's completion proof meaningless.

Keep cosmetic cleanup, naming changes, abstractions, dependency upgrades,
pre-existing failures, speculative performance work, and architectural redesign
report-only. When necessity is ambiguous, do not fix it.

Do not present a workaround as a root-cause fix. A temporary mitigation must be
named as temporary and must not close the goal. Do not silently add retries,
abstractions, compatibility work, dependency upgrades, public API changes, or
fixes for pre-existing failures.

The two-no-evidence stop applies per item: stop an item when two consecutive
repair loops add no new evidence or effective change. Disproving a root-cause
hypothesis counts as new evidence; rereading files, restating the hypothesis, and
rerunning an unchanged check do not.

If an item is blocked, report its exact missing prerequisite and continue to the
next independent item. Stop the repair set only when the same prerequisite blocks
the remaining ledger.

## Exception Checkpoint

Do not emit a checkpoint on a straight-line repair. Emit one only before entering
a second repair loop, or when stopping for a blocker or scope drift:

```text
Progress: <new evidence or effective change> | Scope: OK / Drift | Decision: Continue / Stop | Next: <one action>
```

If scope is `Drift`, stop and report what would require the user to expand the
goal. Every exception checkpoint must identify the current ledger item.

Complete only when every ledger item has a current status and each fixed item has
a current focused proof. Report the ordered results, final suite when required,
and residual risk briefly. Do not narrate every attempt.
