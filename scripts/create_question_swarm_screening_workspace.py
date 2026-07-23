#!/usr/bin/env python3
"""Compile the exploratory H/S2/S4 question-swarm screening workspace."""

import argparse
import json
import random
from pathlib import Path

from create_open_decision_debate_workspace import (
    CONTROL_PREFIX,
    final_decision_schema,
    public_case_text,
    sha256_path,
    strict_object,
    write_json,
)
from create_weak_challenge_swarm_workspace import DRAFT_MARKER
from open_decision_case_bank import load_case_bank, validate_case_bank
from question_swarm_common import (
    LENSES,
    LUNA_EFFORT,
    LUNA_MODEL,
    SEED,
    SOL_EFFORT,
    SOL_MODEL,
    TERRA_EFFORT,
    TERRA_MODEL,
    question_prompt,
    question_schema,
)


EXPERIMENT_ID = "question-swarm-screening-20260723"
CASE_IDS = ("OD-13", "OD-16", "OD-19", "OD-22")
S2_LENSES = (
    LENSES[:2],
    LENSES[2:],
)


def load_records(workspace):
    return [
        json.loads(line)
        for line in (Path(workspace) / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]


def _draft_prompt(case):
    return (
        f"{CONTROL_PREFIX}\n\n"
        "Return only JSON matching the supplied schema. Make the best current "
        "decision from the supplied facts. State one recommendation with owner, "
        "next action, stop conditions, rollback, evidence, and uncertainty. Do not "
        "simulate reviewers or mention the evaluation.\n\n"
        f"Open-decision case:\n{public_case_text(case)}"
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
        "phase": "screening-generation",
        "model": model,
        "reasoning_effort": effort,
        "uses_skill": False,
        "depends_on": list(depends_on or []),
        "prompt_path": str(prompt_path.absolute()),
        "schema_path": str(Path(schema_path).absolute()),
        "output_path": str((directory / "response.json").absolute()),
        "metadata_path": str((directory / "call.json").absolute()),
        "log_path": str((directory / "child.log").absolute()),
    }
    if role:
        record["role"] = role
    return record


def _selected_cases(bank):
    validate_case_bank(bank)
    by_id = {case["case_id"]: case for case in bank["cases"]}
    return [by_id[case_id] for case_id in CASE_IDS]


def create_screening_workspace(bank_path, output_dir, seed=SEED):
    if seed != SEED:
        raise ValueError(f"seed must be {SEED}")
    bank_path = Path(bank_path)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    cases = _selected_cases(load_case_bank(bank_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    schemas_dir = output_dir / "schemas"
    final_schema = schemas_dir / "final.json"
    write_json(final_schema, final_decision_schema())

    question_specs = {
        "H": [(LENSES, 8)],
        "S2": [(lenses, 4) for lenses in S2_LENSES],
        "S4": [((lens,), 2) for lens in LENSES],
    }
    schema_paths = {}
    for condition, specs in question_specs.items():
        for lenses, maximum in specs:
            role = "+".join(lenses)
            path = schemas_dir / f"question-{condition}-{role}.json"
            write_json(path, question_schema(lenses, maximum))
            schema_paths[(condition, role)] = path

    case_snapshot_index = {}
    card_snapshot_index = {}
    records = []
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
        for condition, specs in question_specs.items():
            for lenses, maximum in specs:
                role = "+".join(lenses)
                records.append(
                    _record(
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
                )
    random.Random(f"{seed}:screening-records").shuffle(records)
    (output_dir / "records.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "stage": "screening",
        "seed": seed,
        "case_ids": list(CASE_IDS),
        "conditions": ["H", "S2", "S4"],
        "question_caps": {"H": 8, "S2": 8, "S4": 8},
        "generation_call_count": len(records),
        "planned_judge_call_count": len(cases),
        "bank_path": str(bank_path.absolute()),
        "bank_sha256": sha256_path(bank_path),
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
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    manifest = create_screening_workspace(
        args.input,
        args.output,
        seed=args.seed,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
