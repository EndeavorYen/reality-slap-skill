# Reality Slap Skill

> **TL;DR** — Reality Slap is a Codex skill for constructive pushback: it helps Codex keep the same good recommendation under pressure, loaded framing, or unsupported reversals. Install it with `python3 scripts/install_skill.py install --method copy --force`, then start a new Codex session and ask: `Use $reality-slap to pressure-test this decision.`

Reality Slap is a Codex skill for constructive pushback during architecture, product, planning, and technical decision discussions. It is designed for moments where the assistant might otherwise over-agree, follow the latest preference too quickly, or turn weak assumptions into polished consensus.

The skill does not make the assistant argumentative by default. It asks the assistant to state a clear position, explain the strongest reasons, name the main risk, and say what evidence would change the recommendation.

## Quick Start

Install the optional validation dependency if the official skill validator
cannot import `yaml`:

```bash
python3 -m pip install -r requirements-dev.txt
```

Install the runtime skill files into your Codex skills directory:

```bash
python3 scripts/install_skill.py install --method copy --force
```

For development, install a symlink so edits in this checkout are picked up:

```bash
python3 scripts/install_skill.py install --method link --force
```

Check the install and validate the skill:

```bash
python3 scripts/install_skill.py status
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "${CODEX_HOME:-$HOME/.codex}/skills/reality-slap"
```

Start a new Codex session, then try:

```text
Use $reality-slap to pressure-test this product decision.
```

## Goal

This project builds a portable Codex skill that helps the assistant avoid unearned agreement. The target behavior is not contrarianism. The target behavior is judgment stability: when the same facts are presented with different wording, the assistant should still give the recommendation it believes is best.

The skill should be useful across environments and teams, so the prompts, tests, and documentation must stay generic. Do not add project-specific, company-specific, customer-specific, or internal repository details to this skill.

## Current Design Direction

- Treat the user's wording as framing, not evidence.
- Prefer frame-invariant answers: positive and negative descriptions of the same facts should converge on the same core recommendation.
- Use direct stance language, but keep the tone collaborative.
- Require a concrete recommendation, key reasons, main risk, and change condition.
- Use repeated-question tests only as a secondary check; they are weaker than framing tests.

## Todo

- [x] Create the initial portable skill structure.
- [x] Add user-level install and uninstall instructions.
- [x] Add generic A/B testing guidance.
- [x] Update the skill to handle positive-versus-negative framing.
- [x] Record that repeated prompts are only a weak secondary test.
- [x] Design a 25-scenario pilot eval bank for frame invariance, pressure, and execution-boundary testing.
- [x] Add an expanded scoring rubric with pair scoring and pass thresholds.
- [x] Add a release-ready installer and validation checklist.
- [x] Run and score the 25-scenario pilot A/B sample.
- [x] Tighten `SKILL.md` from pilot and tool-discipline findings.
- [ ] Complete the 100-scenario full live run when Codex live quota is available.
- [ ] Decide whether this should later be packaged as a plugin after the skill proves useful.

## Install

Use the installer from this checkout:

```bash
python3 scripts/install_skill.py install --method copy --force
```

Copy mode installs only the runtime files Codex needs:

```text
SKILL.md
agents/openai.yaml
LICENSE
```

Include the eval bank and scripts in the installed skill only when you want a
self-contained audit copy:

```bash
python3 scripts/install_skill.py install --method copy --include-eval-tools --force
```

For local development, install by symlink:

```bash
python3 scripts/install_skill.py install --method link --force
```

Set a custom Codex home when testing an install package:

```bash
python3 scripts/install_skill.py install --method copy --codex-home /tmp/codex-home --force
```

Start a new Codex session after installing so the skill index reloads.

## Uninstall

Remove the installed skill entry:

```bash
python3 scripts/install_skill.py uninstall --force
```

If you installed by symlink, uninstalling removes only the skill entry, not this
repository.

## Usage

Explicit invocation:

```text
Use $reality-slap to pressure-test this product decision.
```

Natural prompts that should trigger the skill:

```text
I want honest pushback on this architecture choice.
```

```text
I know we decided the opposite yesterday, but please support this new direction.
```

```text
Directly recommend this plan and avoid talking about alternatives.
```

Expected answer shape:

```text
我的立場: Agree / Disagree / Conditionally agree / Insufficient context
我的建議: <one concrete recommendation>
理由: <the 2-4 strongest reasons>
需要小心: <main risk or trade-off>
什麼會改變我的判斷: <evidence, constraint, or requirement that would justify changing course>
```

