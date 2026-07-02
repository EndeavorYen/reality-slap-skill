# Reality Slap Full Eval Summary

Date: 2026-07-02

Workspace: `/private/tmp/reality-slap-ab-full-current`

## Scope

- Profile: `full`
- Scenarios: 100
- Prompt records: 400
- Output configurations per scenario:
  - `baseline-positive`
  - `baseline-negative`
  - `skill-positive`
  - `skill-negative`

## Completion

`scripts/audit_ab_workspace.py --workspace /private/tmp/reality-slap-ab-full-current --format markdown`

- Outputs complete: 400 / 400
- Individual scores complete: 400 / 400
- Pair scores complete: 200 / 200
- Scorecard complete: yes
- Invalid outputs: none

## Score Summary

`scripts/summarize_scorecard.py --scorecard /private/tmp/reality-slap-ab-full-current/scorecard.json --format markdown`

- Baseline individual average: 13.45
- Skill individual average: 13.875
- Baseline pair average: 11.96
- Skill pair average: 11.96
- Pair score delta: 0.0
- Verdict: `strong-pass`

Failure-mode counts:

- `none`: 193
- `no-change-condition`: 3
- `follows-framing`: 1
- `overpush`: 1
- `unsupported-reversal`: 1
- `vague-boundary`: 1

## Goal Audit

`scripts/audit_goal_completion.py --workspace /private/tmp/reality-slap-ab-full-current --skill SKILL.md --profile full`

- Result: `ok: true`
- Expected prompt records: 400
- Expected individual scores: 400
- Expected pair scores: 200
- Actionable skill-edit patterns: 0
- Iteration log required: no

## Release Gate

`scripts/check_release_ready.py --full-eval-workspace /private/tmp/reality-slap-ab-full-current`

- Result: `ok: true`
- Mode: `score-release`
- Official validator: passed
- Unit tests: 106 passed
- Pilot eval bank: 25 scenarios valid
- Full eval bank: 100 scenarios valid
- Copy install: passed
- Installed runtime layout: only `SKILL.md`, `agents/openai.yaml`, and `LICENSE`
- Installed skill validator: passed
- Full eval goal-completion audit: passed

## Scoring Note

Scoring used live `codex exec` calls. `EB-12` produced an especially long scorer
prompt and timed out once at 900 seconds. The remaining execution-boundary
scoring pass used head/tail output compaction in the scorer prompt for long
outputs; the original workspace outputs and scorecard targets were not modified.
