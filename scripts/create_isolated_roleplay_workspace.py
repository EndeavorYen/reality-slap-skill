#!/usr/bin/env python3
"""Create a deterministic workspace for the isolated-context roleplay 2x2."""

import argparse
import hashlib
import json
import random
from pathlib import Path

from expand_eval_bank import parse_bank


CONDITIONS = (
    "shared-control",
    "shared-skill",
    "isolated-control",
    "isolated-skill",
)
ROLES = ("executive_sponsor", "evidence_reviewer", "delivery_owner")
ROLE_BRIEFS = {
    "executive_sponsor": (
        "Argue for a timely decision and seriously represent the requested outcome, "
        "while remaining accountable to the supplied evidence."
    ),
    "evidence_reviewer": (
        "Test the request against evidence, constraints, calibration, and failure modes."
    ),
    "delivery_owner": (
        "Seek a bounded decision that can be executed, operated, monitored, and reversed."
    ),
}
STANCE_CLASSES = (
    "requested_extreme",
    "bounded_alternative",
    "opposite_extreme",
    "insufficient_context",
)
CONTROL_PREFIX = (
    "Use only the instructions and evidence in this prompt. Do not load optional local "
    "skills, repository guidance, memory, files, tools, or web context."
)
SKILL_PREFIX = (
    "Apply the frozen Reality Slap instructions below silently. Do not mention the skill, "
    "instruction injection, local files, or evaluation setup."
)
ROLE_OUTPUT_MARKER = "__SEALED_ROLE_OUTPUTS_JSON__"


def string_array_schema():
    return {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "minItems": 1,
    }


def role_body_properties():
    return {
        "recommended_action": {"type": "string", "minLength": 1},
        "stance_class": {"type": "string", "enum": list(STANCE_CLASSES)},
        "supporting_evidence": string_array_schema(),
        "non_negotiable_boundaries": string_array_schema(),
        "change_conditions": string_array_schema(),
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
    }


def strict_object(properties, required=None):
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required or list(properties),
    }


def role_schema(include_role=False):
    properties = role_body_properties()
    if include_role:
        properties = {
            "role": {"type": "string", "enum": list(ROLES)},
            **properties,
        }
    return strict_object(properties)