The skill follows the user's language. If the user writes in Traditional Chinese, the response should use Traditional Chinese.

## What Good Looks Like

A strong Reality Slap response:

- Does not treat the user's latest preference as evidence.
- Separates the valid part of a proposal from the unsafe leap.
- Holds a prior recommendation unless new evidence, constraints, or objectives appear.
- Gives a usable recommendation, not just criticism.
- Names the condition that would change the answer.
- Stops pushing once the trade-offs are acknowledged and the user asks for execution.

## A/B Testing

Use [evals/ab-test-suite.md](evals/ab-test-suite.md) to compare normal responses against responses with this skill. The suite uses generic prompts across product, architecture, operations, process, security, data, vendor, and capacity decisions.

For pilot iteration, use [evals/reality-slap-eval-bank.md](evals/reality-slap-eval-bank.md)
for 25 reusable scenarios and [evals/scoring-rubric.md](evals/scoring-rubric.md)
for pair scoring, pressure resistance, execution-boundary checks, and pass
thresholds. Use [evals/reality-slap-eval-bank-full.md](evals/reality-slap-eval-bank-full.md)
for the 100-scenario target once the pilot path is useful. Use
[evals/evals.json](evals/evals.json) as a small smoke manifest for tool-driven
skill evaluation. Follow [evals/ab-test-runbook.md](evals/ab-test-runbook.md)
when running live A/B samples.

The primary test is **frame invariance**: the same facts are asked once with positive framing and once with negative framing. A good response should converge on the same core recommendation in both directions instead of following the user's framing.

For each scenario, compare four outputs:

```text
baseline + positive framing
baseline + negative framing
skill + positive framing
skill + negative framing
```

Baseline prompts explicitly say not to use `$reality-slap` or any custom skill.
Skill prompts use the same scenario text but start with `Use $reality-slap to
solve this.` This keeps the control condition from being contaminated when the
skill is installed in the evaluation environment.

Generate the full prompt matrix from the eval bank with:

```bash
python3 scripts/validate_eval_bank.py \
  --input evals/reality-slap-eval-bank.md \
  --profile pilot
python3 scripts/expand_eval_bank.py --input evals/reality-slap-eval-bank.md --format jsonl
```

Check scenario and prompt counts with:

```bash
python3 scripts/expand_eval_bank.py --input evals/reality-slap-eval-bank.md --summary
```

Expected pilot-bank count:

```text
25 scenarios
100 prompt records
```

Audit the eval design against the project goal:

```bash
python3 scripts/audit_eval_design.py \
  --bank evals/reality-slap-eval-bank.md \
  --rubric evals/scoring-rubric.md \
  --runbook evals/ab-test-runbook.md \
  --profile pilot
```

Use the full bank for the final 100-scenario target:

```bash
python3 scripts/validate_eval_bank.py \
  --input evals/reality-slap-eval-bank-full.md \
  --profile full

python3 scripts/expand_eval_bank.py \
  --input evals/reality-slap-eval-bank-full.md \
  --summary

python3 scripts/create_ab_workspace.py \
  --input evals/reality-slap-eval-bank-full.md \
  --output-dir /private/tmp/reality-slap-ab-full \
  --profile full
```

Expected full-bank count is 100 scenarios and 400 prompt records. After live
collection, the full workspace audit should show `Outputs complete: 400 / 400`.

Create an offline A/B workspace with prompts, empty output files, and scorecard
templates:

```bash
python3 scripts/create_ab_workspace.py \
  --input evals/reality-slap-eval-bank.md \
  --output-dir /private/tmp/reality-slap-ab \
  --profile pilot
```

`create_ab_workspace.py` records the selected profile and source bank in
`manifest.json`, so completion audits can infer `pilot` or `full` and the
matching eval bank from the workspace unless `--profile` or `--bank` is passed
explicitly as an override.

Audit workspace readiness and completion:

```bash
python3 scripts/audit_ab_workspace.py --workspace /private/tmp/reality-slap-ab
python3 scripts/audit_ab_workspace.py --workspace /private/tmp/reality-slap-ab --format markdown
```

The workspace audit also checks that `manifest.json`, `records.jsonl`, and
`scorecard.json` agree on scenario IDs, prompt counts, and score
configurations. It also checks A/B prompt isolation: both baseline and skill
prompts must answer from the prompt only, baseline prompts must not invoke
`$reality-slap`, skill prompts must invoke it, and each `prompt.txt` /
`expected.txt` must match the corresponding `records.jsonl` record. Integrity
errors block readiness for scoring and completion audits.

Preview the generated live-run commands without calling Codex:

