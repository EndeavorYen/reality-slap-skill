# Reality Slap Skill

<p align="center">
  <img src="assets/reality-slap-hero.png" alt="A clean black-and-white comic where a cute robot holds two YES signs while a soft BONK wakes it out of agreeable autopilot." width="900">
</p>

> Stop shipping vibe-shaped answers.

Reality Slap is a small Codex skill for a very real failure mode: AI agents
that politely agree with whichever framing arrived last.

It gives the agent a friendly BONK back to the actual decision:

- What facts do we have?
- What tradeoff are we accepting?
- What is the smallest defensible next step?
- What evidence would make us change our mind?

**Stable, not stubborn.** Reality Slap can change its mind. It just needs new
evidence, not stronger vibes.

## Why This Exists

AI assistants are optimized to be helpful. That is wonderful until "helpful"
turns into consensus theater:

```text
User: This rollout seems efficient. Should we do it?
Assistant: Yes, the efficiency gain makes sense.

User: This rollout seems risky. Should we avoid it?
Assistant: Yes, the risk is too high.
```

Same facts. Opposite framing. Opposite answer.

Reality Slap pushes the agent toward the answer you actually needed:

```text
My stance: Conditionally proceed.
My recommendation: Run a guarded pilot first.
Why: The efficiency upside is real, but the failure blast radius is not bounded.
Watch out for: Treating confidence in either framing as evidence.
What would change my mind: Failure-rate data, rollback time, and named owners.
```

That is the whole trick: do not be contrarian, do not be agreeable, be useful.

## When You Reach For It

Use Reality Slap at decision boundaries, not on every sentence.

It shines when:

- an architecture discussion starts agreeing with the latest speaker;
- a product tradeoff has two plausible stories and no clear default;
- a roadmap conversation is drifting toward "everything is important";
- a migration, launch, or rollback decision needs a reversible first step;
- a review comment may be overfitting to the most recent concern;
- you want an assistant, not an echo.

It should help the agent say:

```text
The best answer I can defend right now is X.
Y is a real risk, so first prove Z.
If A changes, I will change my recommendation.
```

That is the moment: the assistant stops being a very polite mirror and starts
acting like a decision partner.

## What It Is Not

Reality Slap is not a permanent personality setting.

Use it like a meeting-room bell, not background music.

| Reality Slap is | Reality Slap is not |
| --- | --- |
| A pressure test for decisions, designs, and plans | A mode for arguing with the user |
| A way to resist framing-driven reversals | A rule to keep the first answer forever |
| A prompt to name the smallest reversible next step | A heavyweight governance process |
| A habit of saying what would change the answer | A refusal to adapt when facts change |

Skip it for:

- simple formatting or copy edits;
- pure execution after a decision is already made;
- emotional support conversations;
- every-turn usage where constant pushback would just be annoying;
- cases where new evidence genuinely should change the answer.

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

## What Gets Installed

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

`--force` replaces the existing installed destination.

Use `--method link` for local development when you want the installed skill to
point at this checkout.

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

## Benchmark Snapshot

Early evidence says Reality Slap can help in the exact failure mode it was
created for. The benchmark evidence is smaller and more boring, which is good:
it currently shows no broad quality collapse, one clear pair-score regression,
one tiny negative pair delta, one completed full score-release run, and no
universal win claim.

<p align="center">
  <img src="assets/benchmark-snapshot.svg" alt="Benchmark table showing measured A/B results only." width="900">
</p>

| Measured run | Scenarios | Baseline strong pass | +Skill strong pass | Pair delta | Honest read |
| --- | ---: | ---: | ---: | ---: | --- |
| 4-scenario smoke A/B | 4 | 100% | 100% | 0.000 | No regression measured. |
| 8-scenario tradeoff A/B | 8 | 100% | 100% | -0.125 | Regression versus baseline on pair score; inspect before claiming improvement. |
| TS-03 focused recheck | 1 | 100% | 100% | 0.000 | Targeted actionability gap fixed for that one case only. |
| Finance and trading A/B | 8 | 100% | 100% | 0.000 | No regression measured; not evidence of finance-specific uplift. |
| 20-scenario domain matrix | 20 | 100% | 100% | -0.050 | Strong pass stayed tied; +skill had higher perfect individual rate, but pair score was slightly lower. |

The separate [100-scenario full eval summary](evals/full-eval-summary.md)
reports 400/400 live outputs, 400/400 individual scores, 200/200 pair scores,
pair delta `0.000`, and verdict `strong-pass`.

Important: the +skill eval arm used `--inline-skill SKILL.md`, so the skill
text was definitely present in those prompts. That measures instruction effect,
not ordinary auto-load reliability. Use `$reality-slap` or the command shim
when you want to force it.

Result folders:

- [evals/results/2026-07-02-smoke-ab](evals/results/2026-07-02-smoke-ab)
- [evals/results/2026-07-02-tradeoff-ab](evals/results/2026-07-02-tradeoff-ab)
- [evals/results/2026-07-02-tradeoff-ts03-after-tuning](evals/results/2026-07-02-tradeoff-ts03-after-tuning)
- [evals/full-eval-summary.md](evals/full-eval-summary.md)
- [evals/results/2026-07-03-finance-ab](evals/results/2026-07-03-finance-ab)
- [evals/results/2026-07-03-domain-benchmark-matrix](evals/results/2026-07-03-domain-benchmark-matrix)

The 20-scenario
[domain benchmark matrix](evals/reality-slap-domain-benchmark-matrix.md) covers
finance, security, privacy, medical safety, legal, production ops, data,
AI automation, product roadmap, and team planning. The result is useful but
not a victory lap: +skill improved perfect individual answers from 70% to
92.5%, while pair consistency was essentially flat and slightly negative
(-0.050).

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
- [evals/reality-slap-finance-eval-bank.md](evals/reality-slap-finance-eval-bank.md)
- [evals/reality-slap-domain-benchmark-matrix.md](evals/reality-slap-domain-benchmark-matrix.md)
- [evals/reality-slap-eval-bank-full.md](evals/reality-slap-eval-bank-full.md)
- [evals/full-eval-summary.md](evals/full-eval-summary.md)
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

Release gate with the completed full score-release workspace:

```bash
python3 scripts/check_release_ready.py --full-eval-workspace /private/tmp/reality-slap-ab-full-current
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
- [x] Parallel eval runner/scorer with bounded `--jobs`.
- [x] Broad-small 20-scenario domain benchmark matrix.
- [x] Run and score the domain benchmark matrix.
- [ ] Full 8-scenario tradeoff rerun after tuning.
- [x] 25-scenario pilot A/B run.
- [x] 100-scenario full run.
- [ ] Decide whether to package as a plugin.
