# Deep Fix Fixed Repair Set Design

## Goal

Keep one explicit `$deep-fix` entry while allowing one invocation to repair a
user-supplied list of problems in order. Freeze that list before edits so the
agent completes the requested set without expanding into minor cleanup,
speculative redesign, or over-engineering.

## Node contract

- `node_id`: `deep-fix`
- `inputs`: one explicitly invoked repair request containing one problem or an
  ordered list of user-visible problems
- `outputs`: a per-item `fixed`, `blocked`, or `not-reproduced` result, current
  focused proof for each fixed item, one final necessary suite result, and a
  concise residual-risk report
- `blocked_output`: the affected item, exact missing prerequisite, and whether
  independent later items were still attempted
- `release_risk`: scope creep can alter unrelated behavior; stopping at the
  first blocked item can leave independent requested repairs unfinished; a
  broad combined patch can hide which requested outcome was actually proved

## One repair-set contract

Replace “one user-visible problem” with “one explicit repair set.” A set may
contain one or more user-named problems but remains one durable goal and one
canonical `$deep-fix` invocation.

Before changing production behavior, freeze an ordered repair ledger. Each
entry records the user-visible outcome and focused proof. No newly discovered
issue becomes a peer ledger item automatically.

## Sequential issue loop

Process ledger items in user order:

1. Reproduce only the current item and identify root-cause evidence.
2. Make the smallest correct patch for that root cause.
3. Rerun the same focused proof and mark the item `fixed`, `blocked`, or
   `not-reproduced`.
4. Continue to the next independent item.

If multiple items share one proven root cause, patch it once and run each
item's focused proof before marking them complete.

The two-no-evidence-loop stop applies per item. A blocked item does not stop
independent later items; it stops the set only when the same prerequisite
blocks the remaining ledger.

## Scope admission gate

Unlisted work may be changed only when evidence proves it is a required
dependency of a ledger item because it:

- is the shared root cause of a requested outcome;
- prevents a correct result, security failure, or data loss; or
- is required to run a meaningful completion proof.

All cosmetic cleanup, naming changes, abstractions, dependency upgrades,
pre-existing failures, speculative performance work, and architectural
redesign remain report-only. When necessity is ambiguous, do not fix it.

## Verification and checkpoints

Run each focused proof once before and once after its patch. Inspect the scoped
diff after every item. Run the full suite once at the end only when repository
policy or cross-item risk requires it.

Do not narrate straight-line execution. Between items, a compact ledger update
is allowed. Use the existing exception checkpoint only for a second loop,
blocker, or scope drift, and identify the current item.

## Evaluation

Forward-test three fresh workspaces:

1. three independent requested bugs plus planted unrelated cleanup;
2. three requested outcomes with one shared root cause;
3. one externally blocked item followed by two independent fixable items.

For each scenario, verify requested outcomes, planted-minor preservation,
focused tests, production diff, and blocked behavior. Publish exact prompts,
results, and limitations. Do not call this a universal quality or speed claim.

## Documentation and installation

Update the Deep Fix UI description, default prompt, README usage, and benchmark
boundary. Keep one entry and no flags or modes. After the repository release
gate passes, install the repository copy into this machine's global Codex skill
directory and verify source/install hashes match.

## Non-goals

- discovering an open-ended backlog;
- repairing every issue found during inspection;
- parallel mutation of related files;
- adding a second command, batch mode, configuration layer, or dependency.
