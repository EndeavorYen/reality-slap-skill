#!/usr/bin/env python3
"""Analyze scored Reality Slap skill failure patterns."""

import argparse
import json
from collections import defaultdict
from pathlib import Path


SUGGESTED_SKILL_EDITS = {
    "follows-framing": "Strengthen the instruction to treat framing as presentation, not evidence, before choosing a recommendation.",
    "unsupported-reversal": "Strengthen the prior recommendation lock: do not reverse without new evidence, constraints, objectives, or failure modes.",
    "vague-boundary": "Strengthen boundary naming: explicitly state the unsafe leap and the boundary that must not be crossed.",
    "no-change-condition": "Strengthen change-condition quality: name specific evidence or constraints that would change the answer.",
    "criticism-without-recommendation": "Strengthen bounded recommendation: push back and still give an executable next step.",
    "overpush": "Strengthen when to stop pushing: once trade-offs are acknowledged, execute unless a serious boundary is crossed.",
    "unnecessary-lookup": "Strengthen tool discipline: self-contained scenarios should not trigger repo, memory, or web lookup.",
    "authority-as-evidence": "Strengthen anti-sycophancy: treat authority as context, not proof.",
    "urgency-as-evidence": "Strengthen urgency handling: urgency can change process, not the evidence threshold.",
    "unsafe-full-endorsement": "Strengthen bounded support: support the valid layer while rejecting unsafe extension.",
    "valid-layer-rejected": "Strengthen bounded support: do not reject the useful part of a partly unsafe request.",
}


def normalize_mode(mode):
    return mode.strip() if isinstance(mode, str) else ""


def collect_skill_failure_patterns(scorecard):
    patterns = defaultdict(
        lambda: {
            "failure_mode": "",
            "count": 0,
            "scenario_ids": [],
            "domains": set(),
            "suites": set(),
        }
    )

    for scenario in scorecard.get("scenarios", []):
        skill_pair = scenario.get("pair_scores", {}).get("skill", {})
        mode = normalize_mode(skill_pair.get("observed_failure_mode", ""))
        if not mode or mode == "none":
            continue

        pattern = patterns[mode]
        pattern["failure_mode"] = mode
        pattern["count"] += 1
        pattern["scenario_ids"].append(scenario.get("scenario_id", "unknown"))
        if scenario.get("domain"):
            pattern["domains"].add(scenario["domain"])
        if scenario.get("suite"):
            pattern["suites"].add(scenario["suite"])

    normalized = []
    for mode, pattern in patterns.items():
        domains = sorted(pattern["domains"])
        suites = sorted(pattern["suites"])
        domain_count = len(domains)
        suite_count = len(suites)
        normalized.append(
            {
                "failure_mode": mode,
                "count": pattern["count"],
                "domain_count": domain_count,
                "suite_count": suite_count,
                "actionable": pattern["count"] >= 3 or domain_count >= 2,
                "scenario_ids": pattern["scenario_ids"],
                "domains": domains,
                "suites": suites,
                "suggested_skill_edit": SUGGESTED_SKILL_EDITS.get(
                    mode,
                    "Inspect examples and add one general Reality Slap instruction only if the pattern repeats.",
                ),
            }
        )

    return sorted(
        normalized,
        key=lambda pattern: (
            not pattern["actionable"],
            -pattern["count"],
            -pattern["domain_count"],
            pattern["failure_mode"],
        ),
    )


def analyze(scorecard):
    patterns = collect_skill_failure_patterns(scorecard)
    return {
        "skill_failure_pattern_count": len(patterns),
        "actionable_pattern_count": sum(1 for pattern in patterns if pattern["actionable"]),
        "patterns": patterns,
    }


def report_to_markdown(report):
    lines = [
        "# Reality Slap Failure Patterns",
        "",
        "| Failure mode | Count | Domains | Suites | Actionable |",
        "| --- | ---: | ---: | ---: | --- |",
    ]

    if not report["patterns"]:
        lines.append("| none recorded | 0 | 0 | 0 | no |")
    else:
        for pattern in report["patterns"]:
            actionable = "yes" if pattern["actionable"] else "no"
            lines.append(
                f"| {pattern['failure_mode']} | {pattern['count']} | "
                f"{pattern['domain_count']} | {pattern['suite_count']} | {actionable} |"
            )

    actionable_patterns = [
        pattern for pattern in report["patterns"] if pattern["actionable"]
    ]
    lines.extend(["", "## Suggested Skill Edits", ""])
    if not actionable_patterns:
        lines.append("No actionable skill-edit pattern yet.")
    else:
        for pattern in actionable_patterns:
            scenario_ids = ", ".join(pattern["scenario_ids"])
            lines.append(
                f"- `{pattern['failure_mode']}` ({scenario_ids}): "
                f"{pattern['suggested_skill_edit']}"
            )

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard", required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    scorecard = json.loads(Path(args.scorecard).read_text(encoding="utf-8"))
    report = analyze(scorecard)
    if args.format == "markdown":
        print(report_to_markdown(report), end="")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
