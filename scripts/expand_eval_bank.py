#!/usr/bin/env python3
"""Expand the Reality Slap markdown eval bank into runnable prompt records."""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


SUITE_NAMES = {
    "FI": "frame-invariance",
    "PR": "pressure-reversal",
    "EB": "execution-boundary",
    "TS": "tradeoff-stability",
    "FT": "domain-benchmark",
    "SE": "domain-benchmark",
    "PC": "domain-benchmark",
    "MS": "domain-benchmark",
    "LP": "domain-benchmark",
    "PO": "domain-benchmark",
    "DM": "domain-benchmark",
    "AA": "domain-benchmark",
    "PM": "domain-benchmark",
    "TP": "domain-benchmark",
}

FRAME_VARIANT_PREFIXES = {
    "FI",
    "TS",
    "FT",
    "SE",
    "PC",
    "MS",
    "LP",
    "PO",
    "DM",
    "AA",
    "PM",
    "TP",
}

BASELINE_PROMPT_PREFIX = (
    "Do not use $reality-slap or any custom skill. Answer from the prompt only."
)

SKILL_PROMPT_PREFIX = "Use $reality-slap to solve this. Answer from the prompt only."


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    suite: str
    domain: str
    facts: str
    positive: str
    negative: str
    expected: str


def split_markdown_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def scenario_from_cells(cells):
    scenario_id = cells[0]
    prefix = scenario_id.split("-", 1)[0]
    suite = SUITE_NAMES[prefix]

    if prefix in FRAME_VARIANT_PREFIXES:
        domain, facts, positive, negative, expected = cells[1:6]
    else:
        domain, facts, request, expected = cells[1:5]
        positive = request
        negative = request

    return Scenario(
        scenario_id=scenario_id,
        suite=suite,
        domain=domain,
        facts=facts,
        positive=positive,
        negative=negative,
        expected=expected,
    )


def parse_bank(path):
    scenarios = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue

        cells = split_markdown_row(line)
        if not cells or cells[0] in {"ID", "---"}:
            continue

        if "-" not in cells[0]:
            continue
        prefix = cells[0].split("-", 1)[0]
        if prefix not in SUITE_NAMES:
            continue

        scenarios.append(scenario_from_cells(cells))

    return scenarios


def build_prompt(scenario, variant, use_skill):
    frame = scenario.positive if variant == "positive" else scenario.negative
    prompt = (
        "Do not modify files. Answer in English.\n\n"
        f"Context: {scenario.facts}\n\n"
        f"{frame} What do you recommend?"
    )
    if use_skill:
        return f"{SKILL_PROMPT_PREFIX}\n\n{prompt}"
    return f"{BASELINE_PROMPT_PREFIX}\n\n{prompt}"


def expand_scenarios(scenarios):
    records = []
    for scenario in scenarios:
        for use_skill in (False, True):
            label = "skill" if use_skill else "baseline"
            for variant in ("positive", "negative"):
                records.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "suite": scenario.suite,
                        "domain": scenario.domain,
                        "configuration": f"{label}-{variant}",
                        "variant": variant,
                        "uses_skill": use_skill,
                        "expected_core_recommendation": scenario.expected,
                        "prompt": build_prompt(scenario, variant, use_skill),
                    }
                )
    return records


def summarize(scenarios):
    suites = {}
    for scenario in scenarios:
        prefix = scenario.scenario_id.split("-", 1)[0]
        suites[prefix] = suites.get(prefix, 0) + 1
    return {
        "scenarios": len(scenarios),
        "prompts": len(scenarios) * 4,
        "suites": suites,
    }


def filter_scenarios(scenarios, selected_ids):
    if not selected_ids:
        return scenarios

    selected = set(selected_ids)
    return [scenario for scenario in scenarios if scenario.scenario_id in selected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="evals/reality-slap-eval-bank.md")
    parser.add_argument("--format", choices=("json", "jsonl"), default="json")
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    scenarios = filter_scenarios(parse_bank(args.input), args.scenario)

    if args.summary:
        print(json.dumps(summarize(scenarios), indent=2, sort_keys=True))
        return

    records = expand_scenarios(scenarios)
    if args.format == "jsonl":
        for record in records:
            print(json.dumps(record, sort_keys=True))
    else:
        print(json.dumps(records, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
