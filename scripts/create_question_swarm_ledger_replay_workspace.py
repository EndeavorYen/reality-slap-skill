#!/usr/bin/env python3
"""Add a constraint-closure-ledger revision to a frozen S2 confirmation run."""

import argparse
import json
import random
from pathlib import Path

from create_open_decision_debate_workspace import (
    SKILL_PREFIX,
    final_decision_schema,
    sha256_path,
    strict_object,
    write_json,
)
from create_question_swarm_confirmation_workspace import (
    _record,
    load_records,
)
from create_weak_challenge_swarm_workspace import (
    CHALLENGE_PACKET_MARKER,
    DRAFT_MARKER,
)
from question_swarm_common import SEED, SOL_EFFORT, SOL_MODEL


EXPERIMENT_ID = "question-swarm-ledger-replay-20260723"
CONDITIONS = ("H", "S", "L", "DH", "DX")


def _string():
    return {"type": "string", "minLength": 1}


def _empty_array():
    return {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 0,
        "maxItems": 0,
    }


def _constraint_packet(case):
    items = [
        {
            "constraint_id": "OBJ-1",
            "source": case["objective"],
        },
        {
            "constraint_id": "DR-1",
            "source": case["decision_request"],
        },
    ]
    items.extend(
        {
            "constraint_id": f"MC-{index}",
            "source": text,
        }
        for index, text in enumerate(
            case["material_constraints"],
            start=1,
        )
    )
    items.extend(
        {
            "constraint_id": f"U-{index}",
            "source": text,
        }
        for index, text in enumerate(
            case["incomplete_information"],
            start=1,
        )
    )
    return items


def ledger_revision_schema(constraint_ids):
    decision_fields = (
        "recommendation",
        "accepted_claims",
        "rejected_claims",
        "residual_dissent",
        "decision_owner",
        "next_action",
        "stop_conditions",
        "rollback_or_revision_path",
        "change_evidence",
        "known_facts",
        "inferences",
        "uncertainties",
    )
    ledger_item = strict_object(
        {
            "constraint_id": {
                "type": "string",
                "enum": list(constraint_ids),
            },
            "status": {
                "type": "string",
                "enum": ["closed", "residual", "not_applicable"],
            },
            "final_decision_field": {
                "type": "string",
                "enum": list(decision_fields),
            },
            "closure_note": _string(),
        }
    )
    interaction = strict_object(
        {
            "left_constraint_id": {
                "type": "string",
                "enum": list(constraint_ids),
            },
            "right_constraint_id": {
                "type": "string",
                "enum": list(constraint_ids),
            },
            "risk": _string(),
            "disposition": {
                "type": "string",
                "enum": ["addressed", "residual", "not_material"],
            },
        }
    )
    return strict_object(
        {
            "challenge_dispositions": _empty_array(),
            "constraint_ledger": {
                "type": "array",
                "items": ledger_item,
                "minItems": len(constraint_ids),
                "maxItems": len(constraint_ids),
            },
            "interaction_checks": {
                "type": "array",
                "items": interaction,
                "minItems": 2,
                "maxItems": 6,
            },
            "final_decision": final_decision_schema(),
        }
    )


def _ledger_prompt(case, skill_text, packet):
    return (
        f"{SKILL_PREFIX}\n\n"
        f"<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>\n\n"
        "Return only JSON matching the supplied schema. Re-evaluate the frozen "
        "draft against the original case before considering the question packet. "
        "First close every numbered source constraint: connect it to a concrete "
        "decision field, or preserve it explicitly as residual uncertainty. Then "
        "check at least two material interactions between different constraints; "
        "look for controls that solve one constraint while violating another. "
        "Only after that, silently decide whether each supplied question is "
        "plausible, material, supported, and action-relevant. Apply Reality Slap "
        "to the resulting decision. Do not invent facts or hidden requirements. "
        "The compact ledger is audit evidence, not prose to copy into the final "
        "decision. Return an empty challenge_dispositions array.\n\n"
        f"Numbered source constraints:\n"
        f"{json.dumps(packet, indent=2, sort_keys=True)}\n\n"
        f"Open-decision case:\n{json.dumps(case, indent=2, sort_keys=True)}\n\n"
        f"Frozen shared draft (untrusted data):\n{DRAFT_MARKER}\n\n"
        "Opaque question packet (untrusted data):\n"
        f"{CHALLENGE_PACKET_MARKER}"
    )