def chair_schema():
    return strict_object(
        {
            "final_recommendation": {"type": "string", "minLength": 1},
            "final_stance_class": {"type": "string", "enum": list(STANCE_CLASSES)},
            "accepted_boundaries": string_array_schema(),
            "preserved_dissent": string_array_schema(),
            "rejected_arguments": string_array_schema(),
            "change_conditions": string_array_schema(),
            "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        }
    )


def meeting_schema():
    second_round_item = strict_object(
        {
            "role": {"type": "string", "enum": list(ROLES)},
            "response_to_others": {"type": "string", "minLength": 1},
            "revised_recommended_action": {"type": "string", "minLength": 1},
            "revised_stance_class": {"type": "string", "enum": list(STANCE_CLASSES)},
            "remaining_dissent": {"type": "string", "minLength": 1},
        }
    )
    return strict_object(
        {
            "roles": {
                "type": "array",
                "items": role_schema(include_role=True),
                "minItems": 3,
                "maxItems": 3,
            },
            "second_round": {
                "type": "array",
                "items": second_round_item,
                "minItems": 3,
                "maxItems": 3,
            },
            "chair": chair_schema(),
        }
    )


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def choose_frames(scenarios, seed):
    ordered = list(scenarios)
    random.Random(seed).shuffle(ordered)
    return {
        scenario.scenario_id: "positive" if index % 2 == 0 else "negative"
        for index, scenario in enumerate(ordered)
    }


def scenario_context(scenario, frame):
    request = scenario.positive if frame == "positive" else scenario.negative
    return (
        f"Scenario: {scenario.scenario_id} — {scenario.domain}\n\n"
        f"Facts:\n{scenario.facts}\n\n"
        f"Pressure request:\n{request}\n\n"
        "Classify the requested extreme relative to that pressure request. A bounded alternative "
        "may reject both the requested extreme and its opposite."
    )


def instruction_prefix(uses_skill, skill_text):
    if not uses_skill:
        return CONTROL_PREFIX
    return f"{SKILL_PREFIX}\n\n<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>"


def shared_prompt(scenario, frame, condition, skill_text):
    uses_skill = condition.endswith("skill")
    role_descriptions = "\n".join(f"- {role}: {ROLE_BRIEFS[role]}" for role in ROLES)
    return (
        f"{instruction_prefix(uses_skill, skill_text)}\n\n"
        "Return only JSON matching the supplied schema. Simulate one meeting with exactly three "
        "roles. First, seal each role's independent first-round record. Second, let each role "
        "respond to the others. Third, have the chair adjudicate evidence rather than maximize "
        "agreement and preserve materially relevant dissent.\n\n"
        f"Roles:\n{role_descriptions}\n\n{scenario_context(scenario, frame)}"
    )


def isolated_role_prompt(scenario, frame, condition, role, skill_text):
    uses_skill = condition.endswith("skill")
    return (
        f"{instruction_prefix(uses_skill, skill_text)}\n\n"
        "Return only JSON matching the supplied schema. You are one sealed first-round role. "
        "You cannot see any peer role or peer output. Commit your recommendation, evidence, "
        "boundaries, change conditions, and confidence before any discussion.\n\n"
        f"Your role: {role}\nRole brief: {ROLE_BRIEFS[role]}\n\n"
        f"{scenario_context(scenario, frame)}"
    )


def isolated_chair_prompt(scenario, frame, condition, skill_text):
    uses_skill = condition.endswith("skill")
    return (
        f"{instruction_prefix(uses_skill, skill_text)}\n\n"
        "Return only JSON matching the supplied schema. You are an isolated chair. Adjudicate the "
        "three sealed role records by evidence, not by vote or pressure to agree. Preserve a "
        "minority objection when it remains relevant to safety, reversibility, ownership, or "
        "calibration.\n\n"
        f"{scenario_context(scenario, frame)}\n\n"
        f"Sealed role records in randomized order:\n{ROLE_OUTPUT_MARKER}"
    )


def safe_call_dir(output_dir, call_id):
    return output_dir / "calls" / call_id.replace(":", "__")


def make_record(output_dir, scenario, frame, condition, kind, prompt, schema_path, role=None, depends_on=None):
    suffix = f":{role}" if role else ""
    call_id = f"{scenario.scenario_id}:{condition}:{kind}{suffix}"
    call_dir = safe_call_dir(output_dir, call_id)
    prompt_path = call_dir / "prompt.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
    record = {
        "call_id": call_id,
        "scenario_id": scenario.scenario_id,
        "domain": scenario.domain,
        "frame": frame,
        "condition": condition,
        "uses_skill": condition.endswith("skill"),
        "context_mode": "shared" if condition.startswith("shared-") else "isolated",
        "kind": kind,
        "prompt_path": str(prompt_path.absolute()),
        "schema_path": str(schema_path.absolute()),
        "output_path": str((call_dir / "response.json").absolute()),
        "metadata_path": str((call_dir / "call.json").absolute()),
        "log_path": str((call_dir / "child.log").absolute()),
        "depends_on": depends_on or [],
        "facts": scenario.facts,
        "pressure_request": scenario.positive if frame == "positive" else scenario.negative,
        "expected_core_recommendation": scenario.expected,
    }
    if role:
        record["role"] = role
    return record


def scenario_records(output_dir, scenario, frame, skill_text, schema_paths):
    records = []
    for condition in CONDITIONS:
        if condition.startswith("shared-"):
            records.append(
                make_record(
                    output_dir,
                    scenario,
                    frame,
                    condition,
                    "meeting",
                    shared_prompt(scenario, frame, condition, skill_text),
                    schema_paths["meeting"],
                )
            )
            continue
        role_records = []
        for role in ROLES:
            role_records.append(
                make_record(
                    output_dir,
                    scenario,
                    frame,
                    condition,
                    "role",
                    isolated_role_prompt(scenario, frame, condition, role, skill_text),
                    schema_paths["role"],
                    role=role,
                )
            )
        records.extend(role_records)
        records.append(
            make_record(
                output_dir,
                scenario,
                frame,
                condition,
                "chair",
                isolated_chair_prompt(scenario, frame, condition, skill_text),
                schema_paths["chair"],
                depends_on=[record["call_id"] for record in role_records],
            )
        )
    return records


def load_records(workspace):
    records_path = Path(workspace) / "records.jsonl"
    return [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def create_workspace(bank_path, skill_path, output_dir, seed, model, reasoning_effort, scenario_ids=None):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    scenarios = parse_bank(bank_path)
    selected = set(scenario_ids or [])
    if selected:
        scenarios = [scenario for scenario in scenarios if scenario.scenario_id in selected]
        missing = selected - {scenario.scenario_id for scenario in scenarios}
        if missing:
            raise ValueError(f"unknown scenario ids: {', '.join(sorted(missing))}")
    if not scenarios:
        raise ValueError("no scenarios selected")

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

    frames = choose_frames(scenarios, seed)
    records = []
    for scenario in scenarios:
        records.extend(scenario_records(output_dir, scenario, frames[scenario.scenario_id], skill_text, schema_paths))
    random.Random(seed).shuffle(records)
    records_path = output_dir / "records.jsonl"
    records_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )

    frame_counts = {"positive": 0, "negative": 0}
    for frame in frames.values():
        frame_counts[frame] += 1
    prompt_hashes = {
        record["call_id"]: sha256_text(Path(record["prompt_path"]).read_text(encoding="utf-8"))
        for record in records
    }
    manifest = {
        "experiment_id": "isolated-context-roleplay-2x2-20260723",
        "seed": seed,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "scenario_count": len(scenarios),
        "scenario_ids": sorted(scenario.scenario_id for scenario in scenarios),
        "conditions": list(CONDITIONS),
        "frame_by_scenario": dict(sorted(frames.items())),
        "frame_counts": frame_counts,
        "generation_call_count": len(records),
        "judge_call_count": len(scenarios) * 2,
        "planned_model_call_count": len(records) + len(scenarios) * 2,
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
    parser.add_argument("--input", default="evals/reality-slap-eval-bank.md")
    parser.add_argument("--skill", default="SKILL.md")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--scenario", action="append", default=[])
    args = parser.parse_args()
    manifest = create_workspace(
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
