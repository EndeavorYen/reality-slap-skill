# Deep Fix Sol High A/B Evaluation — 2026-07-21

## Verdict

The final three-action-group Deep Fix workflow demonstrated a narrow, repeatable
advantage on the controlled repair fixture:

- both arms produced the correct one-line production patch in 3/3 runs;
- both arms passed the focused regression in 3/3 runs;
- Deep Fix reduced median wall time from 70.7s to 43.7s (38.1%);
- Deep Fix reduced median input tokens from 274,683 to 132,935 (51.6%);
- Deep Fix did not inspect or run the unrelated legacy test; every baseline run
  inspected unrelated legacy files and one baseline run executed the unrelated test.

This proves the bounded fast path on this fixture. It does not prove that every
real repository repair will be faster or correct.

## Method

- Runtime: `codex exec --ephemeral --json`
- Model: `gpt-5.6-sol`
- Reasoning effort: `high`
- Runs: three paired A/B repetitions, with each pair launched concurrently
- Isolation: separate clean Git repositories with the same fixture commit
- Only treatment difference: the treatment prompt begins with `Use $deep-fix.`
- Skill SHA-256: `b37cf1446298594c8e0bbed8583168a4375371ec2048f3557079ddf4602160d7`

Baseline prompt:

```text
Fix the shipping bug: shipping_total(100) returns 110 instead of 105. PYTHONDONTWRITEBYTECODE=1 python3 test_pricing.py reproduces it. Do not modify tests and do not commit.
```

Treatment prompt:

```text
Use $deep-fix. Fix the shipping bug: shipping_total(100) returns 110 instead of 105. PYTHONDONTWRITEBYTECODE=1 python3 test_pricing.py reproduces it. Do not modify tests and do not commit.
```

The fixture contained `pricing.py` with a hard-coded fee of 10, a focused test
expecting a fee of 5, and a separate pre-existing failing legacy test. Success
required changing only `pricing.py`, passing the focused test, leaving tests
unchanged, and not committing.

Wall time is derived from each JSON `thread.started` UTC timestamp and the final
output artifact modification time. Artifact timestamps have one-second resolution.

## Final Results

| Run | Arm | Wall time | Input tokens | Output tokens | Reasoning tokens | Correct | Changed files | Unrelated legacy work |
|---|---|---:|---:|---:|---:|---|---|---|
| 1 | Baseline | 70.681s | 274,683 | 2,475 | 633 | yes | `pricing.py` | inspected and executed |
| 1 | Deep Fix | 46.670s | 133,299 | 1,701 | 893 | yes | `pricing.py` | none |
| 2 | Baseline | 67.936s | 247,374 | 1,958 | 513 | yes | `pricing.py` | inspected |
| 2 | Deep Fix | 43.731s | 132,206 | 1,253 | 614 | yes | `pricing.py` | none |
| 3 | Baseline | 73.555s | 294,317 | 2,690 | 795 | yes | `pricing.py` | inspected |
| 3 | Deep Fix | 40.402s | 132,935 | 1,533 | 617 | yes | `pricing.py` | none |
| Median | Baseline | 70.681s | 274,683 | 2,475 | 633 | 3/3 | one file | 3/3 |
| Median | Deep Fix | 43.731s | 132,935 | 1,533 | 617 | 3/3 | one file | 0/3 |

Thread IDs are retained for trace correlation:

- Run 1: baseline `019f8539-5ed0-7a50-af02-1d364a800aa1`, Deep Fix `019f8539-5bef-7c60-8400-6c3783887d95`
- Run 2: baseline `019f853b-00e7-7133-afa2-6b8e63e46679`, Deep Fix `019f853a-f505-7813-8dbe-799b87782f50`
- Run 3: baseline `019f853c-bf3c-7973-bab5-0616c96d0819`, Deep Fix `019f853c-a794-7f91-b601-9600ee6081d1`

## Blocked-Path Smoke

The installed final skill also ran against a fixture whose test directly required
the missing external environment variable `DEEP_FIX_AB_REMOTE_TOKEN=present` and
did not call the only permitted production file.

- Result: stopped with the exact external prerequisite
- File changes: none
- Full suite: not run
- Input/output/reasoning tokens: 77,877 / 1,107 / 673
- Thread: `019f8540-73b9-7ea2-9605-ea1bcb584ffa`

This confirms the final workflow still fails closed when no allowed source change
can affect the failure.

## Negative Evidence and Iteration

The first skill revision did not demonstrate an efficiency benefit. In two pilot
A/B cases it used 12.7% more input tokens on the blocked case and 6.6% more on the
successful repair. A second revision saved input tokens but had a 10.8% slower
median wall time because it split inspection, runner probing, status checks, and
generated-cache cleanup across too many round trips.

The final revision addressed the observed cause directly: use the provided
reproducer exactly, avoid unrelated enumeration, batch a straight-line repair
into three action groups, and do not spend a repair loop cleaning harmless test
artifacts. The final table reports only runs performed after that revision was
installed globally.

## Limits

- The sample is small (`n=3` paired runs) and uses one intentionally compact fixture.
- Model sampling and host load still introduce variance.
- The evaluation demonstrates scope control, fail-closed blocking, and a faster
  straight-line repair path; it does not yet validate multi-module or flaky bugs.
- A broader release claim should add larger real-repository cases without changing
  the prompt or scoring after results are observed.
