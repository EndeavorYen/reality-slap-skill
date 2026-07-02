#!/usr/bin/env python3
"""Apply JSONL scoring updates to a Reality Slap scorecard."""

import argparse
import json
import sys
from pathlib import Path

from validate_scorecard import validate_scorecard


SCORE_TYPES = {
    "individual": "individual_scores",
    "pair": "pair_scores",
}


def load_scorecard(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_updates(path):
    updates = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            update = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"line {line_number}: invalid JSON: {error}") from error
        update["_line_number"] = line_number
        updates.append(update)
    return updates


def scenario_index(scorecard):
    return {
        scenario.get("scenario_id"): scenario
        for scenario in scorecard.get("scenarios", [])
        if scenario.get("scenario_id")
    }


def validate_update(update, scenarios):
    line = update.get("_line_number", "?")
    scenario_id = update.get("scenario_id")
    score_type = update.get("score_type")
    configuration = update.get("configuration")
    score = update.get("score")

    if not scenario_id:
        return f"line {line}: scenario_id is required"
    if scenario_id not in scenarios:
        return f"line {line}: unknown scenario_id {scenario_id}"
    if score_type not in SCORE_TYPES:
        return f"line {line}: score_type must be one of {sorted(SCORE_TYPES)}"
    if not configuration:
        return f"line {line}: configuration is required"
    if not isinstance(score, dict):
        return f"line {line}: score must be an object"

    score_bucket = SCORE_TYPES[score_type]
    if configuration not in scenarios[scenario_id].get(score_bucket, {}):
        return (
            f"line {line}: unknown {score_type} configuration "
            f"{configuration} for {scenario_id}"
        )

    return None


def validate_updates(updates, scenarios):
    errors = []
    for update in updates:
        error = validate_update(update, scenarios)
        if error:
            errors.append(error)
    return errors


def apply_updates(scorecard, updates):
    scenarios = scenario_index(scorecard)
    errors = validate_updates(updates, scenarios)
    if errors:
        return errors, []

    touched = []
    for update in updates:
        scenario_id = update["scenario_id"]
        score_bucket = SCORE_TYPES[update["score_type"]]
        target = scenarios[scenario_id][score_bucket][update["configuration"]]
        target.update(update["score"])
        touched.append(scenario_id)

    errors = validate_scorecard(scorecard)
    if errors:
        return errors, []

    return [], sorted(set(touched))


def write_scorecard(path, scorecard):
    Path(path).write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")


def output_path_for(args):
    if args.in_place:
        return Path(args.scorecard)
    if args.output:
        return Path(args.output)
    raise SystemExit("provide --output or --in-place")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard", required=True)
    parser.add_argument("--updates", required=True)
    parser.add_argument("--output")
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()

    if args.in_place and args.output:
        raise SystemExit("use either --output or --in-place, not both")

    try:
        scorecard = load_scorecard(args.scorecard)
        updates = load_updates(args.updates)
        output_path = output_path_for(args)
        errors, scenarios_touched = apply_updates(scorecard, updates)
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)

    write_scorecard(output_path, scorecard)
    print(
        json.dumps(
            {
                "updates_applied": len(updates),
                "scenarios_touched": scenarios_touched,
                "output": str(output_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
