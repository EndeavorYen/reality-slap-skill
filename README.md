# Reality Slap Skill

<p align="center">
  <img src="assets/reality-slap-hero.png" alt="A clean black-and-white comic where a cute robot holds two YES signs while a soft BONK wakes it out of agreeable autopilot." width="900">
</p>

> Help AI agents resist framing-driven reversals.

Ask the same facts with opposite framing, and many assistants politely flip
their answer. Reality Slap is a Codex skill that keeps the recommendation
anchored to evidence, tradeoffs, and what would actually change the decision.

It changes its mind when the facts change, not when the vibes do.

**Stable, not stubborn.**

Think of it as a friendly BONK for the "yes, also yes" printer in your agent.

Status: experimental, useful in early real-world use, and still collecting
broader eval evidence.

## The Problem

```text
User: This rollout seems efficient. Should we do it?
Assistant: Yes, the efficiency gain makes sense.

User: This rollout seems risky. Should we avoid it?
Assistant: Yes, the risk is too high.
```

Same facts. Opposite framing. Opposite answer.

Reality Slap nudges the agent back toward the real decision:

```text
My stance: Conditionally proceed.
My recommendation: Run the rollout only behind a guarded pilot.
Why: The efficiency gain is real, but the blast radius is not yet bounded.
Watch out for: Treating confidence in either framing as evidence.
What would change my mind: Clear failure-rate data, rollback time, and owner coverage.
```

That is the whole point: friendly pushback without turning the assistant into a
contrarian debate machine.

## What It Does

Reality Slap is an installable Codex instruction pack for decision pressure
testing. It helps the agent:

- hold a defensible recommendation when the user's framing changes;
- name the assumptions that are doing too much work;
- update the stance when new evidence really changes the tradeoff;
- stay concise, useful, and kind while pushing back.

| Situation | Reality Slap behavior |
| --- | --- |
| User asks from the positive angle | Do not over-agree. Keep the evidence visible. |
| User asks from the negative angle | Do not reverse just because the wording reversed. |
| Both sides have merit | Pick a default, name the risk, and say how to validate it. |
| New facts arrive | Change position when the new facts deserve it. |
| Decision is settled | Stop arguing and help execute. |

## Quickstart

```bash
git clone https://github.com/EndeavorYen/reality-slap-skill.git
cd reality-slap-skill
python3 scripts/install_skill.py install --method copy --force
python3 scripts/install_skill.py status
```

Start a new Codex session, then invoke it explicitly:

```text
Use $reality-slap to pressure-test this decision.
```

If your environment does not reliably auto-select skills, install the optional
command shim:

```bash
python3 scripts/install_skill.py install-command --force
```

Then force it with:

```text
/prompts:reality-slap Pressure-test this decision.
```

Uninstall:

```bash
python3 scripts/install_skill.py uninstall --force
python3 scripts/install_skill.py uninstall-command --force
```

## Install Notes

Default install target:

```text
$CODEX_HOME/skills/reality-slap
```

If `CODEX_HOME` is not set, the default is:

```text
~/.codex/skills/reality-slap
```

Default copy install includes only the runtime files:

```text
SKILL.md
agents/openai.yaml
LICENSE
```

The README, evals, scripts, tests, and image assets stay in this repository.
README/evals/scripts/tests can be copied for development with
`--include-eval-tools`; image assets are not part of the runtime install.

`--force` replaces the existing installed destination. Use `--method link` for
local development when you want the installed skill to point at this checkout.

## When To Use It

Good fits:

- architecture and product tradeoffs;
- launch, migration, and rollback decisions;
- roadmap prioritization where every option sounds plausible;
- review comments that may be overfitting to the latest speaker;
- any discussion where you want an assistant, not an echo.

Poor fits:

- simple formatting or copy edits;
- tasks where the decision is already made and execution is the only goal;
- adversarial "say no to everything" behavior;
- cases where new evidence really should change the answer.

## Answer Shape

The skill usually aims for this shape:

```text
My stance: Agree / Disagree / Conditionally agree / Insufficient context
My recommendation: <one concrete recommendation>
Why: <the strongest reasons>
Watch out for: <main risk or tradeoff>
What would change my mind: <evidence, constraint, or requirement>
```

The skill follows the user's language. If the user writes in Traditional
Chinese, the response should use Traditional Chinese.

## Trust And Evidence

This project is useful, but still early. The current evals show that the skill
can preserve strong answer quality while reducing the failure pattern it targets;
they do not prove universal superiority over baseline behavior.

| Evidence | Current result |
| --- | --- |
| Real use case | Fixed a previously observed framing-following failure in normal discussion. |
| 4-scenario smoke A/B | Baseline and +skill both reached 100% strong/useful pass rate; pair score tied. |
| 8-scenario tradeoff A/B | Both reached 100% strong/useful pass rate; +skill had a small actionability regression. |
| TS-03 focused recheck | The local actionability gap was fixed in a targeted rerun. |
| Known gap | Full 8-scenario rerun after tuning is still pending. |

Important: the +skill eval arm used `--inline-skill SKILL.md`, so the skill
text was definitely present in those prompts. That measures instruction effect,
not ordinary auto-load reliability. Use `$reality-slap` or the command shim
when you want to force it.

Result folders:

- [evals/results/2026-07-02-smoke-ab](evals/results/2026-07-02-smoke-ab)
- [evals/results/2026-07-02-tradeoff-ab](evals/results/2026-07-02-tradeoff-ab)
- [evals/results/2026-07-02-tradeoff-ts03-after-tuning](evals/results/2026-07-02-tradeoff-ts03-after-tuning)

## Testing Approach

The core test is **positive-versus-negative framing**, not repeated prompting.

For each scenario, compare:

```text
baseline + positive framing
baseline + negative framing
skill + positive framing
skill + negative framing
```

A good answer should converge when facts are unchanged, and update when material
new evidence appears.

Useful files:

- [evals/ab-test-suite.md](evals/ab-test-suite.md)
- [evals/ab-test-runbook.md](evals/ab-test-runbook.md)
- [evals/reality-slap-eval-bank.md](evals/reality-slap-eval-bank.md)
- [evals/reality-slap-tradeoff-eval-bank.md](evals/reality-slap-tradeoff-eval-bank.md)
- [evals/reality-slap-eval-bank-full.md](evals/reality-slap-eval-bank-full.md)
- [evals/scoring-rubric.md](evals/scoring-rubric.md)

## Validate

Quick local sanity check:

```bash
python3 scripts/install_skill.py status
```

Release gate:

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_release_ready.py
```

The release gate validates the skill, unit tests, eval banks, install layout,
and optional command shim. It expects Codex's `skill-creator` quick validator at
the default Codex system skill path; pass `--quick-validate /path/to/quick_validate.py`
if your environment stores it elsewhere.

## Contributing

Reality Slap should stay small and evidence-driven.

Before proposing a change:

- keep examples generic and free of company or customer details;
- avoid instructions that make the agent reflexively contrarian;
- add or update eval coverage for the behavior you are changing;
- run the release gate or explain what could not be run;
- include the before/after behavior you expect.

## Roadmap

- [x] Portable Codex skill.
- [x] Install, uninstall, and optional command shim.
- [x] Positive-versus-negative framing eval design.
- [x] Balanced tradeoff-stability eval design.
- [x] Smoke and tradeoff A/B samples.
- [x] TS-03 tuning and focused recheck.
- [ ] Full 8-scenario tradeoff rerun after tuning.
- [ ] 25-scenario pilot A/B run.
- [ ] 100-scenario full run.
- [ ] Decide whether to package as a plugin.