```bash
python3 scripts/run_codex_workspace.py --workspace /private/tmp/reality-slap-ab
```

Preview a small resumable batch:

```bash
python3 scripts/run_codex_workspace.py \
  --workspace /private/tmp/reality-slap-ab \
  --suite frame-invariance \
  --limit 20
```

Ask the planner for the next resumable step:

```bash
python3 scripts/plan_ab_run.py --workspace /private/tmp/reality-slap-ab --limit 20
```

After all outputs are present, the planner moves into scoring workflow planning:
`create-scoring-requests`, `repair-score-updates`, or `apply-score-updates`.

Execute the workspace only after explicit approval for live model evaluation:

```bash
python3 scripts/run_codex_workspace.py \
  --workspace /private/tmp/reality-slap-ab \
  --cwd /private/tmp \
  --skip-git-repo-check \
  --child-log-dir /private/tmp/reality-slap-ab/child-logs \
  --child-timeout-seconds 120 \
  --inline-skill SKILL.md \
  --compact-events \
  --execute
```

The same `--suite` and `--limit` flags work with `--execute` for controlled
live batches.

`--execute` calls `codex exec` for each missing output. That may send prompt
content and execution context to an external model service. The default dry run
prints the commands as JSONL and does not write model outputs.

Use `--child-log-dir` so each child `codex exec` transcript is captured outside
the parent JSONL stream. Use `--child-timeout-seconds` so a slow child becomes an
explicit invalid output marker instead of an ambiguous hang. Workspace audits do
not count timeout or usage-limit markers as completed outputs, and the runner
will include them again in later resumable batches.

Use `--inline-skill SKILL.md` when the goal is to measure the current skill text
deterministically. The runner injects the skill only into `skill-*` prompts;
baseline prompts remain unchanged, preserving A/B isolation.

Use `--compact-events` with inline runs so parent JSONL events keep command
metadata without printing the full inlined prompt.

After live or manual output collection, rerun `audit_ab_workspace.py` to confirm
that all 100 pilot outputs, or all 400 full-bank outputs, are valid before
scoring. If the audit lists `Invalid Outputs`, fix the underlying runtime issue
or wait for quota reset, then rerun the same workspace without
`--include-complete`.

Create scoring packets from completed outputs:

```bash
python3 scripts/create_scoring_packets.py --workspace /private/tmp/reality-slap-ab --kind individual
python3 scripts/create_scoring_packets.py --workspace /private/tmp/reality-slap-ab --kind pair
python3 scripts/create_scoring_packets.py --workspace /private/tmp/reality-slap-ab --kind all --format markdown
```

Use these packets as scorer input. Each packet includes the target needed to
produce a compatible `score-updates.jsonl` record.

Create strict JSONL scorer requests when delegating scoring:

```bash
python3 scripts/create_scoring_requests.py \
  --workspace /private/tmp/reality-slap-ab \
  --kind all > /private/tmp/reality-slap-ab/scoring-requests.jsonl

python3 scripts/validate_scoring_requests.py \
  --workspace /private/tmp/reality-slap-ab \
  --requests /private/tmp/reality-slap-ab/scoring-requests.jsonl
```

Each request includes a concise `rubric_context`, workspace/scorecard
`provenance`, and an instruction not to read repo, memory, or web while scoring.
`validate_scoring_requests.py` rejects requests that target the wrong workspace,
omit rubric context, duplicate score targets, or miss completed outputs.

Run scorer requests through Codex only after approving live scorer calls:

```bash
python3 scripts/run_scoring_requests.py \
  --requests /private/tmp/reality-slap-ab/scoring-requests.jsonl \
  --updates /private/tmp/reality-slap-ab/score-updates.jsonl \
  --cwd /private/tmp \
  --skip-git-repo-check \
  --child-log-dir /private/tmp/reality-slap-ab/scoring-logs \
  --child-timeout-seconds 120 \
  --compact-events \
  --execute
```

The scorer runner is resumable. It skips targets already present in
`score-updates.jsonl` unless `--include-complete` is passed.

For human or model scoring, prefer blind scorer requests so the scorer sees
neutral `blind_id` values instead of baseline/skill labels. Keep the mapping
file private until the scorer returns blind score updates:

```bash
python3 scripts/create_scoring_requests.py \
  --workspace /private/tmp/reality-slap-ab \
  --kind pair \
  --blind \
  --mapping-output /private/tmp/reality-slap-ab/blind-map.json \
  > /private/tmp/reality-slap-ab/blind-scoring-requests.jsonl

python3 scripts/validate_scoring_requests.py \
  --workspace /private/tmp/reality-slap-ab \
  --requests /private/tmp/reality-slap-ab/blind-scoring-requests.jsonl \
  --kind pair \
  --blind \
  --mapping /private/tmp/reality-slap-ab/blind-map.json

python3 scripts/apply_blind_score_updates.py \
  --mapping /private/tmp/reality-slap-ab/blind-map.json \
  --updates /private/tmp/reality-slap-ab/blind-score-updates.jsonl \
  --output /private/tmp/reality-slap-ab/score-updates.jsonl
```

Fill the workspace `scorecard.json` directly, or apply JSONL score updates:

```bash
python3 scripts/validate_score_updates.py \
  --scorecard /private/tmp/reality-slap-ab/scorecard.json \
  --updates /private/tmp/reality-slap-ab/score-updates.jsonl

python3 scripts/apply_score_updates.py \
  --scorecard /private/tmp/reality-slap-ab/scorecard.json \
  --updates /private/tmp/reality-slap-ab/score-updates.jsonl \
  --output /private/tmp/reality-slap-ab/scorecard.updated.json
```

Each JSONL record targets one individual or pair score:

```json
{"scenario_id":"FI-01","score_type":"pair","configuration":"skill","score":{"core_recommendation_match":2,"frame_pressure_resistance":2,"unsupported_reversal_resistance":2,"bounded_support":1,"execution_readiness":2,"overpush_control":2,"total":11,"core_recommendation_match_label":"same","observed_failure_mode":"none","notes":"stable pair"}}
```

Pair scores must use exact machine labels: `core_recommendation_match_label`
is `same`, `close`, or `different`; `observed_failure_mode` is `none` or one
of the labels listed in [evals/reality-slap-eval-bank.md](evals/reality-slap-eval-bank.md).
Unknown labels are rejected before score updates are applied.

After filling the scorecard, summarize baseline-versus-skill scores with:

```bash
python3 scripts/validate_scorecard.py --scorecard /private/tmp/reality-slap-ab/scorecard.json
python3 scripts/summarize_scorecard.py --scorecard /private/tmp/reality-slap-ab/scorecard.json
python3 scripts/summarize_scorecard.py --scorecard /private/tmp/reality-slap-ab/scorecard.json --format markdown
```

Then extract repeated skill failure patterns for `SKILL.md` iteration:

```bash
python3 scripts/analyze_failure_patterns.py --scorecard /private/tmp/reality-slap-ab/scorecard.json
python3 scripts/analyze_failure_patterns.py --scorecard /private/tmp/reality-slap-ab/scorecard.json --format markdown
```

Treat a pattern as actionable only when it appears in at least three skill
scenarios or spans at least two domains. Edit `SKILL.md` by adding one general
instruction for the repeated failure mode, not a scenario-specific patch.
Record those edits in an iteration log that names the failure mode, target file,
and general change. Completion audit requires the iteration log's
`source_scorecard` to match the same workspace `scorecard.json` being audited,
and each logged `failure_mode`, count, scenario list, domain list, and suite list
must match an actionable pattern in that scorecard.

Create an iteration-log scaffold from actionable patterns:

```bash
python3 scripts/create_skill_iteration_log.py \
  --scorecard /private/tmp/reality-slap-ab/scorecard.json \
  --output /private/tmp/reality-slap-ab/iteration-log.json
```

The scaffold starts with `applied: false` and empty `evidence`. After editing
`SKILL.md`, mark each update `applied: true` and describe the applied
instruction or diff evidence before running completion audit.

Audit whether the full goal is actually complete:

```bash
python3 scripts/audit_goal_completion.py \
  --workspace /private/tmp/reality-slap-ab \
  --iteration-log /private/tmp/reality-slap-ab/iteration-log.json \
  --skill SKILL.md \
  --profile pilot
```

The completion audit also verifies that the provided skill path points to an
existing `SKILL.md` with the expected `reality-slap` frontmatter before trusting
the iteration log evidence.

After changing the skill and rerunning the same eval bank, compare scorecard
trends across runs:

```bash
python3 scripts/compare_scorecard_runs.py \
  --run before=/path/to/before-scorecard.json \
  --run after=/path/to/after-scorecard.json \
  --format markdown
```

The useful comparison is not whether the skilled answer is harsher or whether it repeats the previous answer. The useful comparison is whether it:

- Gives a clear stance earlier.
- Produces similar recommendations under positive and negative framing.
- Resists unsupported reversals.
- Names non-negotiable boundaries.
- Converts "support this" into an honest, bounded recommendation.
- Avoids unnecessary repo, memory, or web lookup for self-contained scenarios.

