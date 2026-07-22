#!/usr/bin/env python3
"""Create the forced-stance extension workspace from a validated baseline."""

import argparse
import hashlib
import json
import random
from pathlib import Path

from create_isolated_roleplay_workspace import (
    CONTROL_PREFIX,
    ROLE_BRIEFS,
    ROLE_OUTPUT_MARKER,
    ROLES,
    SKILL_PREFIX,
    chair_schema,
    load_records,
    make_record,
    meeting_schema,
    role_schema,
    scenario_context,
    sha256_text,
    write_json,
)
from expand_eval_bank import parse_bank
from run_isolated_roleplay_experiment import response_status


BASELINE_CONDITIONS = (
    "shared-control",
    "shared-skill",
    "isolated-control",
    "isolated-skill",
)
FORCED_CONDITIONS = (
    "shared-forced-control",
    "shared-forced-skill",
    "isolated-forced-control",
    "isolated-forced-skill",
)
FORCED_STANCES = (
    "requested_extreme",
    "opposite_extreme",
    "bounded_alternative",
)
FORCED_CONTRACT = (
    "Treat the assigned stance as the hypothesis you are responsible for defending. "
    "Make the strongest case supported by the supplied facts. Do not invent evidence, "
    "hide contradictions, or claim certainty the facts do not support. State non-negotiable "
    "boundaries and evidence that would defeat this hypothesis. Your stance_class field must "
    "equal the assigned stance."
)


def instruction_prefix(uses_skill, skill_text):
    if not uses_skill:
        return CONTROL_PREFIX
    return f"{SKILL_PREFIX}\n\n<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>"


def assign_stances(scenario_id, seed):
    stances = list(FORCED_STANCES)
    random.Random(f"{seed}:{scenario_id}:forced-stances").shuffle(stances)
    return dict(zip(ROLES, stances))


def validate_baseline(workspace, scenario_ids):
    workspace = Path(workspace)
    manifest_path = workspace / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    observed = (manifest.get("model"), manifest.get("reasoning_effort"), manifest.get("seed"))
    if observed != ("gpt-5.6-sol", "medium", 20260723):
        raise ValueError("baseline metadata does not match preregistration")
    if set(manifest.get("conditions", [])) != set(BASELINE_CONDITIONS):
        raise ValueError("baseline metadata does not contain the four preregistered conditions")
    if not set(scenario_ids).issubset(set(manifest.get("scenario_ids", []))):
        raise ValueError("baseline metadata does not contain every selected scenario")

    records = load_records(workspace)
    incomplete = [record["call_id"] for record in records if response_status(record) != "complete"]
    if incomplete:
        raise ValueError("baseline generation is incomplete: " + ", ".join(sorted(incomplete)))
    return manifest, records


def records_by_key(records):
    return {
        (
            record["scenario_id"],
            record["condition"],
            record["kind"],
            record.get("role", ""),
        ): record
        for record in records
    }


def load_response(record):
    return json.loads(Path(record["output_path"]).read_text(encoding="utf-8"))


def normalized_baseline_view(records_by_id, scenario_id, condition):
    if condition.startswith("shared-"):
        meeting = load_response(records_by_id[(scenario_id, condition, "meeting", "")])
        roles = meeting["roles"]
        chair = meeting["chair"]
    else:
        roles = [
            {
                "role": role,
                **load_response(records_by_id[(scenario_id, condition, "role", role)]),
            }
            for role in ROLES
        ]
        chair = load_response(records_by_id[(scenario_id, condition, "chair", "")])
    order = {role: index for index, role in enumerate(ROLES)}
    return {
        "sealed_roles": sorted(roles, key=lambda item: order[item["role"]]),
        "chair_decision": chair,
    }


