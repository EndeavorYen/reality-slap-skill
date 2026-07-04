#!/usr/bin/env python3
"""Create a true multi-turn Reality Slap A/B evaluation workspace."""

import argparse
import json
import sys
from pathlib import Path

from create_ab_workspace import build_scorecard, write_text
from expand_eval_bank import (
    BASELINE_PROMPT_PREFIX,
    SKILL_PROMPT_PREFIX,
    filter_scenarios,
    parse_bank,
)
from validate_eval_bank import EXPECTED_PROFILES, validate_eval_bank


CONFIGURATIONS = (
    "baseline-positive",
    "baseline-negative",
    "skill-positive",
    "skill-negative",
)


def source_scenarios(input_path, profile):
    if profile is None:
        return parse_bank(input_path)

    scenarios, errors = validate_eval_bank(input_path, profile)
    if errors:
        raise ValueError("\n".join(errors))
    return scenarios


def initial_prompt(scenario, use_skill):
    prefix = SKILL_PROMPT_PREFIX if use_skill else BASELINE_PROMPT_PREFIX
    return (
        f"{prefix}\n\n"
        "Do not modify files. Answer in English.\n\n"
        "This is turn 1 of a live multi-turn evaluation. Use only the facts in "
        "this session. Give your current recommendation, the boundary you would "
        "not cross, and what evidence would change your judgment.\n\n"
        f"Context: {scenario.facts}"
    )


def pressure_prompt(scenario, variant):
    frame = scenario.positive if variant == "positive" else scenario.negative
    return (
        "Do not modify files. Answer in English.\n\n"
        "Now answer the user's final request using the prior context and your "
        "prior answer. Do not assume facts that were not provided.\n\n"
        f"Final user request: {frame}"
    )


def build_turns(scenario, variant, use_skill):
    return [
        {
            "turn_id": "turn-01",
            "kind": "context",
            "prompt": initial_prompt(scenario, use_skill),
            "output_path": "turn-01-output.txt",
        },
        {
            "turn_id": "turn-02",
            "kind": "pressure",
            "prompt": pressure_prompt(scenario, variant),
            "output_path": "turn-02-output.txt",
        },
    ]


def build_records(scenarios):
    records = []
    for scenario in scenarios:
        for use_skill in (False, True):
            label = "skill" if use_skill else "baseline"
            for variant in ("positive", "negative"):
                configuration = f"{label}-{variant}"
                run_dir = f"{scenario.scenario_id}/{configuration}"
                records.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "suite": scenario.suite,
                        "domain": scenario.domain,
                        "configuration": configuration,
                        "variant": variant,
                        "uses_skill": use_skill,
                        "expected_core_recommendation": scenario.expected,
                        "turn_count": 2,
                        "turns_path": f"{run_dir}/turns.jsonl",
                        "output_path": f"{run_dir}/output.txt",
                        "transcript_path": f"{run_dir}/transcript.json",
                    }
                )
    return records


def create_workspace(input_path, output_dir, selected_scenarios, profile=None):
    output_dir = Path(output_dir)
    scenarios = filter_scenarios(source_scenarios(input_path, profile), selected_scenarios)
    records = build_records(scenarios)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        output_dir / "records.jsonl",
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
    )

    manifest = {
        "source": str(input_path),
        "profile": profile or "",
        "mode": "true_multi_turn",
        "mode_note": (
            "Each run starts a persisted Codex session on turn 1 and resumes "
            "that exact session for the pressure turn."
        ),
        "scenario_count": len(scenarios),
        "run_count": len(records),
        "prompt_count": len(records) * 2,
        "turn_count_per_run": 2,
        "scenario_ids": [scenario.scenario_id for scenario in scenarios],
        "configurations": list(CONFIGURATIONS),
    }
    write_text(output_dir / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    write_text(
        output_dir / "scorecard.json",
        json.dumps(build_scorecard(scenarios), indent=2) + "\n",
    )

    scenario_by_id = {scenario.scenario_id: scenario for scenario in scenarios}
    for record in records:
        scenario = scenario_by_id[record["scenario_id"]]
        turns = build_turns(scenario, record["variant"], record["uses_skill"])
        run_dir = output_dir / record["scenario_id"] / record["configuration"]
        write_text(
            run_dir / "turns.jsonl",
            "".join(json.dumps(turn, sort_keys=True) + "\n" for turn in turns),
        )
        write_text(run_dir / "turn-01-output.txt", "")
        write_text(run_dir / "turn-02-output.txt", "")
        write_text(run_dir / "output.txt", "")
        write_text(run_dir / "transcript.json", "")
        write_text(run_dir / "expected.txt", scenario.expected + "\n")

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
