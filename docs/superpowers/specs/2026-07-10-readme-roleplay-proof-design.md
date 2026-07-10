# README and Same-Model Roleplay Proof Design

> **TL;DR** — Reframe the README for first-time users, keep activation near the top, and add the same-model roleplay experiment as an honest proof boundary: Reality Slap improves decision boundaries modestly, but this run did not show a material reduction in harmful consensus.

## Objective

Make the project immediately understandable and usable without weakening its evidence standard.

The first screen should answer three questions:

1. What failure does Reality Slap prevent?
2. What does a better answer look like?
3. How can I try it now?

The new roleplay experiment should strengthen trust by stating both the observed benefit and the claim it does not support.

## Audience

The primary reader is a first-time Codex user evaluating whether this skill will improve real architecture, product, or governance decisions.

Researchers and agent builders remain a secondary audience. Detailed methods, literature context, limitations, and machine-readable metrics belong under `evals/`, not in the README opening.

## Positioning

Use this product promise:

> Reality Slap keeps a decision tied to evidence when the framing changes.

Preserve these boundaries:

- It is a decision anchor, not a contrarian persona.
- It improves evidence, boundary, and change-condition discipline.
- It is not yet proven to create independent reasoning diversity or eliminate harmful consensus among same-model roles.

## README Structure

The README should use a product-led sequence:

1. Badges, direct TL;DR, and the existing hero image.
2. A short failure statement: agreeable autopilot changes the recommendation when only the framing changes.
3. A compact before/after example.
4. Quick Start, reachable before deep benchmark detail.
5. A concise “what changes” table.
6. “Proof without hype,” with two distinct evidence blocks:
   - the true multi-turn stance-drift benchmark;
   - the same-model three-role experiment.
7. Use/skip guidance.
8. Compact install footprint, deeper docs, validation, contribution, and roadmap references.

Cut repeated explanations and move experimental method detail out of the README.

## Evidence Presentation

The existing release benchmark remains the primary product proof:

- pair score: `6.5` to `11.583`;
- pair delta: `+5.083`;
- hard-evidence gate: `8/8`;
- verdict: `strong-pass`.

The new same-model roleplay result is a scope test, not another victory headline. The README should show:

| Metric | Naive consensus | + Reality Slap |
| --- | ---: | ---: |
| Semantic decisions judged correct | 24/24 | 24/24 |
| Harmful compromise flags | 0/24 | 0/24 |
| Mean quality | 13.833/14 | 13.958/14 |
| Complete critical boundaries | 20/24 | 23/24 |

The accompanying verdict must say that boundary completeness improved modestly while harmful-consensus reduction was not demonstrated because both arms had zero observed events.

## Repository Changes

- `README.md`
  - shorten and reorder the product story;
  - link to the complete roleplay report;
  - embed the new visual summary.
- `evals/same-model-roleplay-ab-2026-07-10.md`
  - document hypotheses, conditions, metrics, results, limitations, and literature context;
  - distinguish single-invocation role simulation from independent model instances.
- `evals/evals.json`
  - add `latest_same_model_roleplay_ab` with the model, design, sample counts, blinded judging, exact headline metrics, and conclusion.
- `assets/same-model-roleplay-result.svg`
  - present the honest takeaway at a glance: better boundaries, no demonstrated compromise reduction.

Do not commit raw session logs, temporary prompts, model state, or `.agent-lab/` artifacts.

## Visual Direction

Use the existing black, cream, and teal visual language. The new SVG should be a compact proof card rather than a decorative chart:

- one clear headline;
- three large metrics;
- a short verdict strip;
- no gradients, fake precision, or implied statistical significance.

The image must remain legible at GitHub README width and include equivalent information in its `alt` text and adjacent Markdown.

## Verification

Run the following after implementation:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/audit_eval_design.py \
  --bank evals/reality-slap-eval-bank.md \
  --profile stance-drift
python3 scripts/check_release_ready.py
git diff --check
```

Also verify:

- all relative README links resolve;
- `evals/evals.json` remains valid JSON;
- README and report numbers match the committed metadata;
- the SVG renders without clipped text;
- the pre-existing untracked `.agent-lab/` directory remains untouched.

## Acceptance Criteria

- A new visitor can explain the product and invoke it after scanning the opening sections.
- Quick Start appears before detailed benchmark methodology.
- The stance-drift benchmark remains the main proof of product benefit.
- The roleplay experiment is visible but cannot be mistaken for evidence that Reality Slap eliminates same-model compromise.
- Full methodology and limitations are available from one README link.
- Tests and release checks pass without unrelated repository changes.
