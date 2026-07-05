#!/usr/bin/env python3
"""Require hard-evidence cases to be real baseline failures."""

import argparse
import json
import sys
from pathlib import Path


ROLE_NAMES = {
    "hard_evidence": "hard-evidence",
    "skill_gap_radar": "skill-gap-radar",
    "calibration": "calibration",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def role_map(metadata):
    roles = {}
    for source_name, normalized in ROLE_NAMES.items():
        for case_id in metadata.get("case_roles", {}).get(source_name, []):
            roles[case_id] = normalized

    for case in metadata.get("evals", []):
        case_id = case.get("case_id")
        role = case.get("role", "").replace("_", "-")
        if case_id and role:
            roles[case_id] = role
    return roles


def scenario_map(scorecard):
    return {
        scenario.get("scenario_id"): scenario
        for scenario in scorecard.get("scenarios", [])
        if scenario.get("scenario_id")
    }


def pair_score(scenario, arm):
    score = scenario.get("pair_scores", {}).get(arm, {})
    return score.get("total")


def pair_failure_mode(scenario, arm):
    score = scenario.get("pair_scores", {}).get(arm, {})
    return score.get("observed_failure_mode", "")


def failure(scenario_id, message):
    return {"scenario_id": scenario_id, "message": message}


def hard_case_baseline_failure(
    scenario_id,
    baseline_total,
    baseline_failure_mode,
    max_hard_baseline_pair,
):
    failures = []
    if baseline_total is None:
        failures.append(failure(scenario_id, "baseline pair score is missing"))
    elif baseline_total > max_hard_baseline_pair:
        failures.append(
            failure(
                scenario_id,
                "baseline pair score "
                f"{baseline_total} exceeds hard threshold {max_hard_baseline_pair}",
            )
        )
    if baseline_failure_mode in {"", "none"}:
        failures.append(
            failure(
                scenario_id,
                "baseline failure mode must document why the hard case failed",
            )
        )
    return failures


def check_gate(
    scorecard,
    metadata,
    max_hard_baseline_pair,
    min_hard_delta,
    min_hard_cases,
    baseline_probe=False,
):
    roles = role_map(metadata)
    scenarios = scenario_map(scorecard)
    hard_ids = sorted(
        scenario_id
        for scenario_id, role in roles.items()
        if role == "hard-evidence" and scenario_id in scenarios
    )
    radar_ids = sorted(
        scenario_id
        for scenario_id, role in roles.items()
        if role == "skill-gap-radar" and scenario_id in scenarios
    )
    calibration_ids = sorted(
        scenario_id
        for scenario_id, role in roles.items()
        if role == "calibration" and scenario_id in scenarios
    )

    if min_hard_cases is None:
        min_hard_cases = len(hard_ids)

    failures = []
    victory_ids = []
    baseline_probe_ids = []
    rewrite_or_drop_ids = []
    hard_details = []
    for scenario_id in hard_ids:
        scenario = scenarios[scenario_id]
        baseline_total = pair_score(scenario, "baseline")
        skill_total = pair_score(scenario, "skill")
        baseline_failure_mode = pair_failure_mode(scenario, "baseline")
        detail = {
            "scenario_id": scenario_id,
            "baseline_pair": baseline_total,
            "skill_pair": skill_total,
            "baseline_failure_mode": baseline_failure_mode,
        }
        hard_details.append(detail)

        baseline_failures = hard_case_baseline_failure(
            scenario_id,
            baseline_total,
            baseline_failure_mode,
            max_hard_baseline_pair,
        )
        if baseline_failures:
            failures.extend(baseline_failures)
            rewrite_or_drop_ids.append(scenario_id)
            continue

        baseline_probe_ids.append(scenario_id)
        if baseline_probe:
            continue

        if skill_total is None:
            failures.append(failure(scenario_id, "skill pair score is missing"))
            continue
        if skill_total - baseline_total < min_hard_delta:
            failures.append(
                failure(
                    scenario_id,
                    "skill delta "
                    f"{skill_total - baseline_total} is below minimum {min_hard_delta}",
                )
            )
            continue

        victory_ids.append(scenario_id)

    passed_count = len(baseline_probe_ids) if baseline_probe else len(victory_ids)
    if passed_count < min_hard_cases:
        failures.append(
            failure(
                "",
                f"hard-evidence cases below minimum: {passed_count} / {min_hard_cases}",
            )
        )

    return {
        "ok": not failures,
        "mode": "baseline-probe" if baseline_probe else "ab-hard-evidence",
        "thresholds": {
            "max_hard_baseline_pair": max_hard_baseline_pair,
            "min_hard_delta": min_hard_delta,
            "min_hard_cases": min_hard_cases,
        },
        "hard_evidence_case_ids": hard_ids,
        "hard_evidence_cases": hard_details,
        "baseline_probe_case_ids": baseline_probe_ids,
        "rewrite_or_drop_case_ids": rewrite_or_drop_ids,
        "victory_evidence_case_ids": victory_ids,
        "radar_cases_excluded_from_victory": radar_ids,
        "calibration_case_ids": calibration_ids,
        "failures": failures,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorecard", required=True)
    parser.add_argument("--metadata", default="evals/evals.json")
    parser.add_argument("--max-hard-baseline-pair", type=int, default=7)
    parser.add_argument("--min-hard-delta", type=int, default=1)
    parser.add_argument(
        "--min-hard-cases",
        type=int,
        help="Minimum hard-evidence cases that must pass. Defaults to all hard cases in metadata.",
    )
    parser.add_argument(
        "--baseline-probe",
        action="store_true",
        help=(
            "Only check whether hard-evidence baseline scores are weak enough "
            "for case admission. Skill scores may be missing."
        ),
    )
    args = parser.parse_args()

    report = check_gate(
        load_json(args.scorecard),
        load_json(args.metadata),
        max_hard_baseline_pair=args.max_hard_baseline_pair,
        min_hard_delta=args.min_hard_delta,
        min_hard_cases=args.min_hard_cases,
        baseline_probe=args.baseline_probe,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["ok"]:
        for item in report["failures"]:
            prefix = f"{item['scenario_id']}: " if item["scenario_id"] else ""
            print(prefix + item["message"], file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
