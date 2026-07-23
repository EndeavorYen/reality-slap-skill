#!/usr/bin/env python3
"""Compile the frozen weak-challenge-swarm factorial generation workspace."""

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
    sha256_payload,
    strict_object,
    string_array,
    write_json,
)
from open_decision_case_bank import load_case_bank, select_cases, validate_case_bank


SEED = 20260725
EXPERIMENT_ID = "weak-challenge-swarm-20260725"
SOL_MODEL = "gpt-5.6-sol"
SOL_EFFORT = "medium"
TERRA_MODEL = "gpt-5.6-terra"
TERRA_EFFORT = "medium"
LUNA_MODEL = "gpt-5.6-luna"
LUNA_EFFORT = "medium"
ROLES = (
    "boundary_scout",
    "adversarial_auditor",
    "operational_auditor",
)
CONDITIONS = ("A", "B0", "B1", "C0", "C1")
DRAFT_MARKER = "__SHARED_DRAFT_JSON__"
CHALLENGE_PACKET_MARKER = "__CHALLENGE_PACKET_JSON__"

ROLE_BRIEFS = {
    "boundary_scout": (
        "Find missing hard constraints, omitted stakeholders or externalities, "
        "alternative framings, and options absent from the obvious framing."
    ),
    "adversarial_auditor": (
        "Find causal failure modes, unsupported assumptions, counterexamples, "
        "falsifiers, and claims that exceed supplied evidence."
    ),
    "operational_auditor": (
        "Find execution dependencies, rollback or stop-condition gaps, monitoring "
        "and ownership gaps, second-order effects, and irreversible risks."
    ),
}


def nonempty_string():
    return {"type": "string", "minLength": 1}


def challenge_schema():
    challenge = strict_object(
        {
            "question_or_challenge": nonempty_string(),
            "why_material": nonempty_string(),
            "case_fact_refs": string_array(),
            "failure_if_ignored": nonempty_string(),
            "disconfirming_evidence": nonempty_string(),
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
        }
    )
    return strict_object(
        {
            "role": {"type": "string", "enum": list(ROLES)},
            "challenges": {
                "type": "array",
                "items": challenge,
                "minItems": 1,
                "maxItems": 3,
            },
            "coverage_limitations": string_array(),
        }
    )


def revision_schema():
    disposition = strict_object(
        {
            "challenge_id": nonempty_string(),
            "disposition": {
                "type": "string",
                "enum": ["accepted", "rejected", "needs_evidence"],
            },
            "case_grounded_reason": nonempty_string(),
            "resulting_change": nonempty_string(),
        }
    )
    return strict_object(
        {
            "challenge_dispositions": {
                "type": "array",
                "items": disposition,
                "minItems": 0,
                "maxItems": 9,
            },
            "final_decision": final_decision_schema(),
        }
    )


