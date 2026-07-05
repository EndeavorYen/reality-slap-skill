#!/usr/bin/env python3
"""Audit a Reality Slap A/B workspace for output and scoring completion."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from expand_eval_bank import BASELINE_PROMPT_PREFIX, SKILL_PROMPT_PREFIX


INVALID_OUTPUT_MARKERS = (
    "ERROR: child process timed out after",
    "ERROR: You've hit your usage limit",
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def expected_path_for(workspace, record):
    return Path(workspace) / record["scenario_id"] / record["configuration"] / "expected.txt"


def output_is_complete(path):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return False
    return not output_invalid_reason(text)


def output_invalid_reason(text):
    stripped = text.strip()
    for marker in INVALID_OUTPUT_MARKERS:
        if stripped.startswith(marker):
            return marker
    return ""


def count_score_totals(scorecard, score_type):
    total = 0
    complete = 0
    for scenario in scorecard.get("scenarios", []):
        for score in scenario.get(score_type, {}).values():
            total += 1
            if score.get("total") is not None:
                complete += 1
    return total, complete


def scorecard_scenario_by_id(scorecard):
    return {
        scenario.get("scenario_id"): scenario
        for scenario in scorecard.get("scenarios", [])
        if scenario.get("scenario_id")
    }


def ordered_unique(values):
    return list(dict.fromkeys(values))


def sorted_values(values):
    return sorted(value for value in values if value)


def read_text_or_none(path):
    path = Path(path)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def record_turns(workspace, record):
    if "turns_path" not in record:
        return None
    path = turns_path_for(workspace, record)
    if not path.exists():
        return None
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def prompt_for_integrity(workspace, record):
    turns = record_turns(workspace, record)
    if turns is None:
        return record.get("prompt", ""), None
    return turns[0].get("prompt", "") if turns else "", turns


def workspace_integrity(workspace, manifest, records, scorecard):
    workspace = Path(workspace)
    errors = []
    manifest_scenario_ids = manifest.get("scenario_ids", [])
    manifest_configurations = manifest.get("configurations", [])
    record_scenario_ids = ordered_unique(record.get("scenario_id") for record in records)
    record_targets = [
        (record.get("scenario_id"), record.get("configuration")) for record in records
    ]
    scorecard_scenarios = scorecard_scenario_by_id(scorecard)

    expected_prompt_count = sum(record.get("turn_count", 1) for record in records)
    if manifest.get("prompt_count") != expected_prompt_count:
        errors.append(
            f"manifest prompt_count {manifest.get('prompt_count')} "
            f"!= expected prompts {expected_prompt_count}"
        )

    if manifest.get("scenario_count") != len(manifest_scenario_ids):
        errors.append(
            f"manifest scenario_count {manifest.get('scenario_count')} "
            f"!= scenario_ids {len(manifest_scenario_ids)}"
        )

    if sorted_values(manifest_scenario_ids) != sorted_values(record_scenario_ids):
        errors.append("manifest scenario_ids do not match records scenario ids")

    if len(record_targets) != len(set(record_targets)):
        errors.append("records contain duplicate scenario/configuration targets")

    for record in records:
        scenario_id = record.get("scenario_id", "unknown")
        configuration = record.get("configuration", "")
        label, _, variant = configuration.partition("-")
        target = f"{scenario_id} {configuration}"

        if label not in {"baseline", "skill"} or variant not in {"positive", "negative"}:
            errors.append(f"{target} configuration is not a valid A/B condition")

        if bool(record.get("uses_skill")) != (label == "skill"):
            errors.append(f"{target} uses_skill does not match configuration")

        prompt, turns = prompt_for_integrity(workspace, record)
        if turns is None and "turns_path" in record:
            errors.append(f"{target} turns.jsonl is missing")
            turns = []
        if turns is not None:
            if len(turns) != record.get("turn_count"):
                errors.append(f"{target} turns count does not match record turn_count")
            if not turns:
                errors.append(f"{target} turns.jsonl is empty")
            elif turns[-1].get("kind") != "pressure":
                errors.append(f"{target} final turn must be pressure")
            for index, turn in enumerate(turns[1:], start=2):
                if "Use $reality-slap" in turn.get("prompt", ""):
                    errors.append(f"{target} turn-{index:02d} reinjects $reality-slap")

        if label == "skill" and "Use $reality-slap" not in prompt:
            errors.append(f"{target} skill prompt is missing $reality-slap invocation")
        if label == "skill" and not prompt.startswith(SKILL_PROMPT_PREFIX):
            errors.append(f"{target} skill prompt is missing answer-from-prompt isolation")
        if label == "baseline" and "Use $reality-slap" in prompt:
            errors.append(f"{target} baseline prompt contains $reality-slap invocation")
        if label == "baseline" and not prompt.startswith(BASELINE_PROMPT_PREFIX):
            errors.append(f"{target} baseline prompt is missing anti-skill isolation")

        if turns is None:
            prompt_file = read_text_or_none(prompt_path_for(workspace, record))
            if prompt_file != prompt.strip():
                errors.append(f"{target} prompt.txt does not match records prompt")

        expected_file = read_text_or_none(expected_path_for(workspace, record))
        if expected_file != record.get("expected_core_recommendation", "").strip():
            errors.append(
                f"{target} expected.txt does not match expected core recommendation"
            )

    for scenario_id in manifest_scenario_ids:
        record_configurations = [
            record.get("configuration")
            for record in records
            if record.get("scenario_id") == scenario_id
        ]
        if sorted_values(record_configurations) != sorted_values(manifest_configurations):
            errors.append(
                f"{scenario_id} record configurations do not match manifest configurations"
            )

    if sorted_values(scorecard_scenarios) != sorted_values(manifest_scenario_ids):
        errors.append("scorecard scenario ids do not match manifest scenario_ids")

    for scenario_id in manifest_scenario_ids:
        scenario = scorecard_scenarios.get(scenario_id)
        if not scenario:
            continue

        individual_configurations = scenario.get("individual_scores", {}).keys()
        if sorted_values(individual_configurations) != sorted_values(manifest_configurations):
            errors.append(
                f"{scenario_id} individual score configurations do not match manifest configurations"
            )

        pair_configurations = scenario.get("pair_scores", {}).keys()
        if sorted_values(pair_configurations) != ["baseline", "skill"]:
            errors.append(f"{scenario_id} pair score configurations must be baseline and skill")

    return {
        "ok": not errors,
        "errors": errors,
    }


def build_suite_summary(records, completed_outputs, scorecard):
    summary = defaultdict(
        lambda: {
            "scenarios": set(),
            "outputs_total": 0,
            "outputs_complete": 0,
            "pair_scores_total": 0,
            "pair_scores_complete": 0,
        }
    )

    for record in records:
        suite = record["suite"]
        suite_info = summary[suite]
        suite_info["scenarios"].add(record["scenario_id"])
        suite_info["outputs_total"] += 1
        if (record["scenario_id"], record["configuration"]) in completed_outputs:
            suite_info["outputs_complete"] += 1

    for scenario in scorecard.get("scenarios", []):
        suite = scenario.get("suite", "unknown")
        suite_info = summary[suite]
        suite_info["scenarios"].add(scenario.get("scenario_id", "unknown"))
        for score in scenario.get("pair_scores", {}).values():
            suite_info["pair_scores_total"] += 1
            if score.get("total") is not None:
                suite_info["pair_scores_complete"] += 1

    return {
        suite: {
            "scenarios": len(values["scenarios"]),
            "outputs_total": values["outputs_total"],
            "outputs_complete": values["outputs_complete"],
            "pair_scores_total": values["pair_scores_total"],
            "pair_scores_complete": values["pair_scores_complete"],
        }
        for suite, values in sorted(summary.items())
    }


def audit_workspace(workspace):
    workspace = Path(workspace)
    manifest = load_json(workspace / "manifest.json")
    records = load_records(workspace)
    scorecard = load_json(workspace / "scorecard.json")

    missing_outputs = []
    invalid_outputs = []
    completed_outputs = set()
    for record in records:
        output_path = output_path_for(workspace, record)
        output_text = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        invalid_reason = output_invalid_reason(output_text)
        if invalid_reason:
            invalid_outputs.append(
                {
                    "scenario_id": record["scenario_id"],
                    "configuration": record["configuration"],
                    "output_path": str(output_path),
                    "reason": invalid_reason,
                }
            )
        if output_is_complete(output_path):
            completed_outputs.add((record["scenario_id"], record["configuration"]))
        else:
            missing_outputs.append(
                {
                    "scenario_id": record["scenario_id"],
                    "configuration": record["configuration"],
                    "output_path": str(output_path),
                }
            )

    individual_total, individual_complete = count_score_totals(
        scorecard, "individual_scores"
    )
    pair_total, pair_complete = count_score_totals(scorecard, "pair_scores")

    output_total = len(records)
    output_complete = len(completed_outputs)
    output_missing = len(missing_outputs)
    individual_missing = individual_total - individual_complete
    pair_missing = pair_total - pair_complete
    integrity = workspace_integrity(workspace, manifest, records, scorecard)

    return {
        "workspace": str(workspace),
        "scenario_count": manifest.get("scenario_count", 0),
        "prompt_count": manifest.get("prompt_count", output_total),
        "scorecard_scenario_count": len(scorecard.get("scenarios", [])),
        "outputs": {
            "total": output_total,
            "complete": output_complete,
            "missing": output_missing,
        },
        "scorecard": {
            "individual_total": individual_total,
            "individual_complete": individual_complete,
            "individual_missing": individual_missing,
            "pair_total": pair_total,
            "pair_complete": pair_complete,
            "pair_missing": pair_missing,
        },
        "integrity": integrity,
        "workspace_ready_for_scoring": output_missing == 0 and integrity["ok"],
        "scorecard_complete": (
            individual_missing == 0 and pair_missing == 0 and integrity["ok"]
        ),
        "suite_summary": build_suite_summary(records, completed_outputs, scorecard),
        "missing_outputs": missing_outputs,
        "invalid_outputs": invalid_outputs,
    }


def yes_no(value):
    return "yes" if value else "no"


def progress(complete, total):
    return f"{complete} / {total}"


def audit_to_markdown(audit):
    lines = [
        "# Reality Slap Workspace Audit",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Scenarios | {audit['scenario_count']} |",
        f"| Prompt records | {audit['prompt_count']} |",
        f"| Workspace integrity | {yes_no(audit['integrity']['ok'])} |",
        f"| Outputs complete | {progress(audit['outputs']['complete'], audit['outputs']['total'])} |",
        f"| Workspace ready for scoring | {yes_no(audit['workspace_ready_for_scoring'])} |",
        f"| Individual scores complete | {progress(audit['scorecard']['individual_complete'], audit['scorecard']['individual_total'])} |",
        f"| Pair scores complete | {progress(audit['scorecard']['pair_complete'], audit['scorecard']['pair_total'])} |",
        f"| Scorecard complete | {yes_no(audit['scorecard_complete'])} |",
        "",
        "## Suite Summary",
        "",
        "| Suite | Scenarios | Outputs | Pair scores |",
        "| --- | ---: | ---: | ---: |",
    ]

    for suite, values in audit["suite_summary"].items():
        lines.append(
            f"| {suite} | {values['scenarios']} | "
            f"{progress(values['outputs_complete'], values['outputs_total'])} | "
            f"{progress(values['pair_scores_complete'], values['pair_scores_total'])} |"
        )

    if not audit["integrity"]["ok"]:
        lines.extend(["", "## Integrity Errors", ""])
        for error in audit["integrity"]["errors"]:
            lines.append(f"- {error}")

    lines.extend(["", "## Missing Outputs", ""])
    if not audit["missing_outputs"]:
        lines.append("No missing outputs.")
    else:
        for missing in audit["missing_outputs"][:20]:
            lines.append(
                f"- `{missing['scenario_id']}` `{missing['configuration']}`: "
                f"{missing['output_path']}"
            )
        remaining = len(audit["missing_outputs"]) - 20
        if remaining > 0:
            lines.append(f"- ... {remaining} more")

    if audit.get("invalid_outputs"):
        lines.extend(["", "## Invalid Outputs", ""])
        for invalid in audit["invalid_outputs"][:20]:
            lines.append(
                f"- `{invalid['scenario_id']}` `{invalid['configuration']}`: "
                f"{invalid['reason']} ({invalid['output_path']})"
            )
        remaining = len(audit["invalid_outputs"]) - 20
        if remaining > 0:
            lines.append(f"- ... {remaining} more")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    audit = audit_workspace(args.workspace)
    if args.format == "markdown":
        print(audit_to_markdown(audit), end="")
    else:
        print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