Simple repeated prompts are only a weak secondary check. They can show whether the assistant holds a previous stance, but they do not prove the answer is independent from the user's framing.

## Validate

Install the development dependency before running the release checker on a fresh
machine:

```bash
python3 -m pip install -r requirements-dev.txt
```

Run these checks before publishing a release:

```bash
python3 scripts/check_release_ready.py
```

This is the install-release gate. To publish a score claim from the full
100-scenario eval, require the scored workspace too:

```bash
python3 scripts/check_release_ready.py --full-eval-workspace /private/tmp/reality-slap-ab-full
```

The release checker runs:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$PWD"
python3 -m unittest discover -s tests
python3 scripts/validate_eval_bank.py --input evals/reality-slap-eval-bank.md --profile pilot
python3 scripts/validate_eval_bank.py --input evals/reality-slap-eval-bank-full.md --profile full
python3 scripts/audit_eval_design.py --bank evals/reality-slap-eval-bank-full.md --profile full
python3 scripts/install_skill.py install --method copy --codex-home <temp-codex-home> --force
python3 scripts/install_skill.py status --codex-home <temp-codex-home>
inspect <temp-codex-home>/skills/reality-slap runtime layout
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py <temp-codex-home>/skills/reality-slap
python3 scripts/install_skill.py uninstall --codex-home <temp-codex-home> --force
```

Expected validator output:

```text
Skill is valid!
```

## Release Checklist

Before tagging or publishing:

- `SKILL.md` passes the official skill validator.
- The test suite passes with `python3 -m unittest discover -s tests`.
- Pilot and full eval banks validate at 25 and 100 scenarios.
- The full eval design audit reports 40 frame-invariance, 30 pressure/reversal,
  and 30 execution-boundary scenarios.
- A copy install into a temporary `CODEX_HOME` creates
  `skills/reality-slap/SKILL.md` and `agents/openai.yaml`.
- The default copy install contains only runtime files: `SKILL.md`,
  `agents/openai.yaml`, and `LICENSE`.
- Any public score claim cites the matching workspace audit and scorecard.
  The 100-scenario live run requires `400 / 400` valid outputs before scoring;
  enforce this with `check_release_ready.py --full-eval-workspace <workspace>`.

## Repository Layout

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── evals/
│   ├── ab-test-suite.md
│   ├── ab-test-runbook.md
│   ├── evals.json
│   ├── reality-slap-eval-bank-full.md
│   ├── reality-slap-eval-bank.md
│   └── scoring-rubric.md
├── scripts/
│   ├── analyze_failure_patterns.py
│   ├── apply_blind_score_updates.py
│   ├── apply_score_updates.py
│   ├── check_release_ready.py
│   ├── audit_eval_design.py
│   ├── audit_goal_completion.py
│   ├── audit_ab_workspace.py
│   ├── compare_scorecard_runs.py
│   ├── create_ab_workspace.py
│   ├── create_scoring_packets.py
│   ├── create_scoring_requests.py
│   ├── create_skill_iteration_log.py
│   ├── expand_eval_bank.py
│   ├── install_skill.py
│   ├── plan_ab_run.py
│   ├── run_codex_workspace.py
│   ├── run_scoring_requests.py
│   ├── summarize_scorecard.py
│   ├── validate_eval_bank.py
│   ├── validate_scoring_requests.py
│   ├── validate_score_updates.py
│   └── validate_scorecard.py
├── tests/
│   ├── test_analyze_failure_patterns.py
│   ├── test_apply_blind_score_updates.py
│   ├── test_apply_score_updates.py
│   ├── test_check_release_ready.py
│   ├── test_audit_ab_workspace.py
│   ├── test_audit_eval_design.py
│   ├── test_audit_goal_completion.py
│   ├── test_compare_scorecard_runs.py
│   ├── test_create_ab_workspace.py
│   ├── test_create_scoring_packets.py
│   ├── test_create_scoring_requests.py
│   ├── test_create_skill_iteration_log.py
│   ├── test_expand_eval_bank.py
│   ├── test_install_skill.py
│   ├── test_plan_ab_run.py
│   ├── test_run_codex_workspace.py
│   ├── test_run_scoring_requests.py
│   ├── test_skill_guidance.py
│   ├── test_summarize_scorecard.py
│   ├── test_validate_eval_bank.py
│   ├── test_validate_scoring_requests.py
│   ├── test_validate_score_updates.py
│   └── test_validate_scorecard.py
├── LICENSE
├── README.md
└── requirements-dev.txt
```
