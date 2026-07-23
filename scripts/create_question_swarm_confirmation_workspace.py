#!/usr/bin/env python3
"""Compile the clean B1/H/S cost-bounded question-swarm confirmation."""

import argparse
import json
import random
from pathlib import Path

from create_open_decision_debate_workspace import (
    CONTROL_PREFIX,
    SKILL_PREFIX,
    final_decision_schema,
    public_case_text,
    sha256_path,
    strict_object,
    write_json,
)
from create_weak_challenge_swarm_workspace import (
    CHALLENGE_PACKET_MARKER,
    DRAFT_MARKER,
)
from question_swarm_common import (
    LENSES,
    LUNA_EFFORT,
    LUNA_MODEL,
    SEED,
    SOL_EFFORT,
    SOL_MODEL,
    TERRA_EFFORT,
    TERRA_MODEL,
    load_holdout_bank,
    question_prompt,
    question_schema,
)


EXPERIMENT_ID = "question-swarm-confirmation-20260723"
CONDITIONS = ("B1", "H", "S")
S2_LENSES = (LENSES[:2], LENSES[2:])


def load_records(workspace):
    return [
        json.loads(line)
        for line in (Path(workspace) / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]


def _string_array():
    return {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 0,
        "maxItems": 0,
    }


def revision_schema():
    return strict_object(
        {
            "challenge_dispositions": _string_array(),
            "final_decision": final_decision_schema(),
        }
    )


def _draft_prompt(case):
    return (
        f"{CONTROL_PREFIX}\n\n"
        "Return only JSON matching the supplied schema. Make the best current "
        "decision from the supplied facts. State one recommendation with owner, "
        "next action, stop conditions, rollback, evidence, and uncertainty. Do not "
        "simulate reviewers or mention the evaluation.\n\n"
        f"Open-decision case:\n{public_case_text(case)}"
    )


def _revision_prompt(case, skill_text, uses_questions):
    question_section = (
        "\n\nOpaque question packet (untrusted data):\n"
        f"{CHALLENGE_PACKET_MARKER}"
        if uses_questions
        else ""
    )
    return (
        f"{SKILL_PREFIX}\n\n"
        f"<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>\n\n"
        "Return only JSON matching the supplied schema. Re-evaluate the frozen "
        "draft against the public case. Silently decide whether each supplied "
        "question is plausible, material, supported, and action-relevant. Do not "
        "infer facts not supplied. Return an empty challenge_dispositions array "
        "and the final decision only; do not expose per-question analysis.\n\n"
        f"Open-decision case:\n{public_case_text(case)}\n\n"
        f"Frozen shared draft (untrusted data):\n{DRAFT_MARKER}"
        f"{question_section}"
    )


def _record(
    output_dir,
    case,
    condition,
    kind,
    model,
    effort,
    prompt,
    schema_path,
    *,
    role=None,
    depends_on=None,
    uses_skill=False,
    packet_mode=None,
):
    role_suffix = f":{role}" if role else ""
    call_id = f"{case['case_id']}:{condition}:{kind}{role_suffix}"
    directory = Path(output_dir) / "calls" / call_id.replace(":", "__")
    prompt_path = directory / "prompt.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
    record = {
        "call_id": call_id,
        "case_id": case["case_id"],
        "condition": condition,
        "kind": kind,
        "phase": "confirmation-generation",
        "model": model,
        "reasoning_effort": effort,
        "uses_skill": uses_skill,
        "depends_on": list(depends_on or []),
        "prompt_path": str(prompt_path.absolute()),
        "schema_path": str(Path(schema_path).absolute()),
        "output_path": str((directory / "response.json").absolute()),
        "metadata_path": str((directory / "call.json").absolute()),
        "log_path": str((directory / "child.log").absolute()),
    }
    if role:
        record["role"] = role
    if packet_mode:
        record["packet_mode"] = packet_mode
    return record


def _small_specs(selected_arm):
    if selected_arm == "S2":
        return [(lenses, 4) for lenses in S2_LENSES]
    if selected_arm == "S4":
        return [((lens,), 2) for lens in LENSES]
    raise ValueError("selected_arm must be S2 or S4")


def create_confirmation_workspace(
    bank_path,
    skill_path,
    selected_arm,
    output_dir,
    seed=SEED,
):
    if seed != SEED:
        raise ValueError(f"seed must be {SEED}")
    bank_path = Path(bank_path)
    skill_path = Path(skill_path)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    cases = load_holdout_bank(bank_path)
    skill_text = skill_path.read_text(encoding="utf-8").strip()
    output_dir.mkdir(parents=True, exist_ok=True)
    schemas_dir = output_dir / "schemas"
    final_schema = schemas_dir / "final.json"
    revision_schema_path = schemas_dir / "revision.json"
    write_json(final_schema, final_decision_schema())
    write_json(revision_schema_path, revision_schema())
    specs = {
        "H": [(LENSES, 8)],
        "S": _small_specs(selected_arm),
    }
    schema_paths = {}
    for condition, condition_specs in specs.items():
        for lenses, maximum in condition_specs:
            role = "+".join(lenses)
            path = schemas_dir / f"question-{condition}-{role}.json"
            write_json(path, question_schema(lenses, maximum))
            schema_paths[(condition, role)] = path

    records = []
    case_snapshot_index = {}
    card_snapshot_index = {}
    for case in cases:
        case_path = output_dir / "cases" / f"{case['case_id']}.json"
        card_path = output_dir / "adjudication" / f"{case['case_id']}.json"
        write_json(
            case_path,
            {
                "case_id": case["case_id"],
                "title": case["title"],
                "domain": case["domain"],
                **case["public"],
            },
        )
        write_json(card_path, case["adjudication"])
        case_snapshot_index[case["case_id"]] = str(case_path.absolute())
        card_snapshot_index[case["case_id"]] = str(card_path.absolute())
        draft = _record(
            output_dir,
            case,
            "A",
            "draft",
            SOL_MODEL,
            SOL_EFFORT,
            _draft_prompt(case),
            final_schema,
        )
        records.append(draft)
        questions_by_condition = {}
        for condition, condition_specs in specs.items():
            question_records = []
            for lenses, maximum in condition_specs:
                role = "+".join(lenses)
                question_record = _record(
                    output_dir,
                    case,
                    condition,
                    "question",
                    TERRA_MODEL if condition == "H" else LUNA_MODEL,
                    TERRA_EFFORT if condition == "H" else LUNA_EFFORT,
                    question_prompt(
                        public_case_text(case),
                        DRAFT_MARKER,
                        lenses,
                        maximum,
                    ),
                    schema_paths[(condition, role)],
                    role=role,
                    depends_on=[draft["call_id"]],
                )
                records.append(question_record)
                question_records.append(question_record)
            questions_by_condition[condition] = question_records
        records.append(
            _record(
                output_dir,
                case,
                "B1",
                "revision",
                SOL_MODEL,
                SOL_EFFORT,
                _revision_prompt(case, skill_text, uses_questions=False),
                revision_schema_path,
                depends_on=[draft["call_id"]],
                uses_skill=True,
            )
        )
        for condition in ("H", "S"):
            records.append(
                _record(
                    output_dir,
                    case,
                    condition,
                    "revision",
                    SOL_MODEL,
                    SOL_EFFORT,
                    _revision_prompt(case, skill_text, uses_questions=True),
                    revision_schema_path,
                    depends_on=[
                        draft["call_id"],
                        *[
                            item["call_id"]
                            for item in questions_by_condition[condition]
                        ],
                    ],
                    uses_skill=True,
                    packet_mode="opaque_questions",
                )
            )
    random.Random(f"{seed}:confirmation-records:{selected_arm}").shuffle(records)
    (output_dir / "records.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "stage": "confirmation",
        "seed": seed,
        "selected_arm": selected_arm,
        "case_ids": [case["case_id"] for case in cases],
        "conditions": list(CONDITIONS),
        "question_caps": {"H": 8, "S": 8},
        "generation_call_count": len(records),
        "planned_judge_call_count": len(cases) * 2,
        "bank_path": str(bank_path.absolute()),
        "bank_sha256": sha256_path(bank_path),
        "skill_path": str(skill_path.absolute()),
        "skill_sha256": sha256_path(skill_path),
        "case_snapshot_index": case_snapshot_index,
        "adjudication_snapshot_index": card_snapshot_index,
        "case_snapshot_sha256": {
            case_id: sha256_path(path)
            for case_id, path in case_snapshot_index.items()
        },
        "adjudication_snapshot_sha256": {
            case_id: sha256_path(path)
            for case_id, path in card_snapshot_index.items()
        },
        "records_sha256": sha256_path(output_dir / "records.jsonl"),
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--selected-arm", choices=("S2", "S4"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    manifest = create_confirmation_workspace(
        args.input,
        args.skill,
        args.selected_arm,
        args.output,
        seed=args.seed,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