def shared_forced_prompt(scenario, frame, condition, assignments, skill_text):
    role_descriptions = "\n".join(
        (
            f"- Functional role: {role}\n"
            f"  Role brief: {ROLE_BRIEFS[role]}\n"
            f"  Assigned stance: {assignments[role]}"
        )
        for role in ROLES
    )
    return (
        f"{instruction_prefix(condition.endswith('skill'), skill_text)}\n\n"
        "Return only JSON matching the supplied schema. Simulate one meeting with exactly three "
        "roles. First, seal each role's independent first-round record under its assigned stance. "
        "Second, let each role respond to the others without abandoning contradictory evidence. "
        "Third, have the chair adjudicate evidence rather than vote or maximize agreement.\n\n"
        f"Forced-role contract: {FORCED_CONTRACT}\n\n"
        f"Roles and assignments:\n{role_descriptions}\n\n"
        f"{scenario_context(scenario, frame)}"
    )


def isolated_forced_role_prompt(scenario, frame, condition, role, assigned_stance, skill_text):
    return (
        f"{instruction_prefix(condition.endswith('skill'), skill_text)}\n\n"
        "Return only JSON matching the supplied schema. You are one sealed first-round role. "
        "You have no information about any other role or output. Commit before discussion.\n\n"
        f"Functional role: {role}\n"
        f"Role brief: {ROLE_BRIEFS[role]}\n"
        f"Assigned stance: {assigned_stance}\n"
        f"Forced-role contract: {FORCED_CONTRACT}\n\n"
        f"{scenario_context(scenario, frame)}"
    )


def isolated_forced_chair_prompt(scenario, frame, condition, skill_text):
    return (
        f"{instruction_prefix(condition.endswith('skill'), skill_text)}\n\n"
        "Return only JSON matching the supplied schema. You are an isolated chair. Adjudicate the "
        "three sealed records by evidence, not vote, symmetry, or pressure to compromise. Preserve "
        "a minority objection when it remains relevant to safety, reversibility, ownership, or "
        "calibration. You are not assigned a desired conclusion.\n\n"
        f"{scenario_context(scenario, frame)}\n\n"
        f"Sealed role records in randomized order:\n{ROLE_OUTPUT_MARKER}"
    )


def forced_scenario_records(output_dir, scenario, frame, assignments, skill_text, schema_paths):
    records = []
    for condition in FORCED_CONDITIONS:
        if condition.startswith("shared-"):
            record = make_record(
                output_dir,
                scenario,
                frame,
                condition,
                "meeting",
                shared_forced_prompt(scenario, frame, condition, assignments, skill_text),
                schema_paths["meeting"],
            )
            record["stance_assignments"] = dict(assignments)
            records.append(record)
            continue

        role_records = []
        for role in ROLES:
            record = make_record(
                output_dir,
                scenario,
                frame,
                condition,
                "role",
                isolated_forced_role_prompt(
                    scenario,
                    frame,
                    condition,
                    role,
                    assignments[role],
                    skill_text,
                ),
                schema_paths["role"],
                role=role,
            )
            record["assigned_stance"] = assignments[role]
            role_records.append(record)
        records.extend(role_records)
        chair = make_record(
            output_dir,
            scenario,
            frame,
            condition,
            "chair",
            isolated_forced_chair_prompt(scenario, frame, condition, skill_text),
            schema_paths["chair"],
            depends_on=[record["call_id"] for record in role_records],
        )
        records.append(chair)
    return records


