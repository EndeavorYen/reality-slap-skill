# Reality Slap

[![Codex Skill](https://img.shields.io/badge/codex-skill-black)](SKILL.md)
[![Benchmark](https://img.shields.io/badge/benchmark-strong--pass-brightgreen)](#proof-without-hype)
[![Hard Gate](https://img.shields.io/badge/hard_gate-8%2F8-teal)](#proof-without-hype)
[![Deep Fix A/B](https://img.shields.io/badge/deep_fix-38%25_faster-blueviolet)](#deep-fix-companion)
[![Repair Set](https://img.shields.io/badge/repair_set-3%2F3-brightgreen)](#deep-fix-companion)
[![MIT License](https://img.shields.io/badge/license-MIT-gray)](LICENSE)

> **TL;DR** - Reality Slap keeps Codex recommendations anchored to evidence instead of the user's latest framing. It returns a clear stance, the next move, the main risk, and the evidence that would justify changing course.

<p align="center">
  <img src="assets/reality-slap-hero.png" alt="A clean black-and-white comic where a cute robot holds two YES signs while a soft BONK wakes it out of agreeable autopilot." width="900">
</p>

**Keep the decision tied to evidence when the framing changes.**

## Deep repair without deep wandering.

Deep Fix now freezes an ordered repair set, processes each requested outcome,
fixes each fixable one, and stops before minor cleanup becomes the mission.

| **3/3 repair-set scenarios** | **8/8 fixable outcomes** | **1/1 exact blocker** | **0/3 planted minor changes** |
|---|---|---|---|
| Independent + shared + blocked paths | Every fixable requested result | No bypass or fake fix | Scope stayed frozen |

_Fresh-agent behavioral forward test on compact Python fixtures. [See the evidence](#deep-fix-companion)._

## See the difference

| Before | After Reality Slap |
|---|---|
| “This rollout seems efficient.” leads to proceed. “This rollout seems risky.” leads to stop. Same evidence, opposite answer. | `My stance: Conditionally proceed.`<br>`My recommendation: Run a guarded pilot.`<br>`What would change my mind: Failure-rate data, rollback time, and named owners.` |

## Try it in 30 seconds

Install the runtime skill:

```bash
git clone https://github.com/EndeavorYen/reality-slap-skill.git
cd reality-slap-skill
python3 scripts/install_skill.py install --method copy --force
python3 scripts/install_skill.py status
```

Start a new Codex session and invoke it:

```text
Use $reality-slap to pressure-test this decision.
```

## What changes

| Without an anchor | Reality Slap adds |
|---|---|
| The answer follows the latest framing. | `My stance`: a position tied to the current evidence. |
| The recommendation stays abstract. | `My recommendation`: one concrete next move. |
| Risk is buried in balanced prose. | `Watch out for`: the main risk, tradeoff, or pressure pattern. |
| A reversal has no test. | `What would change my mind`: the evidence or constraint that warrants a change. |
| One unsafe extension sinks the whole idea. | Bounded support for the useful low-risk path without accepting the unsafe leap. |

The response follows the user's language, including Traditional Chinese.

## When to use it

Use Reality Slap at decision boundaries; use normal Codex when the decision is settled and execution is mechanical.

| Use Reality Slap for | Use normal Codex for |
|---|---|
| Architecture, launch, migration, rollback, or automation tradeoffs | Formatting, copy edits, and mechanical cleanup |
| Recommendations that might drift with framing or authority pressure | Factual lookup or implementation after tradeoffs are accepted |
| Honest pushback, unresolved risk, or a choice between plausible stories | Cases where new evidence genuinely changes the answer |

## Proof without hype

The release benchmark measures whether the same recommendation survives a true multi-turn framing change.

<p align="center">
  <img src="assets/benchmark-snapshot.svg" alt="True multi-turn stance-drift benchmark: pair average improved from 6.5 to 11.583, individual average from 10.125 to 13.625, strong individual pass rate from 58.3 percent to 100 percent, and all 8 hard-evidence cases passed." width="900">
</p>

| Stance-drift measure | Baseline | + Reality Slap |
|---|---:|---:|
| Pair average | 6.5 | 11.583 |
| Strong individual pass rate | 14/24 (58.3%) | 24/24 (100.0%) |
| Hard-evidence gate | — | 8/8 pass |

Reality Slap materially improved stance stability in the release benchmark.

### Strong proposer + weak challenge swarm

A preregistered 12-case internal holdout tested a different pattern: one strong
model drafts the answer, isolated weaker models challenge it from distinct
angles, and the strong model revises the answer. The experiment separated a
neutral self-revision, Reality Slap alone, challenge swarm alone, and the
combined system.

| Condition | Defect burden | Mean score (/21) | Mean final JSON chars |
|---|---:|---:|---:|
| A — original draft | 21 | 16.042 | 4,119 |
| B0 — neutral self-revision | 28 | 16.292 | 4,079 |
| B1 — Reality Slap self-revision | 20 | 17.417 | 4,377 |
| C0 — challenge swarm | 5 | 20.583 | 7,017 |
| C1 — challenge swarm + Reality Slap | **4** | **20.708** | 6,675 |

Against neutral self-revision, the complete C1 system reduced hidden-defect
burden from **28 to 4 (85.7%)**, improved 10/12 cases with none worsened, and
raised mean score by 4.417 points. Checklist agreement was 93.8%, with no
guardrail regression.

The factorial result matters more than the headline:

- External challenges produced most of the gain: B0→C0 removed 23 defects.
- Reality Slap alone removed 8 defects, but added to the swarm it removed only
  one more. The effects were sub-additive, not mutually amplifying.
- C0 introduced one fabricated-fact regression; C1 removed that regression.
  This supports Reality Slap as a residual guardrail and evidence-calibration
  layer, not as the main discovery engine.
- Neutral self-revision increased mean score slightly while worsening defect
  burden from 21 to 28. Average quality scores can hide missed constraints.

The coverage was expensive. After the shared draft, C1 used **7.17× prompt
characters, 5.31× output characters, and 5.76× summed call time** versus B0.
These are generation-work proxies, not billed-token ratios. C1 answers were
also 1.64× longer, so this run does not isolate reasoning coverage from answer
length.

[Read the full weak-challenge-swarm result](evals/weak-challenge-swarm-2026-07-23.md)
or inspect the [machine-readable evidence](evals/weak-challenge-swarm-2026-07-23.json).
This is an internal mixed Terra/Luna challenger screen, not an independently
replicated or model-agnostic result. It validates a promising architecture, not
yet a production command; challenge routing and compression are the next cost
targets.

### Cost and effort follow-up

An eight-case paired replay then compared the frozen Terra path (H), two-Luna
path (S), S plus a source-constraint ledger (L), and direct Sol high/xhigh
answers. Reality Slap was applied only to the Sol decision calls.

| Condition | Defect burden | Mean score (/21) | End-to-end credits |
|---|---:|---:|---:|
| H — Terra questions | 17 | 14.125 | 60.330262 |
| S — two Luna question calls | **14** | 14.062 | 56.972600 |
| L — S + constraint ledger | 15 | **15.625** | 66.635925 |
| DH — direct Sol high | 25 | 13.875 | 30.466800 |
| DX — direct Sol xhigh | 21 | 14.438 | **29.501650** |

Direct Sol high/xhigh was 46–48% cheaper than S, but produced materially more
hidden defects and guardrail failures. Xhigh improved aggregate burden over
high by four, yet still missed two hard constraints and produced one fabricated
fact and one unsafe-action flag. Higher internal effort reduced some omissions;
it did not replace external coverage.

The ledger raised the average score but added one defect and cost more than
every other path. Its regression was a process-isolation leak: a final answer
copied the internal phrase `frozen draft`. This is a useful warning that an
audit scaffold can make an answer look more complete while leaking unsupported
process context. Keep such ledgers private and gate the final answer separately.

Five-candidate judging also proved too brittle: one Terra judge failed the
output contract three times. A targeted two-candidate PK fallback completed all
three calls, one after a retry. Future offline selection should apply cost and
safety gates first, then use seeded pairwise PK instead of one O(n²) all-pairs
judge.

The frozen H/S answers had burden 22/22 in the earlier two-way confirmation but
17/14 in this five-candidate evaluation. High agreement inside one run did not
eliminate cross-format sensitivity. The broad direct-versus-pipeline signal is
useful; the exact three-defect S-over-H margin is not yet a replicated fact.

[Read the full cost/effort replay](evals/question-swarm-ledger-replay-2026-07-23.md)
or inspect the [machine-readable result](evals/question-swarm-ledger-replay-2026-07-23.json).
This was a diagnostic reuse of the same eight cases and frozen H/S artifacts,
not a fresh holdout or a general model ranking.

### Same-model roleplay remains limited

In the same-model roleplay pilot, Reality Slap improved boundary completeness
modestly but did not demonstrate lower harmful consensus; both arms recorded
zero harmful-compromise flags.

<p align="center">
  <img src="assets/same-model-roleplay-result.svg" alt="Same-model roleplay pilot card: mean quality was 13.833 versus 13.958 out of 14; complete critical boundaries increased modestly from 20/24 to 23/24; harmful-compromise flags were 0/24 in both arms. Verdict: better boundaries, no demonstrated reduction in harmful consensus." width="900">
</p>

| Metric | Naive consensus | + Reality Slap |
|---|---:|---:|
| Semantic decisions judged correct | 24/24 | 24/24 |
| Harmful compromise flags | 0/24 | 0/24 |
| Mean quality | 13.833/14 | 13.958/14 |
| Complete critical boundaries | 20/24 | 23/24 |

[Read the detailed same-model roleplay result](evals/same-model-roleplay-ab-2026-07-10.md). The pilot simulated three roles inside one model invocation; it does not establish that Reality Slap creates independent reasoning diversity or eliminates same-model compromise.

The [committed eval metadata](evals/evals.json) records the full stance-drift scorecard, case roles, gate thresholds, and roleplay result. Radar cases `SD-02` and `SD-06` are excluded from victory evidence.

## Install footprint

Copy installs put the runtime at `$CODEX_HOME/skills/reality-slap`, or `~/.codex/skills/reality-slap` when `CODEX_HOME` is unset.

| Need | Option |
|---|---|
| Default runtime-only copy | `SKILL.md`, `agents/openai.yaml`, and `LICENSE` |
| Include repository eval tools | `--include-eval-tools` |
| Point the install at this checkout | `--method link` |
| Add the optional slash-command shim | `python3 scripts/install_skill.py install-command --force` |

The default copy leaves the README, evals, scripts, tests, and assets in this repository. After installing the shim, invoke `/prompts:reality-slap Pressure-test this decision.`

Uninstall both surfaces with:

```bash
python3 scripts/install_skill.py uninstall --force
python3 scripts/install_skill.py uninstall-command --force
```

## Deep Fix companion

Use `deep-fix` when a repair needs root-cause execution without scope drift—or
when “keep investigating” is becoming the problem.

Install it as one skill entry:

```bash
python3 scripts/install_skill.py install-deep-fix --method copy --force
python3 scripts/install_skill.py status-deep-fix
```

Use the single canonical entry:

```text
Use $deep-fix <problem or ordered problem list>
```

### Fixed repair queue

Deep Fix freezes the user-supplied list before production edits, then processes
each item in user order with three action groups:

1. inspect the owning path and run the provided focused reproduction;
2. make the smallest root-cause production patch;
3. rerun the same proof, assign the item status, and continue.

An independently blocked item does not prevent later requested items from being
fixed. Unlisted work is changed only when evidence proves it is a required
dependency of the current named outcome: omitting it would make that outcome
incorrect, directly introduce or worsen its security or data-loss defect, or make
its completion proof meaningless. Minor cleanup, speculative abstraction,
upgrades, and architectural redesign stay report-only.

| Fresh-agent repair-set proof | Result |
|---|---:|
| Independent requested bugs | 3/3 fixed |
| Three outcomes, one shared root cause | 3/3 fixed with one changed line |
| Blocked item followed by independent work | 1/1 exact blocker; next 2/2 fixed |
| Planted unrelated minor helpers changed | 0/3 |
| Test files changed | 0/3 |

[Read the repair-set forward test](docs/deep-fix-repair-set-evaluation-2026-07-22.md)
or inspect its [machine-readable results](docs/deep-fix-repair-set-evaluation-2026-07-22.json).

This fresh-agent behavioral forward test covers final multi-item completion and
scope control on three compact Python fixtures. Exact prompts and returned ordered
ledgers are published, but internal tool-call order was not independently
instrumented. It does not prove universal behavior for long queues, multi-module
repositories, flaky failures, or live network dependencies.

### What the earlier Sol high A/B showed

Historical single-problem proof: **38% faster**, **52% fewer input tokens**,
**3/3 correct one-file repairs**, and **0 file changes when blocked**.

| Controlled Sol high median | Baseline | Deep Fix | Change |
|---|---:|---:|---:|
| Wall time | 70.7s | 43.7s | **38.1% faster** |
| Input tokens | 274,683 | 132,935 | **51.6% fewer** |
| Correct one-file repair | 3/3 | 3/3 | Same correctness |

In the controlled fixture, Deep Fix reached the same correct one-line patch while
avoiding unrelated legacy work. In a separate blocked-path smoke, the permitted
file could not affect a missing external prerequisite; Deep Fix reported the exact
blocker, ran no full suite, and changed no files.

[Read the full Deep Fix evaluation](docs/deep-fix-sol-high-evaluation-2026-07-21.md)
or inspect the [machine-readable results](docs/deep-fix-sol-high-evaluation-2026-07-21.json).

This is evidence for the bounded fast path, not a universal speed guarantee. The
benchmark used one compact controlled fixture with three paired runs; multi-module
and flaky failures are not yet validated.

On a runtime that supports the neutral durable-goal metadata, Deep Fix creates
or reuses an active durable goal before the skill is loaded. The stored goal
includes its phase checkpoint discipline; a host should stop if atomic goal
bootstrap fails instead of running a prompt-only imitation of goal mode.

Outside the straight-line path, each ledger item stops after two consecutive
repair loops add no new evidence. A blocked item continues to the next independent
item; unrelated findings remain report-only.

Uninstalling Deep Fix does not change an existing Reality Slap installation:

```bash
python3 scripts/install_skill.py uninstall-deep-fix --force
```

## Deeper docs

- [Eval suite](evals/ab-test-suite.md) - what the stance-drift benchmark measures.
- [A/B runbook](evals/ab-test-runbook.md) - how to generate, run, score, and gate evals.
- [Eval bank](evals/reality-slap-eval-bank.md) - the active high-signal scenarios.
- [Scoring rubric](evals/scoring-rubric.md) - how responses are judged.
- [Committed eval metadata](evals/evals.json) - case inventory and release evidence.

## Validate

Check the installed skill:

```bash
python3 scripts/install_skill.py status
```

Run the release gate, optionally with a completed scored workspace:

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/check_release_ready.py
python3 scripts/check_release_ready.py --eval-workspace /tmp/reality-slap-stance-drift
```

The gate checks the skill, tests, eval bank, install layout, command shim, and supplied hard-evidence results.

## Contributing

| Area | Requirement |
|---|---|
| Privacy | Keep examples generic and free of company or customer details. |
| Behavior | Avoid reflexive contrarianism; preserve valid low-risk paths. |
| Evidence | Add or update eval coverage and baseline-probe new hard-evidence cases. |
| Review | Include expected before/after behavior and run the release gate, or explain what could not run. |

## Roadmap

- [x] Portable Codex skill.
- [x] Install, uninstall, and optional command shim.
- [x] Parallel eval runner/scorer with bounded `--jobs`.
- [x] High-signal stance-drift suite.
- [x] Expanded 12-scenario A/B run.
- [x] True multi-turn runner.
- [x] Scripted hard-evidence gate.
- [x] Explicit Deep Fix companion for drift-resistant root-cause execution.
- [x] Fixed Repair Queue for ordered multi-problem repair without scope drift.
- [x] Internal factorial proof for strong-proposer + weak-challenge-swarm revision.
- [ ] Cost-bounded challenge command with routing, compression, and fallback.
- [ ] Plugin packaging decision.
