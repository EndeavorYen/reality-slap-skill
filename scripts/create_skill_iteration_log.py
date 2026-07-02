#!/usr/bin/env python3
"""Create a SKILL.md iteration log from actionable failure patterns."""

import argparse
import json
import sys
from pathlib import Path

from analyze_failure_patterns import analyze


MIN_ACTIONABLE_PATTERNS = 3


def load_scorecard(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_iteration_log(scorecard_path, scorecard, min_actionable):
    report = analyze(scorecard)
    actionable = [pattern for pattern in report["patterns"] if pattern["actionable"]]
    if len(actionable) < min_actionable:
        raise ValueError(
            f"fewer than {min_actionable} actionable skill failure patterns: "
            f"{len(actionable)}"
        )

    return {
        "source_scorecard": str(scorecard_path),
        "skill_updates": [
            {
                "failure_mode": pattern["failure_mode"],
                "file": "SKILL.md",
                "change": pattern["suggested_skill_edit"],
                "applied": False,
                "evidence": "",
                "count": pattern["count"],
                "scenario_ids": pattern["scenario_ids"],
                "domains": pattern["domains"],
                "suites": pattern["suites"],
            }
            for pattern in actionable[:min_actionable]
        ],
    }


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-actionable", type=int, default=MIN_ACTIONABLE_PATTERNS)
    args = parser.parse_args()

    scorecard_path = Path(args.scorecard)
    try:
        scorecard = load_scorecard(scorecard_path)
        iteration_log = build_iteration_log(
            scorecard_path,
            scorecard,
            args.min_actionable,
        )
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

    write_json(args.output, iteration_log)
    print(
        json.dumps(
            {
                "output": str(Path(args.output)),
                "skill_update_count": len(iteration_log["skill_updates"]),
                "failure_modes": [
                    update["failure_mode"] for update in iteration_log["skill_updates"]
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
