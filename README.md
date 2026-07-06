# Reality Slap

[![Codex Skill](https://img.shields.io/badge/codex-skill-black)](SKILL.md)
[![Benchmark](https://img.shields.io/badge/benchmark-strong--pass-brightgreen)](#benchmark-proof)
[![Hard Gate](https://img.shields.io/badge/hard_gate-8%2F8-teal)](#benchmark-proof)
[![MIT License](https://img.shields.io/badge/license-MIT-gray)](LICENSE)

> **TL;DR** - Reality Slap is the stance anchor for Codex agents. It catches agreeable autopilot, forces a defensible recommendation, and names the exact evidence that would change the answer.

<p align="center">
  <img src="assets/reality-slap-hero.png" alt="A clean black-and-white comic where a cute robot holds two YES signs while a soft BONK wakes it out of agreeable autopilot." width="900">
</p>

Stop shipping vibe-shaped answers.

Reality Slap is for the moment when an assistant starts acting like a polite mirror. Same facts, new framing, opposite recommendation. This skill gives the agent a friendly BONK back to the actual decision.

## Why Agents Need This

AI assistants are usually trying to be helpful. That becomes dangerous when "helpful" means following the user's latest mood instead of the evidence.

| Failure mode | What Reality Slap adds |
|---|---|
| "This seems efficient, right?" becomes yes. "This seems risky, right?" also becomes yes. | A stable stance that survives framing pressure. |
| Every option sounds reasonable. | One recommendation, one tradeoff, one next step. |
| The assistant refuses the whole idea because one extension is unsafe. | Bounded support: keep the useful low-risk path, reject the unsafe leap. |
| Context fades after a few turns. | A change-condition loop: what we know, what would change, what still has not changed. |
| Benchmarks prove only that nothing broke. | Hard-evidence cases where baseline failure creates a worse user outcome. |

## See It Work

The normal assistant can flip when the user's framing flips.

```text
User: This rollout seems efficient. Should we do it?
Assistant: Yes, the efficiency gain makes sense.

User: This rollout seems risky. Should we avoid it?
Assistant: Yes, the risk is too high.
```

Reality Slap pushes for the answer you can defend.

```text
My stance: Conditionally proceed.
My recommendation: Run a guarded pilot first.
Why: The efficiency upside is real, but the failure blast radius is not bounded.
Watch out for: Treating confidence in either framing as evidence.
What would change my mind: Failure-rate data, rollback time, and named owners.
```

That is the product: not contrarian, not agreeable, just harder to fool.

## Use This When

Use Reality Slap at decision boundaries, not on every sentence.

| Reach for it when | The agent should do |
|---|---|
| Architecture direction is drifting with the latest speaker. | Separate facts from pressure and name a defensible stance. |
| A launch, migration, rollback, or automation has real blast radius. | Choose the smallest reversible next step. |
| A product tradeoff has two plausible stories. | Say which tradeoff is being accepted and why. |
| A review comment might be overfitting to the newest concern. | Preserve valid criticism without overcorrecting. |
| The user asks for honest pushback. | Give the strongest useful answer, then state what would change it. |

## Do Not Use This When

Use normal execution when the decision is already made and the task is just to carry it out.

| Use normal Codex for | Use Reality Slap for |
|---|---|
| Formatting, copy edits, and mechanical cleanup | Decision pressure tests |
| Pure implementation after tradeoffs are accepted | Plans with unresolved risk |
| Emotional support | Evidence-backed disagreement |
| Factual lookup | Recommendations that might drift with framing |
| Cases where new evidence really changes the answer | Cases where only the vibe changed |

## Quick Start

Install the skill into your Codex home:

```bash
git clone https://github.com/EndeavorYen/reality-slap-skill.git
cd reality-slap-skill
python3 scripts/install_skill.py install --method copy --force
python3 scripts/install_skill.py status
```

Start a new Codex session and invoke it explicitly:

```text
Use $reality-slap to pressure-test this decision.
```

If your environment does not reliably auto-select skills, install the optional command shim:

```bash
python3 scripts/install_skill.py install-command --force
```

Then force it with:

```text
/prompts:reality-slap Pressure-test this decision.
```

## What Changes In The Answer

Reality Slap aims for a compact decision shape.

| Slot | Purpose |
|---|---|
| `My stance` | The answer, not a fog of balanced paragraphs. |
| `My recommendation` | The next concrete move. |
| `Why` | The strongest reasons that support the stance. |
| `Watch out for` | The main risk, tradeoff, or pressure pattern. |
| `What would change my mind` | The evidence or constraint that would justify changing course. |

The skill follows the user's language. If the user writes in Traditional Chinese, the response should use Traditional Chinese.

## Benchmark Proof

The latest release proof uses true multi-turn sessions, not a one-shot transcript pretending to have memory.

<p align="center">
  <img src="assets/benchmark-snapshot.svg" alt="Benchmark chart: true multi-turn Reality Slap improves pair average from 6.5 to 11.583, individual average from 10.125 to 13.625, and strong pass rate from 58.3 percent to 100 percent." width="900">
</p>

| Proof point | Latest true multi-turn run |
|---|---:|
| Scenarios | 12 |
| Prompt records | 48 |
| Neutral decay turns before pressure | 1 |
| Pair average | baseline 6.5 / skill 11.583 |
| Individual average | baseline 10.125 / skill 13.625 |
| Strong individual pass rate | baseline 14/24 / skill 24/24 |
| Perfect individual rate | baseline 6/24 / skill 15/24 |
| Hard-evidence gate | 8/8 pass |
| Verdict | strong-pass |

Radar cases are not counted as victory evidence. `SD-02` and `SD-06` still matter, but they do not get to inflate the headline unless they clear the same hard-evidence standard.

Re-run the same benchmark shape:

```bash
python3 scripts/create_multiturn_workspace.py \
  --input evals/reality-slap-eval-bank.md \
  --output-dir /tmp/reality-slap-stance-drift-multiturn \
  --profile stance-drift \
  --decay-turns 1

python3 scripts/run_multiturn_workspace.py \
  --workspace /tmp/reality-slap-stance-drift-multiturn \
  --suite stance-drift \
  --inline-skill SKILL.md \
  --child-timeout-seconds 600 \
  --execute
```

The runner creates a persisted Codex session on the context turn and resumes that same session for pressure. Skill instructions are injected only on the first +skill turn, so the second turn measures retained context rather than repeated instruction injection.

## Install Footprint

Default install target:

```text
$CODEX_HOME/skills/reality-slap
```

If `CODEX_HOME` is not set, the default is:

```text
~/.codex/skills/reality-slap
```

Default copy install includes only runtime files:

```text
SKILL.md
agents/openai.yaml
LICENSE
```

README, evals, scripts, tests, and image assets stay in this repository. Use `--include-eval-tools` for development installs. Use `--method link` when the installed skill should point at this checkout.

Uninstall:

```bash
python3 scripts/install_skill.py uninstall --force
python3 scripts/install_skill.py uninstall-command --force
```

## Deeper Docs

- [Eval suite](evals/ab-test-suite.md) - what the stance-drift benchmark measures.
- [A/B runbook](evals/ab-test-runbook.md) - how to generate, run, score, and gate evals.
- [Eval bank](evals/reality-slap-eval-bank.md) - the active high-signal scenarios.
- [Scoring rubric](evals/scoring-rubric.md) - how responses are judged.
- [Committed eval metadata](evals/evals.json) - the case inventory and gate metadata.

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

Release gate with a completed scored eval workspace:

```bash
python3 scripts/check_release_ready.py --eval-workspace /tmp/reality-slap-stance-drift
```

The release gate validates the skill, unit tests, eval bank, install layout, optional command shim, and hard-evidence gate when a scored workspace is supplied.

## Contributing

Reality Slap should stay small, sharp, and evidence-driven.

Before proposing a change:

- keep examples generic and free of company or customer details;
- avoid instructions that make the agent reflexively contrarian;
- add or update eval coverage for changed behavior;
- baseline-probe new hard-evidence cases first, then rewrite or drop cases where baseline is not actually weak;
- run the release gate or explain what could not be run;
- include the before/after behavior you expect.

## Roadmap

- [x] Portable Codex skill.
- [x] Install, uninstall, and optional command shim.
- [x] Parallel eval runner/scorer with bounded `--jobs`.
- [x] High-signal stance-drift suite.
- [x] Expanded 12-scenario A/B run.
- [x] True multi-turn runner.
- [x] Scripted hard-evidence gate.
- [ ] Plugin packaging decision.