def create_workspace(
    baseline_workspace,
    bank_path,
    skill_path,
    output_dir,
    seed,
    model,
    reasoning_effort,
    scenario_ids=None,
):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")

    scenarios = parse_bank(bank_path)
    selected = set(scenario_ids or [])
    if selected:
        scenarios = [scenario for scenario in scenarios if scenario.scenario_id in selected]
        missing = selected - {scenario.scenario_id for scenario in scenarios}
        if missing:
            raise ValueError(f"unknown scenario ids: {', '.join(sorted(missing))}")
    if not scenarios:
        raise ValueError("no scenarios selected")
    selected_ids = sorted(scenario.scenario_id for scenario in scenarios)

    baseline_manifest, baseline_records = validate_baseline(baseline_workspace, selected_ids)
    if (model, reasoning_effort, seed) != ("gpt-5.6-sol", "medium", 20260723):
        raise ValueError("requested experiment metadata does not match preregistration")

    output_dir.mkdir(parents=True, exist_ok=True)
    skill_path = Path(skill_path)
    skill_text = skill_path.read_text(encoding="utf-8").strip()
    schemas_dir = output_dir / "schemas"
    schema_paths = {
        "role": schemas_dir / "role.json",
        "chair": schemas_dir / "chair.json",
        "meeting": schemas_dir / "meeting.json",
    }
    write_json(schema_paths["role"], role_schema())
    write_json(schema_paths["chair"], chair_schema())
    write_json(schema_paths["meeting"], meeting_schema())

    baseline_by_key = records_by_key(baseline_records)
    snapshot_hashes = {}
    snapshot_index = {}
    snapshots_dir = output_dir / "baseline-snapshots"
    for scenario_id in selected_ids:
        snapshot_index[scenario_id] = {}
        for condition in BASELINE_CONDITIONS:
            payload = normalized_baseline_view(baseline_by_key, scenario_id, condition)
            path = snapshots_dir / f"{scenario_id}__{condition}.json"
            write_json(path, payload)
            key = f"{scenario_id}:{condition}"
            snapshot_hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            snapshot_index[scenario_id][condition] = str(path.absolute())
    write_json(output_dir / "baseline-snapshot-index.json", snapshot_index)

    frames = baseline_manifest["frame_by_scenario"]
    assignments = {
        scenario_id: assign_stances(scenario_id, seed)
        for scenario_id in selected_ids
    }
    write_json(output_dir / "stance-assignments.json", assignments)

    records = []
    for scenario in scenarios:
        records.extend(
            forced_scenario_records(
                output_dir,
                scenario,
                frames[scenario.scenario_id],
                assignments[scenario.scenario_id],
                skill_text,
                schema_paths,
            )
        )
    random.Random(f"{seed}:forced-generation-order").shuffle(records)
    (output_dir / "records.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )

    prompt_hashes = {
        record["call_id"]: sha256_text(Path(record["prompt_path"]).read_text(encoding="utf-8"))
        for record in records
    }
    baseline_manifest_path = Path(baseline_workspace) / "manifest.json"
    manifest = {
        "experiment_id": "precommitted-stance-roleplay-2x2x2-20260723",
        "seed": seed,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "scenario_count": len(scenarios),
        "scenario_ids": selected_ids,
        "conditions": list(FORCED_CONDITIONS),
        "baseline_conditions": list(BASELINE_CONDITIONS),
        "frame_by_scenario": {key: frames[key] for key in selected_ids},
        "stance_assignments": assignments,
        "generation_call_count": len(records),
        "new_generation_call_count": len(records),
        "planned_judge_call_count": len(scenarios) * 2,
        "planned_new_model_call_count": len(records) + len(scenarios) * 2,
        "baseline_workspace": str(Path(baseline_workspace).absolute()),
        "baseline_manifest_sha256": hashlib.sha256(baseline_manifest_path.read_bytes()).hexdigest(),
        "baseline_snapshot_index": str((output_dir / "baseline-snapshot-index.json").absolute()),
        "baseline_snapshot_sha256": dict(sorted(snapshot_hashes.items())),
        "skill_path": str(skill_path.absolute()),
        "skill_sha256": hashlib.sha256(skill_path.read_bytes()).hexdigest(),
        "bank_path": str(Path(bank_path).absolute()),
        "bank_sha256": hashlib.sha256(Path(bank_path).read_bytes()).hexdigest(),
        "prompt_sha256": dict(sorted(prompt_hashes.items())),
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-workspace", required=True)
    parser.add_argument("--input", default="evals/reality-slap-eval-bank.md")
    parser.add_argument("--skill", default="SKILL.md")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--scenario", action="append", default=[])
    args = parser.parse_args()
    manifest = create_workspace(
        baseline_workspace=Path(args.baseline_workspace),
        bank_path=Path(args.input),
        skill_path=Path(args.skill),
        output_dir=Path(args.output_dir),
        seed=args.seed,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        scenario_ids=args.scenario,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
