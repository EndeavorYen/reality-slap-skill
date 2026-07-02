#!/usr/bin/env python3
"""Validate score-update JSONL coverage before applying it to a scorecard."""

import argparse
import copy
import json
import sys

from apply_score_updates import (
    SCORE_TYPES,
    apply_updates,
    load_scorecard,
    load_updates,
    scenario_index,
    validate_update,
)


KIND_SCORE_TYPES = {
    "all": ("individual", "pair"),
    "individual": ("individual",),
    "pair": ("pair",),
}


def target_key(update):
    return (
        update.get("scenario_id"),
        update.get("score_type"),
        update.get("configuration"),
    )


def format_target(target):
    scenario_id, score_type, configuration = target
    return f"{scenario_id} {score_type} {configuration}"


def expected_targets(scorecard, kind):
    targets = []
    score_types = KIND_SCORE_TYPES[kind]
    for scenario in scorecard.get("scenarios", []):
        scenario_id = scenario.get("scenario_id")
        if not scenario_id:
            continue
        for score_type in score_types:
            bucket = SCORE_TYPES[score_type]
            for configuration in scenario.get(bucket, {}):
                targets.append((scenario_id, score_type, configuration))
    return targets


def validate_coverage(scorecard, updates, kind):
    scenarios = scenario_index(scorecard)
    expected = set(expected_targets(scorecard, kind))
    seen = {}
    errors = []
    unknown_targets = []
    duplicate_targets = []
    allowed_score_types = set(KIND_SCORE_TYPES[kind])

    for update in updates:
        update_score_type = update.get("score_type")
        if update_score_type not in allowed_score_types:
            line = update.get("_line_number", "?")
            errors.append(
                f"line {line}: unexpected score_type {update_score_type!r} "
                f"for --kind {kind}"
            )
            unknown_targets.append(target_key(update))
            continue

        error = validate_update(update, scenarios)
        if error:
            errors.append(error)
            unknown_targets.append(target_key(update))
            continue

        target = target_key(update)
        if target not in expected:
            line = update.get("_line_number", "?")
            errors.append(f"line {line}: unexpected score target {format_target(target)}")
            unknown_targets.append(target)
            continue

        if target in seen:
            errors.append(f"duplicate score update {format_target(target)}")
            duplicate_targets.append(target)
            continue
        seen[target] = update

    missing_targets = sorted(expected.difference(seen))
    for target in missing_targets:
        errors.append(f"missing score update {format_target(target)}")

    recognized_updates = [seen[target] for target in sorted(seen)]
    score_errors = validate_score_values(scorecard, recognized_updates)
    errors.extend(score_errors)

    return {
        "ok": not errors,
        "expected_updates": len(expected),
        "provided_updates": len(updates),
        "covered_updates": len(seen),
        "missing_update_count": len(missing_targets),
        "duplicate_update_count": len(duplicate_targets),
        "unknown_update_count": len(unknown_targets),
        "missing_targets": [format_target(target) for target in missing_targets],
        "duplicate_targets": [format_target(target) for target in duplicate_targets],
        "unknown_targets": [format_target(target) for target in unknown_targets],
        "errors": errors,
    }


def validate_score_values(scorecard, updates):
    if not updates:
        return []

    scorecard_copy = copy.deepcopy(scorecard)
    errors, _ = apply_updates(scorecard_copy, updates)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard", required=True)
    parser.add_argument("--updates", required=True)
    parser.add_argument("--kind", choices=("all", "individual", "pair"), default="all")
    args = parser.parse_args()

    try:
        scorecard = load_scorecard(args.scorecard)
        updates = load_updates(args.updates)
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

    report = validate_coverage(scorecard, updates, args.kind)
    print(json.dumps(report, indent=2, sort_keys=True))

    if not report["ok"]:
        for error in report["errors"]:
            print(error, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
