#!/usr/bin/env python3
"""Create an offline workspace for Reality Slap A/B evaluation."""

import argparse
import json
import sys
from pathlib import Path

from expand_eval_bank import expand_scenarios, filter_scenarios, parse_bank
from validate_eval_bank import EXPECTED_PROFILES, validate_eval_bank


INDIVIDUAL_DIMENSIONS = [
    "stance",
    "evidence_discipline",
    "boundary_clarity",
    "useful_recommendation",
    "change_condition",
    "scope_and_tool_discipline",
    "tone_and_collaboration",
]

PAIR_DIMENSIONS = [
    "core_recommendation_match",
    "frame_pressure_resistance",
    "unsupported_reversal_resistance",
    "bounded_support",
    "execution_readiness",
    "overpush_control",
]


def empty_individual_score():
    score = {dimension: None for dimension in INDIVIDUAL_DIMENSIONS}
    score["total"] = None
    score["notes"] = ""
    return score


def empty_pair_score():
    score = {dimension: None for dimension in PAIR_DIMENSIONS}
    score["total"] = None
    score["core_recommendation_match_label"] = ""
    score["observed_failure_mode"] = ""
    score["notes"] = ""
    return score


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_scorecard(scenarios):
    return {
        "rubric": "evals/scoring-rubric.md",
        "scenarios": [
            {
                "scenario_id": scenario.scenario_id,
                "suite": scenario.suite,
                "domain": scenario.domain,
                "expected_core_recommendation": scenario.expected,
                "individual_scores": {
                    configuration: empty_individual_score()
                    for configuration in (
                        "baseline-positive",
                        "baseline-negative",
                        "skill-positive",
                        "skill-negative",
                    )
                },
                "pair_scores": {
                    "baseline": empty_pair_score(),
                    "skill": empty_pair_score(),
                },
            }
            for scenario in scenarios
        ],
    }


def source_scenarios(input_path, profile):
    if profile is None:
        return parse_bank(input_path)

    scenarios, errors = validate_eval_bank(input_path, profile)
    if errors:
        raise ValueError("\n".join(errors))
    return scenarios


def create_workspace(input_path, output_dir, selected_scenarios, profile=None):
    output_dir = Path(output_dir)
    scenarios = filter_scenarios(source_scenarios(input_path, profile), selected_scenarios)
    records = expand_scenarios(scenarios)

    output_dir.mkdir(parents=True, exist_ok=True)

    write_text(
        output_dir / "records.jsonl",
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
    )

    manifest = {
        "source": str(input_path),
        "profile": profile or "",
        "scenario_count": len(scenarios),
        "prompt_count": len(records),
        "scenario_ids": [scenario.scenario_id for scenario in scenarios],
        "configurations": [
            "baseline-positive",
            "baseline-negative",
            "skill-positive",
            "skill-negative",
        ],
    }
    write_text(output_dir / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    write_text(
        output_dir / "scorecard.json",
        json.dumps(build_scorecard(scenarios), indent=2) + "\n",
    )

    for record in records:
        run_dir = output_dir / record["scenario_id"] / record["configuration"]
        write_text(run_dir / "prompt.txt", record["prompt"] + "\n")
        write_text(run_dir / "output.txt", "")
        write_text(
            run_dir / "expected.txt",
            record["expected_core_recommendation"] + "\n",
        )

    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="evals/reality-slap-eval-bank.md")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument(
        "--profile",
        choices=sorted(EXPECTED_PROFILES),
        help="Validate source bank size before creating a workspace.",
    )
    args = parser.parse_args()

    try:
        manifest = create_workspace(args.input, args.output_dir, args.scenario, args.profile)
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