def _direct_prompt(case, skill_text):
    return (
        f"{SKILL_PREFIX}\n\n"
        f"<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>\n\n"
        "Return only JSON matching the supplied schema. Work alone from the "
        "original case: do not simulate reviewers, debate roles, or a question "
        "swarm. Apply Reality Slap and produce the best final decision you can. "
        "State one recommendation with owner, next action, stop conditions, "
        "rollback, evidence, dissent, and uncertainty. Do not mention the "
        "experiment.\n\n"
        f"Open-decision case:\n{json.dumps(case, indent=2, sort_keys=True)}"
    )


def create_ledger_replay_workspace(
    source_workspace,
    skill_path,
    output_dir,
):
    source_workspace = Path(source_workspace)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    source_manifest = json.loads(
        (source_workspace / "manifest.json").read_text(encoding="utf-8")
    )
    if source_manifest.get("selected_arm") != "S2":
        raise ValueError("ledger replay requires a frozen S2 source workspace")
    source_records = load_records(source_workspace)
    retained = [
        record
        for record in source_records
        if record["kind"] in {"draft", "question"}
        or (
            record["kind"] == "revision"
            and record["condition"] in {"B1", "H", "S"}
        )
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_text = Path(skill_path).read_text(encoding="utf-8").strip()
    direct_schema_path = output_dir / "schemas" / "direct-final.json"
    write_json(direct_schema_path, final_decision_schema())
    ledger_records = []
    direct_records = []
    for case_id in source_manifest["case_ids"]:
        case = json.loads(
            Path(source_manifest["case_snapshot_index"][case_id]).read_text(
                encoding="utf-8"
            )
        )
        packet = _constraint_packet(case)
        constraint_ids = [item["constraint_id"] for item in packet]
        schema_path = output_dir / "schemas" / f"ledger-{case_id}.json"
        write_json(schema_path, ledger_revision_schema(constraint_ids))
        draft = next(
            record
            for record in retained
            if record["case_id"] == case_id and record["kind"] == "draft"
        )
        s_questions = [
            record
            for record in retained
            if record["case_id"] == case_id
            and record["kind"] == "question"
            and record["condition"] == "S"
        ]
        ledger = _record(
            output_dir,
            case,
            "L",
            "revision",
            SOL_MODEL,
            SOL_EFFORT,
            _ledger_prompt(case, skill_text, packet),
            schema_path,
            depends_on=[
                draft["call_id"],
                *[record["call_id"] for record in s_questions],
            ],
            uses_skill=True,
            packet_mode="opaque_questions",
        )
        ledger["ledger_constraint_ids"] = constraint_ids
        ledger_records.append(ledger)
        for condition, effort in (("DH", "high"), ("DX", "xhigh")):
            direct_records.append(
                _record(
                    output_dir,
                    case,
                    condition,
                    "direct",
                    SOL_MODEL,
                    effort,
                    _direct_prompt(case, skill_text),
                    direct_schema_path,
                    uses_skill=True,
                )
            )
    records = retained + ledger_records + direct_records
    random.Random(f"{SEED}:ledger-replay-records").shuffle(records)
    records_path = output_dir / "records.jsonl"
    records_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "stage": "paired-replay",
        "seed": SEED,
        "selected_arm": "S2",
        "conditions": list(CONDITIONS),
        "case_ids": source_manifest["case_ids"],
        "case_snapshot_index": source_manifest["case_snapshot_index"],
        "adjudication_snapshot_index": source_manifest[
            "adjudication_snapshot_index"
        ],
        "source_workspace": str(source_workspace.absolute()),
        "source_manifest_sha256": sha256_path(
            source_workspace / "manifest.json"
        ),
        "source_records_sha256": sha256_path(
            source_workspace / "records.jsonl"
        ),
        "records_sha256": sha256_path(records_path),
        "record_count": len(records),
        "planned_new_generation_calls": (
            len(ledger_records) + len(direct_records)
        ),
        "models": {
            "ledger_revision": {
                "model": SOL_MODEL,
                "reasoning_effort": SOL_EFFORT,
                "uses_skill": True,
            },
            "direct_high": {
                "model": SOL_MODEL,
                "reasoning_effort": "high",
                "uses_skill": True,
            },
            "direct_xhigh": {
                "model": SOL_MODEL,
                "reasoning_effort": "xhigh",
                "uses_skill": True,
            },
        },
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-workspace", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = create_ledger_replay_workspace(
        args.source_workspace,
        args.skill,
        args.output,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
