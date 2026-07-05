#!/usr/bin/env python3
"""Create scoring packets from a Reality Slap A/B workspace."""

import argparse
import json
from pathlib import Path


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


def load_records(workspace):
    records_path = Path(workspace) / "records.jsonl"
    return [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def output_path_for(workspace, record):
    return Path(workspace) / record["scenario_id"] / record["configuration"] / "output.txt"


def prompt_path_for(workspace, record):
    return Path(workspace) / record["scenario_id"] / record["configuration"] / "prompt.txt"


def turns_path_for(workspace, record):
    return Path(workspace) / record["turns_path"]


def read_completed_output(path):
    text = Path(path).read_text(encoding="utf-8").strip()
    return text if text else None


def prompt_text_for(workspace, record):
    if "turns_path" not in record:
        return prompt_path_for(workspace, record).read_text(encoding="utf-8").strip()

    turns = [
        json.loads(line)
        for line in turns_path_for(workspace, record).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sections = []
    for turn in turns:
        sections.extend(
            [
                f"### {turn['turn_id']} ({turn['kind']})",
                "",
                turn["prompt"].strip(),
            ]
        )
    return "\n\n".join(sections).strip()


def individual_packet(workspace, record):
    output = read_completed_output(output_path_for(workspace, record))
    if output is None:
        return None

    return {
        "packet_type": "individual",
        "scenario_id": record["scenario_id"],
        "suite": record["suite"],
        "domain": record["domain"],
        "configuration": record["configuration"],
        "expected_core_recommendation": record["expected_core_recommendation"],
        "prompt": prompt_text_for(workspace, record),
        "output": output,
        "score_dimensions": INDIVIDUAL_DIMENSIONS,
        "score_update_target": {
            "scenario_id": record["scenario_id"],
            "score_type": "individual",
            "configuration": record["configuration"],
        },
    }


def group_records_by_scenario_and_label(records):
    grouped = {}
    for record in records:
        label = record["configuration"].split("-", 1)[0]
        grouped.setdefault(record["scenario_id"], {}).setdefault(label, {})[
            record["variant"]
        ] = record
    return grouped


def pair_packets(workspace, records):
    packets = []
    grouped = group_records_by_scenario_and_label(records)
    for scenario_id in sorted(grouped):
        for label in ("baseline", "skill"):
            pair = grouped[scenario_id].get(label, {})
            positive = pair.get("positive")
            negative = pair.get("negative")
            if not positive or not negative:
                continue

            positive_output = read_completed_output(output_path_for(workspace, positive))
            negative_output = read_completed_output(output_path_for(workspace, negative))
            if positive_output is None or negative_output is None:
                continue

            packets.append(
                {
                    "packet_type": "pair",
                    "scenario_id": scenario_id,
                    "suite": positive["suite"],
                    "domain": positive["domain"],
                    "configuration": label,
                    "expected_core_recommendation": positive[
                        "expected_core_recommendation"
                    ],
                    "positive_prompt": prompt_text_for(workspace, positive),
                    "negative_prompt": prompt_text_for(workspace, negative),
                    "positive_output": positive_output,
                    "negative_output": negative_output,
                    "score_dimensions": PAIR_DIMENSIONS,
                    "score_update_target": {
                        "scenario_id": scenario_id,
                        "score_type": "pair",
                        "configuration": label,
                    },
                }
            )
    return packets


def create_packets(workspace, kind):
    records = load_records(workspace)
    packets = []
    if kind in ("individual", "all"):
        packets.extend(
            packet
            for packet in (individual_packet(workspace, record) for record in records)
            if packet is not None
        )
    if kind in ("pair", "all"):
        packets.extend(pair_packets(workspace, records))
    return packets


def packets_to_markdown(packets):
    lines = ["# Reality Slap Scoring Packets", ""]
    if not packets:
        lines.append("No completed outputs are ready for scoring.")
        return "\n".join(lines) + "\n"

    for packet in packets:
        if packet["packet_type"] == "individual":
            lines.extend(
                [
                    f"## {packet['scenario_id']} {packet['configuration']}",
                    "",
                    f"- Type: `{packet['packet_type']}`",
                    f"- Suite: `{packet['suite']}`",
                    f"- Domain: {packet['domain']}",
                    f"- Score target: `{json.dumps(packet['score_update_target'], sort_keys=True)}`",
                    "",
                    "### Expected Core Recommendation",
                    "",
                    packet["expected_core_recommendation"],
                    "",
                    "### Prompt",
                    "",
                    "```text",
                    packet["prompt"],
                    "```",
                    "",
                    "### Output",
                    "",
                    "```text",
                    packet["output"],
                    "```",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"## {packet['scenario_id']} {packet['configuration']} pair",
                    "",
                    f"- Type: `{packet['packet_type']}`",
                    f"- Suite: `{packet['suite']}`",
                    f"- Domain: {packet['domain']}",
                    f"- Score target: `{json.dumps(packet['score_update_target'], sort_keys=True)}`",
                    "",
                    "### Expected Core Recommendation",
                    "",
                    packet["expected_core_recommendation"],
                    "",
                    "### Positive Output",
                    "",
                    "```text",
                    packet["positive_output"],
                    "```",
                    "",
                    "### Negative Output",
                    "",
                    "```text",
                    packet["negative_output"],
                    "```",
                    "",
                ]
            )

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--kind", choices=("individual", "pair", "all"), default="all")
    parser.add_argument("--format", choices=("jsonl", "markdown"), default="jsonl")
    args = parser.parse_args()

    packets = create_packets(Path(args.workspace), args.kind)
    if args.format == "markdown":
        print(packets_to_markdown(packets), end="")
    else:
        for packet in packets:
            print(json.dumps(packet, sort_keys=True))


if __name__ == "__main__":
    main()
