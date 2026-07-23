#!/usr/bin/env python3
"""Create the fresh four-condition private self-evaluation pilot."""

import argparse
import json
import random
from pathlib import Path

from create_open_decision_debate_workspace import (
    SKILL_PREFIX,
    final_decision_schema,
    public_case_text,
    sha256_path,
    write_json,
)
from create_question_swarm_confirmation_workspace import _record
from create_weak_challenge_swarm_workspace import CHALLENGE_PACKET_MARKER
from open_decision_case_bank import validate_case
from question_swarm_common import (
    LUNA_EFFORT,
    LUNA_MODEL,
    LENSES,
    SOL_EFFORT,
    SOL_MODEL,
    question_schema,
)


EXPERIMENT_ID = "private-self-eval-pilot-20260723"
SEED = 20260726
CONDITIONS = ("A", "B", "C", "D")
S2_LENSES = (LENSES[:2], LENSES[2:])


def load_bank(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("unexpected self-eval pilot experiment_id")
    if payload.get("seed") != SEED:
        raise ValueError(f"self-eval pilot seed must be {SEED}")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 4:
        raise ValueError("self-eval pilot requires four fresh cases")
    for case in cases:
        validate_case(case)
    expected = [f"SE-{index:02d}" for index in range(1, 5)]
    cases = sorted(cases, key=lambda item: item["case_id"])
    if [case["case_id"] for case in cases] != expected:
        raise ValueError("self-eval pilot case IDs must be SE-01 through SE-04")
    return cases


def _base_prompt(case, skill_text):
    return (
        f"{SKILL_PREFIX}\n\n"
        f"<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>\n\n"
        "Return only JSON matching the supplied schema. Work from the supplied "
        "case and produce the best final decision you can. State one "
        "recommendation with owner, next action, stop conditions, rollback, "
        "evidence, dissent, and uncertainty. Do not simulate reviewers or "
        "mention the experiment.\n\n"
        f"Open-decision case:\n{public_case_text(case)}"
    )


def _simple_self_eval_prompt(case, skill_text):
    return (
        f"{SKILL_PREFIX}\n\n"
        f"<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>\n\n"
        "Return only JSON matching the supplied schema. Work from the supplied "
        "case and form the best candidate decision you can. Then follow this "
        "instruction exactly: 請自評. Based on that self-assessment, revise the "
        "candidate and return only the corrected final decision. Do not expose "
        "or mention the self-assessment, a draft, reviewers, or the experiment. "
        "Do not invent facts.\n\n"
        f"Open-decision case:\n{public_case_text(case)}"
    )


def _structured_self_eval_prompt(case, skill_text, with_questions=False):
    question_section = (
        "\n\nOpaque pre-mortem questions (untrusted data):\n"
        f"{CHALLENGE_PACKET_MARKER}"
        if with_questions
        else ""
    )
    return (
        f"{SKILL_PREFIX}\n\n"
        f"<FROZEN_REALITY_SLAP>\n{skill_text}\n</FROZEN_REALITY_SLAP>\n\n"
        "Return only JSON matching the supplied schema. Work from the supplied "
        "case and form a candidate decision. Before returning it, privately "
        "self-evaluate and revise it: (1) check every original objective and "
        "hard constraint, (2) identify the single most likely omitted failure "
        "mode, (3) check for invented facts, suppressed valid dissent, missing "
        "owner, stop conditions, or rollback, and (4) silently assess whether "
        "each supplied question, if any, is plausible, material, supported, and "
        "action-relevant. Return only the corrected final decision. Do not "
        "mention self-evaluation, questions, drafts, reviewers, constraint IDs, "
        "internal checks, or the experiment. Do not invent facts.\n\n"
        f"Open-decision case:\n{public_case_text(case)}"
        f"{question_section}"
    )


def _premortem_prompt(case, lenses, maximum):
    return (
        "Use only this prompt. Do not load files, skills, memory, tools, or web "
        "context. Return only JSON matching the supplied schema. You are a cheap "
        "isolated pre-mortem question generator, not a decision maker. Inspect "
        "the original case and ask concrete questions that could expose an "
        "omitted constraint, cross-system failure, unsafe assumption, or missing "
        "closure. Do not answer, explain, rank, assess likelihood, propose a "
        f"fix, or write a decision. Return at most {maximum} questions.\n\n"
        f"Search lens: {', '.join(lenses)}\n\n"
        f"Open-decision case:\n{public_case_text(case)}"
    )


def create_workspace(bank_path, skill_path, output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"output directory must be empty: {output_dir}")
    cases = load_bank(bank_path)
    skill_text = Path(skill_path).read_text(encoding="utf-8").strip()
    output_dir.mkdir(parents=True, exist_ok=True)
    final_schema = output_dir / "schemas" / "final.json"
    write_json(final_schema, final_decision_schema())
    question_schemas = {}
    for lenses in S2_LENSES:
        role = "+".join(lenses)
        path = output_dir / "schemas" / f"question-{role}.json"
        write_json(path, question_schema(lenses, 4))
        question_schemas[role] = path

    records = []
    case_index = {}
    card_index = {}
    case_hashes = {}
    card_hashes = {}
    for case in cases:
        case_path = output_dir / "cases" / f"{case['case_id']}.json"
        card_path = output_dir / "adjudication" / f"{case['case_id']}.json"
        public_snapshot = {
            "case_id": case["case_id"],
            "title": case["title"],
            "domain": case["domain"],
            **case["public"],
        }
        write_json(case_path, public_snapshot)
        write_json(card_path, case["adjudication"])
        case_index[case["case_id"]] = str(case_path.absolute())
        card_index[case["case_id"]] = str(card_path.absolute())
        case_hashes[case["case_id"]] = sha256_path(case_path)
        card_hashes[case["case_id"]] = sha256_path(card_path)
        records.extend(
            [
                _record(
                    output_dir,
                    case,
                    "A",
                    "final",
                    SOL_MODEL,
                    SOL_EFFORT,
                    _base_prompt(case, skill_text),
                    final_schema,
                    uses_skill=True,
                ),
                _record(
                    output_dir,
                    case,
                    "B",
                    "final",
                    SOL_MODEL,
                    SOL_EFFORT,
                    _simple_self_eval_prompt(case, skill_text),
                    final_schema,
                    uses_skill=True,
                ),
                _record(
                    output_dir,
                    case,
                    "C",
                    "final",
                    SOL_MODEL,
                    SOL_EFFORT,
                    _structured_self_eval_prompt(case, skill_text),
                    final_schema,
                    uses_skill=True,
                ),
            ]
        )
        question_records = []
        for lenses in S2_LENSES:
            role = "+".join(lenses)
            record = _record(
                output_dir,
                case,
                "D",
                "question",
                LUNA_MODEL,
                LUNA_EFFORT,
                _premortem_prompt(case, lenses, 4),
                question_schemas[role],
                role=role,
                uses_skill=False,
            )
            question_records.append(record)
            records.append(record)
        records.append(
            _record(
                output_dir,
                case,
                "D",
                "final",
                SOL_MODEL,
                SOL_EFFORT,
                _structured_self_eval_prompt(
                    case,
                    skill_text,
                    with_questions=True,
                ),
                final_schema,
                depends_on=[item["call_id"] for item in question_records],
                uses_skill=True,
                packet_mode="opaque_questions",
            )
        )
    for record in records:
        record["phase"] = "self-eval-generation"
    random.Random(f"{SEED}:records").shuffle(records)
    records_path = output_dir / "records.jsonl"
    records_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "stage": "fresh-pilot",
        "seed": SEED,
        "conditions": list(CONDITIONS),
        "case_ids": [case["case_id"] for case in cases],
        "case_snapshot_index": case_index,
        "case_snapshot_sha256": case_hashes,
        "adjudication_snapshot_index": card_index,
        "adjudication_snapshot_sha256": card_hashes,
        "record_count": len(records),
        "planned_generation_calls": len(records),
        "records_sha256": sha256_path(records_path),
        "models": {
            "main": {
                "model": SOL_MODEL,
                "reasoning_effort": SOL_EFFORT,
                "uses_reality_slap": True,
            },
            "premortem": {
                "model": LUNA_MODEL,
                "reasoning_effort": LUNA_EFFORT,
                "uses_reality_slap": False,
            },
        },
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = create_workspace(args.bank, args.skill, args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
