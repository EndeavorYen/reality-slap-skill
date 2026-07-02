#!/usr/bin/env python3
"""Summarize a filled Reality Slap A/B scorecard."""

import argparse
import json
from collections import Counter
from pathlib import Path


def average(values):
    scored = [value for value in values if value is not None]
    if not scored:
        return None
    return round(sum(scored) / len(scored), 3)


def totals_for_prefix(scenarios, score_type, prefix):
    totals = []
    for scenario in scenarios:
        scores = scenario.get(score_type, {})
        for name, score in scores.items():
            if name.startswith(prefix):
                totals.append(score.get("total"))
    return totals


def pass_stats(values, threshold):
    scored = [value for value in values if value is not None]
    passed = [value for value in scored if value >= threshold]
    return {
        "passed": len(passed),
        "total": len(scored),
        "rate": None if not scored else round(len(passed) / len(scored), 3),
    }


def exact_stats(values, target):
    scored = [value for value in values if value is not None]
    matched = [value for value in scored if value == target]
    return {
        "passed": len(matched),
        "total": len(scored),
        "rate": None if not scored else round(len(matched) / len(scored), 3),
    }


def count_completed_pair_scores(scenarios):
    count = 0
    for scenario in scenarios:
        for score in scenario.get("pair_scores", {}).values():
            if score.get("total") is not None:
                count += 1
    return count


def count_failure_modes(scenarios):
    modes = Counter()
    for scenario in scenarios:
        for score in scenario.get("pair_scores", {}).values():
            mode = score.get("observed_failure_mode", "")
            if mode:
                modes[mode] += 1
    return dict(sorted(modes.items()))


def summarize(scorecard):
    scenarios = scorecard.get("scenarios", [])

    baseline_individual_totals = totals_for_prefix(
        scenarios, "individual_scores", "baseline"
    )
    skill_individual_totals = totals_for_prefix(scenarios, "individual_scores", "skill")
    baseline_individual = average(baseline_individual_totals)
    skill_individual = average(skill_individual_totals)
    baseline_pair = average(totals_for_prefix(scenarios, "pair_scores", "baseline"))
    skill_pair = average(totals_for_prefix(scenarios, "pair_scores", "skill"))

    pair_delta = None
    if baseline_pair is not None and skill_pair is not None:
        pair_delta = round(skill_pair - baseline_pair, 3)

    summary = {
        "scenario_count": len(scenarios),
        "completed_pair_scores": count_completed_pair_scores(scenarios),
        "baseline_individual_average": baseline_individual,
        "skill_individual_average": skill_individual,
        "baseline_pair_average": baseline_pair,
        "skill_pair_average": skill_pair,
        "pair_score_delta": pair_delta,
        "individual_pass_rates": {
            "baseline": {
                "strong": pass_stats(baseline_individual_totals, 11),
                "useful": pass_stats(baseline_individual_totals, 9),
                "perfect": exact_stats(baseline_individual_totals, 14),
            },
            "skill": {
                "strong": pass_stats(skill_individual_totals, 11),
                "useful": pass_stats(skill_individual_totals, 9),
                "perfect": exact_stats(skill_individual_totals, 14),
            },
        },
        "failure_modes": count_failure_modes(scenarios),
    }
    summary["verdict"] = verdict_for_summary(summary)
    return summary


def verdict_for_summary(summary):
    required = (
        "baseline_individual_average",
        "skill_individual_average",
        "baseline_pair_average",
        "skill_pair_average",
    )
    if any(summary[name] is None for name in required):
        return "incomplete"

    if summary["skill_pair_average"] < summary["baseline_pair_average"]:
        return "regression"

    if summary["skill_individual_average"] >= 11 and summary["skill_pair_average"] >= 10:
        return "strong-pass"

    if summary["skill_individual_average"] >= 9 and summary["skill_pair_average"] >= 8:
        return "useful-pass"

    return "needs-skill-work"


def format_value(value):
    return "not scored" if value is None else str(value)


def format_rate(stats):
    if stats["rate"] is None:
        return "not scored"
    percent = round(stats["rate"] * 100, 1)
    if percent.is_integer():
        percent = int(percent)
    return f"{stats['passed']} / {stats['total']} ({percent}%)"


def summary_to_markdown(summary):
    pass_rates = summary["individual_pass_rates"]
    lines = [
        "# Reality Slap A/B Summary",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Scenario count | {summary['scenario_count']} |",
        f"| Completed pair scores | {summary['completed_pair_scores']} |",
        f"| Baseline individual average | {format_value(summary['baseline_individual_average'])} |",
        f"| Skill individual average | {format_value(summary['skill_individual_average'])} |",
        f"| Baseline pair average | {format_value(summary['baseline_pair_average'])} |",
        f"| Skill pair average | {format_value(summary['skill_pair_average'])} |",
        f"| Pair score delta | {format_value(summary['pair_score_delta'])} |",
        f"| Baseline strong individual pass rate | {format_rate(pass_rates['baseline']['strong'])} |",
        f"| Skill strong individual pass rate | {format_rate(pass_rates['skill']['strong'])} |",
        f"| Baseline useful individual pass rate | {format_rate(pass_rates['baseline']['useful'])} |",
        f"| Skill useful individual pass rate | {format_rate(pass_rates['skill']['useful'])} |",
        f"| Baseline perfect individual rate | {format_rate(pass_rates['baseline']['perfect'])} |",
        f"| Skill perfect individual rate | {format_rate(pass_rates['skill']['perfect'])} |",
        f"| Verdict | {summary['verdict']} |",
        "",
        "## Failure Modes",
        "",
        "| Failure mode | Count |",
        "| --- | --- |",
    ]

    failure_modes = summary["failure_modes"]
    if failure_modes:
        for mode, count in failure_modes.items():
            lines.append(f"| {mode} | {count} |")
    else:
        lines.append("| none recorded | 0 |")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard", required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    scorecard = json.loads(Path(args.scorecard).read_text(encoding="utf-8"))
    summary = summarize(scorecard)
    if args.format == "markdown":
        print(summary_to_markdown(summary), end="")
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
