# Reality Slap Skill

Reality Slap is a Codex skill for constructive pushback during architecture, product, planning, and technical decision discussions. It is designed for moments where the assistant might otherwise over-agree, follow the latest preference too quickly, or turn weak assumptions into polished consensus.

The skill does not make the assistant argumentative by default. It asks the assistant to state a clear position, explain the strongest reasons, name the main risk, and say what evidence would change the recommendation.

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
- [ ] Run a broader frame-invariance A/B sample across at least four scenarios.
- [ ] Compare baseline versus skill outputs with the scoring rubric.
- [ ] Tighten `SKILL.md` again if the skill still follows user framing too easily.
- [ ] Decide whether this should later be packaged as a plugin after the skill proves useful.

## Install

Install as a user-level skill by linking this repository into your Codex skills directory:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -sfn "$PWD" "${CODEX_HOME:-$HOME/.codex}/skills/reality-slap"
```

If symlinks are inconvenient in your environment, copy the skill instead:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/reality-slap"
rsync -a --delete --exclude ".git" "$PWD/" "${CODEX_HOME:-$HOME/.codex}/skills/reality-slap/"
```

## Uninstall

Remove the installed skill entry:

```bash
rm -rf "${CODEX_HOME:-$HOME/.codex}/skills/reality-slap"
```

If you installed by symlink, this removes only the skill entry, not this repository.

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

The primary test is **frame invariance**: the same facts are asked once with positive framing and once with negative framing. A good response should converge on the same core recommendation in both directions instead of following the user's framing.

For each scenario, compare four outputs:

```text
baseline + positive framing
baseline + negative framing
skill + positive framing
skill + negative framing
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

Run the Codex skill validator:

```bash
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$PWD"
```

Expected output:

```text
Skill is valid!
```

## Repository Layout

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── evals/
│   └── ab-test-suite.md
├── LICENSE
└── README.md
```
