#!/usr/bin/env python3
"""Compare Reality Slap scorecard summaries across runs."""

import argparse
import json
from pathlib import Path

from analyze_failure_patterns import analyze as analyze_failures
from summarize_scorecard import summarize


def parse_run_arg(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("--run must use label=/path/to/scorecard.json")
    label, path = value.split("=", 1)
    if not label:
        raise argparse.ArgumentTypeError("--run label must not be empty")
    if not path:
        raise argparse.ArgumentTypeError("--run path must not be empty")
    return label, Path(path)


def load_run(label, path):
    scorecard = json.loads(path.read_text(encoding="utf-8"))
    failure_report = analyze_failures(scorecard)
    skill_failure_counts = {
        pattern["failure_mode"]: pattern["count"]
        for pattern in failure_report["patterns"]
    }
    return {
        "label": label,
        "path": str(path),
        "summary": summarize(scorecard),
        "skill_failure_modes": skill_failure_counts,
    }


def delta(after, before):
    if after is None or before is None:
        return None
    return round(after - before, 3)


def failure_mode_delta(previous, current):
    modes = set(previous["skill_failure_modes"]) | set(current["skill_failure_modes"])
    changes = {}
    for mode in sorted(modes):
        change = current["skill_failure_modes"].get(mode, 0) - previous[
            "skill_failure_modes"
        ].get(mode, 0)
        if change != 0:
            changes[mode] = change
    return changes


def compare_pair(previous, current):
    summary_before = previous["summary"]
    summary_after = current["summary"]
    skill_individual_delta = delta(
        summary_after["skill_individual_average"],
        summary_before["skill_individual_average"],
    )
    skill_pair_delta = delta(
        summary_after["skill_pair_average"],
        summary_before["skill_pair_average"],
    )
    pair_score_delta_delta = delta(
        summary_after["pair_score_delta"],
        summary_before["pair_score_delta"],
    )

    verdict_change = (
        f"{summary_before['verdict']} -> {summary_after['verdict']}"
        if summary_before["verdict"] != summary_after["verdict"]
        else summary_after["verdict"]
    )

    return {
        "from": previous["label"],
        "to": current["label"],
        "skill_individual_average_delta": skill_individual_delta,
        "skill_pair_average_delta": skill_pair_delta,
        "pair_score_delta_delta": pair_score_delta_delta,
        "verdict_change": verdict_change,
        "skill_failure_mode_delta": failure_mode_delta(previous, current),
        "improved": any(
            value is not None and value > 0
            for value in (
                skill_individual_delta,
                skill_pair_delta,
                pair_score_delta_delta,
            )
        ),
    }


def compare_runs(runs):
    return {
        "runs": runs,
        "comparisons": [
            compare_pair(previous, current)
            for previous, current in zip(runs, runs[1:])
        ],
    }


def format_value(value):
    return "n/a" if value is None else str(value)


def format_delta(value):
    if value is None:
        return "n/a"
    if value > 0:
        return f"+{value}"
    return str(value)


def format_failure_delta(changes):
    if not changes:
        return "none"
    return ", ".join(f"`{mode}`: {format_delta(change)}" for mode, change in changes.items())


def report_to_markdown(report):
    lines = [
        "# Reality Slap Scorecard Trend",
        "",
        "| Run | Verdict | Skill individual avg | Skill pair avg | Pair delta |",
        "| --- | --- | ---: | ---: | ---: |",
    ]

    for run in report["runs"]:
        summary = run["summary"]
        lines.append(
            f"| {run['label']} | {summary['verdict']} | "
            f"{format_value(summary['skill_individual_average'])} | "
            f"{format_value(summary['skill_pair_average'])} | "
            f"{format_value(summary['pair_score_delta'])} |"
        )

    lines.extend(
        [
            "",
            "## Adjacent Comparisons",
            "",
            "| Change | Improved | Skill individual | Skill pair | Pair delta | Failure mode delta |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )

    for comparison in report["comparisons"]:
        lines.append(
            f"| {comparison['from']} -> {comparison['to']} | "
            f"{'yes' if comparison['improved'] else 'no'} | "
            f"{format_delta(comparison['skill_individual_average_delta'])} | "
            f"{format_delta(comparison['skill_pair_average_delta'])} | "
            f"{format_delta(comparison['pair_score_delta_delta'])} | "
            f"{format_failure_delta(comparison['skill_failure_mode_delta'])} |"
        )

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", type=parse_run_arg, required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    if len(args.run) < 2:
        raise SystemExit("provide at least two --run label=scorecard.json arguments")

    runs = [load_run(label, path) for label, path in args.run]
    report = compare_runs(runs)
    if args.format == "markdown":
        print(report_to_markdown(report), end="")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
