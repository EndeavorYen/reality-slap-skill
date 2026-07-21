# Deep Fix README Proof Design

## Goal

Make Deep Fix's newly verified fast path visible and memorable without turning
the Reality Slap README into a two-product landing page or overstating a small
controlled benchmark.

## Information hierarchy

1. Keep Reality Slap as the README hero and primary product.
2. Add a compact Deep Fix proof strip immediately after the hero message.
3. Expand the existing `Deep Fix companion` section with the workflow, paired
   A/B results, blocked-path result, and links to the full evidence.

## Hero proof strip

Use one short positioning line: `Deep repair without deep wandering.`

Show four scan-friendly results from the final `gpt-5.6-sol`, `high` evaluation:

- `38% faster` median wall time;
- `52% fewer input tokens`;
- `3/3 correct one-file repairs`;
- `0 file changes when blocked`.

The strip must identify these as controlled paired results rather than universal
performance guarantees.

## Detailed Deep Fix section

Keep one canonical invocation: `Use $deep-fix <problem>`.

Explain the fast path as three action groups:

1. inspect the owning path and run the provided focused reproduction;
2. make the smallest root-cause production patch;
3. rerun the same proof, inspect the diff, and stop.

Add a compact median-results table comparing baseline and Deep Fix. State that
both arms were correct in 3/3 runs, while Deep Fix reduced median wall time from
70.7s to 43.7s and median input tokens from 274,683 to 132,935.

Include the blocked-path result: when the only permitted file could not affect a
missing external prerequisite, Deep Fix reported the exact blocker and changed
no files.

Link both the human-readable evaluation report and machine-readable JSON result.

## Claim boundary

State next to the results that the benchmark used one compact controlled fixture
with three paired runs. Claim the demonstrated bounded fast path, scope control,
and fail-closed behavior. Do not claim universal speedups, correctness on every
repository, or validation of multi-module and flaky failures.

## Verification

Update README guidance tests to require:

- the four proof-strip results;
- the three-action-group positioning;
- the canonical `$deep-fix` invocation;
- links to both evaluation artifacts;
- the controlled-fixture limitation.

Run the focused README/Deep Fix tests, then the complete release gate.
