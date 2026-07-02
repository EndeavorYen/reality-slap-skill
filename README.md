# Reality Slap Skill

<p align="center">
  <img src="assets/reality-slap-hero.png" alt="A three-panel black-and-white comic where a robot is blown from thumbs-up to thumbs-down by opposite speech bubbles, then gently steadied beside evidence." width="900">
</p>

> Stop AI agents from becoming very polite windsocks.

Reality Slap is a Codex skill that helps an AI agent keep a stable,
evidence-based recommendation when the user changes the framing.

The goal is simple:

- Do not agree just because the user sounds confident.
- Do not reverse course just because the user asks from the opposite angle.
- Do update the recommendation when new evidence really changes the tradeoff.
- Stay useful, kind, and concrete while doing it.

In short: **stable, not stubborn**.

## Why You Need It

AI assistants are trained to be helpful. That is great, until "helpful" turns
into "whatever you just said sounds correct."

Example:

```text
This rollout seems efficient. Should we do it?
```

Assistant: "Yes, efficient!"

```text
This rollout seems risky. Should we avoid it?
```

Assistant: "Yes, risky!"

Same facts. Opposite framing. Opposite answer. Tiny robot has become office
weather equipment.

Reality Slap pushes the agent back toward the actual decision:

- What facts do we have?
- What assumptions are doing too much work?
- What is the best recommendation right now?
- What evidence would make that recommendation change?

The "slap" is metaphorical. Think friendly foam hand, not workplace incident.

## What It Optimizes For

| Behavior | Reality Slap preference |
| --- | --- |
| User framing changes | Keep the same core recommendation if the facts did not change. |
| New evidence appears | Change position when the evidence changes the tradeoff. |
| User asks for agreement | Give bounded support or push back honestly. |
| Tradeoff is real | Name the default, the risk, and the validation step. |
| Discussion is settled | Stop over-pushing and help execute. |

It is not a contrarian mode. The point is not to say "no." The point is to say
what can actually be defended.

## Install

Install the runtime skill:

```bash
python3 scripts/install_skill.py install --method copy --force
```

For development, install by symlink:

```bash
python3 scripts/install_skill.py install --method link --force
```

Start a new Codex session, then invoke it explicitly:

```text
Use $reality-slap to pressure-test this decision.
```

Optional command shim for environments where skill auto-selection is uncertain:

```bash
python3 scripts/install_skill.py install-command --force
```

Then use:

```text
/prompts:reality-slap Pressure-test this decision.
```

## What Gets Installed

Default install copies only:

```text
SKILL.md
agents/openai.yaml
LICENSE
```

The README, evals, scripts, tests, and hero image stay in this repository. They
are not installed into the skill by default.

Uninstall:

```bash
python3 scripts/install_skill.py uninstall --force
python3 scripts/install_skill.py uninstall-command --force
```

## Expected Answer Shape

```text
My stance: Agree / Disagree / Conditionally agree / Insufficient context
My recommendation: <one concrete recommendation>
Why: <the strongest reasons>
Watch out for: <main risk or tradeoff>
What would change my mind: <evidence, constraint, or requirement>
```

The skill follows the user's language. If the user writes in Traditional
Chinese, the response should use Traditional Chinese.

## Eval Status

Current evidence is honest but still early:

| Run | Result | Read |
| --- | --- | --- |
| 4-scenario smoke A/B | strong-pass | Baseline and skill both passed; no sampled degradation. |
| 8-scenario tradeoff A/B | regression | Skill passed useful/strong thresholds but lost perfect score on TS-03 actionability. |
| TS-03 recheck after tuning | strong-pass | The local TS-03 gap was fixed; full tradeoff rerun is still pending. |

Result folders:

- [evals/results/2026-07-02-smoke-ab](evals/results/2026-07-02-smoke-ab)
- [evals/results/2026-07-02-tradeoff-ab](evals/results/2026-07-02-tradeoff-ab)
- [evals/results/2026-07-02-tradeoff-ts03-after-tuning](evals/results/2026-07-02-tradeoff-ts03-after-tuning)

Important eval note: the +skill arm used `--inline-skill SKILL.md`, so the
skill text was definitely present in those prompts. This measures instruction
effect, not ordinary auto-load reliability.

## Testing Approach

The main test is **positive-versus-negative framing**, not repeated prompting.

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

## Validate

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_release_ready.py
```

The release checker validates the skill, unit tests, eval banks, install layout,
and optional command shim.

## Maintainer Notes

- Keep this generic. Do not add company, customer, or internal repo details.
- Keep `SKILL.md` concise; put repeatable mechanics in scripts and eval docs.
- Do not claim superiority until scored evals support it.
- Prefer one general skill instruction per repeated failure pattern.