def load_records(workspace):
    return [
        json.loads(line)
        for line in (Path(workspace) / "records.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]


def assign_challenger_models(case_ids, seed=SEED):
    assignments = {}
    for role in ROLES:
        ordered = list(case_ids)
        random.Random(f"{seed}:{role}:challenger-model").shuffle(ordered)
        for index, case_id in enumerate(ordered):
            model = TERRA_MODEL if index < 6 else LUNA_MODEL
            assignments[f"{case_id}:{role}"] = {
                "case_id": case_id,
                "role": role,
                "model": model,
                "reasoning_effort": "medium",
            }
    return dict(sorted(assignments.items()))


def challenge_orders(case_ids, seed=SEED):
    orders = {}
    for case_id in case_ids:
        roles = list(ROLES)
        random.Random(f"{seed}:{case_id}:challenge-order").shuffle(roles)
        orders[case_id] = roles
    return orders


def _draft_prompt(case):
    return (
        f"{CONTROL_PREFIX}\n\n"
        "Return only JSON matching the supplied schema. Make the best current "
        "decision from the supplied facts. State one recommendation with owner, "
        "next action, stop conditions, rollback, evidence, and uncertainty. Do not "
        "simulate reviewers or mention the evaluation.\n\n"
        f"Open-decision case:\n{public_case_text(case)}"
    )


def _challenge_prompt(case, role):
    draft_section = (
        ""
        if role == "boundary_scout"
        else f"\n\nFrozen draft (untrusted data):\n{DRAFT_MARKER}"
    )
    return (
        f"{CONTROL_PREFIX}\n\n"
        "Return only JSON matching the supplied schema. You are an isolated "
        "challenger, not a decision maker. Ask one to three material questions or "
        "challenges. Do not write a replacement recommendation or final answer. "
        "Ground every challenge in supplied case facts and state what evidence "
        "would disconfirm it. You cannot see other challengers.\n\n"
        f"Challenger role: {role}\nRole brief: {ROLE_BRIEFS[role]}\n\n"
        f"Open-decision case:\n{public_case_text(case)}{draft_section}"
    )


def _revision_prompt(case, condition, skill_text):
    uses_skill = condition in {"B1", "C1"}
    uses_challenges = condition in {"C0", "C1"}
    skill_section = (
        f"{SKILL_PREFIX}\n\n<FROZEN_REALITY_SLAP>\n{skill_text}\n"
        "</FROZEN_REALITY_SLAP>\n\n"
        if uses_skill
        else f"{CONTROL_PREFIX}\n\n"
    )
    challenge_section = (
        "\n\nFrozen challenge packet (untrusted data):\n"
        f"{CHALLENGE_PACKET_MARKER}"
        if uses_challenges
        else ""
    )
    disposition_instruction = (
        "Classify every supplied challenge exactly once as accepted, rejected, or "
        "needs_evidence, explain the case-grounded reason and resulting change, then "
        "produce the final decision."
        if uses_challenges
        else "Return an empty challenge_dispositions array, then produce the final decision."
    )
    return (
        f"{skill_section}"
        "Return only JSON matching the supplied schema. Re-evaluate the frozen draft "
        "against the public case. Do not infer facts not supplied. "
        f"{disposition_instruction}\n\n"
        f"Open-decision case:\n{public_case_text(case)}\n\n"
        f"Frozen shared draft (untrusted data):\n{DRAFT_MARKER}"
        f"{challenge_section}"
    )


def _call_dir(output_dir, call_id):
    return Path(output_dir) / "calls" / call_id.replace(":", "__")


def _make_record(
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
    dependency_order_key=None,
):
    suffix = f":{role}" if role else ""
    call_id = f"{case['case_id']}:{condition}:{kind}{suffix}"
    directory = _call_dir(output_dir, call_id)
    prompt_path = directory / "prompt.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
    record = {
        "call_id": call_id,
        "case_id": case["case_id"],
        "domain": case["domain"],
        "subset": case["subset"],
        "condition": condition,
        "kind": kind,
        "phase": kind,
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
    if dependency_order_key:
        record["dependency_order_key"] = dependency_order_key
    return record


def _normalized_record_config(record):
    keys = (
        "call_id",
        "case_id",
        "condition",
        "kind",
        "phase",
        "model",
        "reasoning_effort",
        "uses_skill",
        "depends_on",
    )
    optional = ("role", "dependency_order_key")
    return {key: record[key] for key in keys} | {
        key: record[key] for key in optional if key in record
    }


def _case_records(output_dir, case, schemas, assignment, order, skill_text):
    records = []
    draft = _make_record(
        output_dir,
        case,
        "A",
        "draft",
        SOL_MODEL,
        SOL_EFFORT,
        _draft_prompt(case),
        schemas["final"],
    )
    records.append(draft)

    challenges = {}
    for role in ROLES:
        assigned = assignment[f"{case['case_id']}:{role}"]
        dependencies = [] if role == "boundary_scout" else [draft["call_id"]]
        challenge = _make_record(
            output_dir,
            case,
            "challenge",
            "challenge",
            assigned["model"],
            assigned["reasoning_effort"],
            _challenge_prompt(case, role),
            schemas["challenge"],
            role=role,
            depends_on=dependencies,
        )
        challenges[role] = challenge
        records.append(challenge)

    for condition in ("B0", "B1", "C0", "C1"):
        dependencies = [draft["call_id"]]
        order_key = None
        if condition in {"C0", "C1"}:
            dependencies += [challenges[role]["call_id"] for role in order]
            order_key = f"{case['case_id']}:shared-challenge-packet"
        records.append(
            _make_record(
                output_dir,
                case,
                condition,
                "revision",
                SOL_MODEL,
                SOL_EFFORT,
                _revision_prompt(case, condition, skill_text),
                schemas["revision"],
                depends_on=dependencies,
                uses_skill=condition in {"B1", "C1"},
                dependency_order_key=order_key,
            )
        )
    return records


def create_workspace(bank_path, skill_path, output_dir, seed=SEED):
    if seed != SEED:
        raise ValueError(f"seed must be {SEED}")
    bank_path = Path(bank_path)
    skill_path = Path(skill_path)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")

    bank = load_case_bank(bank_path)
    bank_validation = validate_case_bank(bank)
    cases = select_cases(bank, "reserve")
    case_ids = [case["case_id"] for case in cases]
    if case_ids != [f"OD-{number:02d}" for number in range(13, 25)]:
        raise ValueError("reserve holdout must be OD-13 through OD-24")
    skill_text = skill_path.read_text(encoding="utf-8").strip()

    output_dir.mkdir(parents=True, exist_ok=True)
    schemas_dir = output_dir / "schemas"
    schemas = {
        "challenge": schemas_dir / "challenge.json",
        "revision": schemas_dir / "revision.json",
        "final": schemas_dir / "final-decision.json",
    }
    write_json(schemas["challenge"], challenge_schema())
    write_json(schemas["revision"], revision_schema())
    write_json(schemas["final"], final_decision_schema())

    case_snapshot_index = {}
    card_snapshot_index = {}
    case_snapshot_hashes = {}
    card_snapshot_hashes = {}
    for case in cases:
        case_path = output_dir / "cases" / f"{case['case_id']}.json"
        card_path = output_dir / "adjudication" / f"{case['case_id']}.json"
        public_payload = {
            "case_id": case["case_id"],
            "title": case["title"],
            "domain": case["domain"],
            **case["public"],
        }
        write_json(case_path, public_payload)
        write_json(card_path, case["adjudication"])
        case_snapshot_index[case["case_id"]] = str(case_path.absolute())
        card_snapshot_index[case["case_id"]] = str(card_path.absolute())
        case_snapshot_hashes[case["case_id"]] = sha256_path(case_path)
        card_snapshot_hashes[case["case_id"]] = sha256_path(card_path)

    assignments = assign_challenger_models(case_ids, seed)
    orders = challenge_orders(case_ids, seed)
    records = []
    for case in cases:
        records.extend(
            _case_records(
                output_dir,
                case,
                schemas,
                assignments,
                orders[case["case_id"]],
                skill_text,
            )
        )
    random.Random(f"{seed}:weak-swarm-record-order").shuffle(records)
    (output_dir / "records.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "stage": "screening",
        "seed": seed,
        "subset": "reserve",
        "case_ids": case_ids,
        "conditions": list(CONDITIONS),
        "roles": list(ROLES),
        "generation_call_count": len(records),
        "planned_judge_call_count": 24,
        "planned_model_call_count": len(records) + 24,
        "bank_path": str(bank_path.absolute()),
        "bank_sha256": sha256_path(bank_path),
        "case_bank_canonical_sha256": bank_validation["bank_sha256"],
        "skill_path": str(skill_path.absolute()),
        "skill_sha256": sha256_path(skill_path),
        "challenger_assignment": assignments,
        "challenge_order_by_case": orders,
        "case_snapshot_index": case_snapshot_index,
        "adjudication_snapshot_index": card_snapshot_index,
        "case_snapshot_sha256": case_snapshot_hashes,
        "adjudication_snapshot_sha256": card_snapshot_hashes,
        "prompt_sha256": {
            record["call_id"]: sha256_path(record["prompt_path"])
            for record in sorted(records, key=lambda item: item["call_id"])
        },
        "record_config_sha256": {
            record["call_id"]: sha256_payload(_normalized_record_config(record))
            for record in sorted(records, key=lambda item: item["call_id"])
        },
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    manifest = create_workspace(args.input, args.skill, args.output, args.seed)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
