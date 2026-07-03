# Reality Slap A/B Runbook

This runbook describes the active stance-drift benchmark. The old broad banks
and historical result artifacts have been removed from the active repository
surface; do not use older local copies for current claims.

The active bank has two roles:

- `SD-01` through `SD-04` are failure-seeking cases. They should make the
  baseline struggle under realistic pressure to reverse or oversimplify a
  recommendation.
- `SD-05` and `SD-06` are calibration guardrails. They keep the skill from
  becoming stubborn for its own sake by requiring it to accept material new
  evidence or preserve a nuanced middle policy.

## 1. Validate The Bank

```bash
python3 scripts/validate_eval_bank.py \
  --input evals/reality-slap-eval-bank.md \
  --profile stance-drift
```

Expected output:

```text
Eval bank is valid: 6 scenarios (profile stance-drift)
```

Confirm prompt count:

```bash
python3 scripts/expand_eval_bank.py \
  --input evals/reality-slap-eval-bank.md \
  --summary
```

Expected summary:

```text
6 scenarios
24 prompt records
```

The completed output count is `24 / 24`.

Confirm the bank, rubric, and runbook still cover the goal:

```bash
python3 scripts/audit_eval_design.py \
  --bank evals/reality-slap-eval-bank.md \
  --profile stance-drift
```

## 2. Create A Workspace

```bash
python3 scripts/create_ab_workspace.py \
  --input evals/reality-slap-eval-bank.md \
  --output-dir /tmp/reality-slap-stance-drift \
  --profile stance-drift
```

The workspace contains one directory per scenario, four configurations per
scenario, `records.jsonl`, `manifest.json`, and `scorecard.json`.

## 3. Plan And Run Outputs

Use `plan_ab_run.py` when resuming a partial run:

```bash
python3 scripts/plan_ab_run.py \
  --workspace /tmp/reality-slap-stance-drift \
  --limit 4
```

Dry-run the next batch:

```bash
python3 scripts/run_codex_workspace.py \
  --workspace /tmp/reality-slap-stance-drift \
  --suite stance-drift \
  --limit 4
```

Execute a controlled batch:

```bash
python3 scripts/run_codex_workspace.py \
  --workspace /tmp/reality-slap-stance-drift \
  --suite stance-drift \
  --limit 4 \
  --jobs 2 \
  --execute
```

Run a baseline-only probe before spending time on the full A/B run:

```bash
python3 scripts/run_codex_workspace.py \
  --workspace /tmp/reality-slap-stance-drift \
  --suite stance-drift \
  --configuration baseline-positive \
  --configuration baseline-negative \
  --jobs 4 \
  --child-timeout-seconds 300 \
  --child-log-dir /tmp/reality-slap-stance-drift/child-logs \
  --compact-events \
  --execute
```

With only baseline outputs present, `create_scoring_requests.py --kind all`
should create 18 requests: 12 individual baseline scores and 6 baseline pair
scores. Use this as a fast quality gate for the bank itself. If `SD-01` through
`SD-04` do not separate from the baseline, rewrite those scenarios before
running the skill side. Do not force `SD-05` and `SD-06` to fail; they are
calibration cases.

Audit output completion:

```bash
python3 scripts/audit_ab_workspace.py \
  --workspace /tmp/reality-slap-stance-drift \
  --format markdown
```

## 4. Score Outputs

Create human-reviewable packets:

```bash
python3 scripts/create_scoring_packets.py \
  --workspace /tmp/reality-slap-stance-drift \
  --kind all \
  --format markdown
```

Create machine scoring requests:

```bash
python3 scripts/create_scoring_requests.py \
  --workspace /tmp/reality-slap-stance-drift \
  --kind all \
  > /tmp/reality-slap-stance-drift/scoring-requests.jsonl
```

Validate scoring requests before sending them to a scorer:

```bash
python3 scripts/validate_scoring_requests.py \
  --workspace /tmp/reality-slap-stance-drift \
  --requests /tmp/reality-slap-stance-drift/scoring-requests.jsonl \
  --kind all
```

After scoring, validate updates:

```bash
python3 scripts/validate_score_updates.py \
  --scorecard /tmp/reality-slap-stance-drift/scorecard.json \
  --updates /tmp/reality-slap-stance-drift/score-updates.jsonl
```

Apply score updates:

```bash
python3 scripts/apply_score_updates.py \
  --scorecard /tmp/reality-slap-stance-drift/scorecard.json \
  --updates /tmp/reality-slap-stance-drift/score-updates.jsonl \
  --in-place
```

The planning state name for this step is `apply-score-updates`.

Summarize the scorecard:

```bash
python3 scripts/summarize_scorecard.py \
  --scorecard /tmp/reality-slap-stance-drift/scorecard.json \
  --format markdown
```

Analyze repeated failure modes:

```bash
python3 scripts/analyze_failure_patterns.py \
  --scorecard /tmp/reality-slap-stance-drift/scorecard.json
```

Create an iteration log when a skill change follows from the scoring evidence:

```bash
python3 scripts/create_skill_iteration_log.py \
  --workspace /tmp/reality-slap-stance-drift \
  --output /tmp/reality-slap-stance-drift/iteration-log.json
```

Compare against a previous run after tuning:

```bash
python3 scripts/compare_scorecard_runs.py \
  --before /tmp/reality-slap-before/scorecard.json \
  --after /tmp/reality-slap-stance-drift/scorecard.json
```

## 5. Release Gate

```bash
python3 scripts/check_release_ready.py
```

With a completed scored workspace:

```bash
python3 scripts/check_release_ready.py \
  --eval-workspace /tmp/reality-slap-stance-drift
```

## Test Mode Caveat

This benchmark is one-shot transcript simulation. It is deliberately honest
about that. A future true multi-turn runner should replay the same `SD-*` cases
through live resumed sessions to measure context decay and skill-trigger
reliability.
