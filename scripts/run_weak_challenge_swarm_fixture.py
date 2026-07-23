#!/usr/bin/env python3
"""Exercise the complete weak-challenge-swarm pipeline without model calls."""

import argparse
import itertools
import json
from pathlib import Path

from create_weak_challenge_swarm_judging import (
    CRITICAL_FLAGS,
    DIMENSIONS,
    create_judge_records,
)
from create_weak_challenge_swarm_workspace import ROLES, create_workspace, load_records
from run_open_decision_debate_experiment import (
    audit_workspace,
    expected_challenge_ids,
)
from summarize_weak_challenge_swarm_experiment import summarize


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"
MODES = (
    "green",
    "amber",
    "not-supported",
    "safety-regression",
    "evaluator-instability",
    "incomplete",
    "invalid-challenge",
    "rs-over-rejection",
)


def _write(record, payload):
    path = Path(record["output_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _final_payload(label):
    return {
        "recommendation": f"Choose the bounded {label} path.",
        "accepted_claims": ["The case supports a reversible step."],
        "rejected_claims": ["An irreversible rollout is unsupported."],
        "residual_dissent": ["Outcome magnitude remains uncertain."],
        "decision_owner": "Named owner",
        "next_action": "Run the bounded step.",
        "stop_conditions": ["Stop if the supplied threshold fails."],
        "rollback_or_revision_path": "Return to the prior state.",
        "change_evidence": ["Measured evidence beyond the supplied uncertainty."],
        "known_facts": ["A supplied case fact."],
        "inferences": ["A reversible step limits downside."],
        "uncertainties": ["Outcome magnitude."],
    }


def _challenge_payload(role):
    return {
        "role": role,
        "challenges": [
            {
                "question_or_challenge": f"What material issue did {role} find?",
                "why_material": "It can change the safe action.",
                "case_fact_refs": ["facts[0]"],
                "failure_if_ignored": "The decision may miss a hard constraint.",
                "disconfirming_evidence": "Direct evidence that the constraint is met.",
                "severity": "high",
            }
        ],
        "coverage_limitations": ["No evidence outside the supplied case."],
    }


def _complete_generation(workspace, mode):
    records = load_records(workspace)
    records_by_id = {record["call_id"]: record for record in records}
    manifest = json.loads((Path(workspace) / "manifest.json").read_text(encoding="utf-8"))
    for case_id in manifest["case_ids"]:
        case_records = [record for record in records if record["case_id"] == case_id]
        draft = next(record for record in case_records if record["condition"] == "A")
        _write(draft, _final_payload("A"))
        for role in ROLES:
            record = next(
                item
                for item in case_records
                if item["kind"] == "challenge" and item["role"] == role
            )
            payload = _challenge_payload(role)
            if mode == "invalid-challenge" and case_id == "OD-13" and role == "boundary_scout":
                payload["role"] = "adversarial_auditor"
            _write(record, payload)
        for condition in ("B0", "B1", "C0", "C1"):
            record = next(item for item in case_records if item["condition"] == condition)
            challenge_ids = expected_challenge_ids(record, records_by_id, manifest)
            _write(
                record,
                {
                    "challenge_dispositions": [
                        {
                            "challenge_id": challenge_id,
                            "disposition": "accepted",
                            "case_grounded_reason": "The challenge maps to supplied facts.",
                            "resulting_change": "Added a bounded safeguard.",
                        }
                        for challenge_id in challenge_ids
                    ],
                    "final_decision": _final_payload(condition),
                },
            )
    return records


def _condition_covered(mode, condition, case_index):
    if condition == "B0":
        return False
    if condition == "B1":
        return False
    if condition == "C0":
        return mode == "rs-over-rejection" and case_index < 4
    if condition == "C1":
        if mode in {"green", "safety-regression"}:
            return case_index < 4
        if mode == "amber":
            return case_index < 2
        return False
    return False


def _judge_payload(record, mode, judge_index, case_index):
    evaluations = []
    for label in record["candidate_labels"]:
        condition = record["label_to_condition"][label]
        covered = _condition_covered(mode, condition, case_index)
        invert = mode == "evaluator-instability" and judge_index == 1
        must_cover = []
        for index, item_id in enumerate(record["checklist_item_ids"]["must_cover"]):
            value = covered if index == 0 else True
            if invert:
                value = not value
            must_cover.append(
                {
                    "item_id": item_id,
                    "covered": value,
                    "explanation": "Fixture coverage decision.",
                }
            )
        closure = [
            {
                "item_id": item_id,
                "satisfied": not invert,
                "explanation": "Fixture closure decision.",
            }
            for item_id in record["checklist_item_ids"]["closure"]
        ]
        fatal_errors = [
            {
                "item_id": item_id,
                "present": invert,
                "explanation": "Fixture fatal-error decision.",
            }
            for item_id in record["checklist_item_ids"]["fatal_errors"]
        ]
        flags = {flag: invert for flag in CRITICAL_FLAGS}
        if (
            mode == "safety-regression"
            and condition == "C1"
            and case_index == 0
        ):
            flags["unsafe_irreversible_action"] = True
        scores = {dimension: 2 for dimension in DIMENSIONS}
        evaluations.append(
            {
                "label": label,
                "must_cover": must_cover,
                "closure": closure,
                "fatal_errors": fatal_errors,
                "critical_flags": flags,
                "critical_explanations": {
                    flag: "Fixture critical-flag decision."
                    for flag in CRITICAL_FLAGS
                },
                "scores": scores,
                "total_score": 14,
                "summary": "Fixture candidate assessment.",
            }
        )
    pairs = [
        {
            "left_label": left,
            "right_label": right,
            "winner": "tie",
            "rationale": "Fixture treats the secondary pair as tied.",
        }
        for left, right in itertools.combinations(record["candidate_labels"], 2)
    ]
    return {
        "case_id": record["case_id"],
        "evaluations": evaluations,
        "pairwise_preferences": pairs,
        "ranking": list(record["candidate_labels"]),
    }


def run_fixture(output_dir, mode):
    if mode not in MODES:
        raise ValueError(f"unknown fixture mode: {mode}")
    output_dir = Path(output_dir)
    create_workspace(BANK, SKILL, output_dir, seed=20260725)
    generation_records = _complete_generation(output_dir, mode)
    if mode == "invalid-challenge":
        summary = summarize(output_dir)
        audit = audit_workspace(output_dir)
        return {
            "fixture_verdict": "invalid-challenge",
            "verdict": summary["gate"]["verdict"],
            "summary": summary,
            "audit": audit,
            "counts": {
                "generation_records": len(generation_records),
                "judge_records": 0,
            },
        }

    judge_records = create_judge_records(output_dir)
    case_index = {
        case_id: index
        for index, case_id in enumerate(
            json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))[
                "case_ids"
            ]
        )
    }
    for record in judge_records:
        judge_index = 0 if record["judge_id"] == "sol-medium" else 1
        _write(
            record,
            _judge_payload(
                record,
                mode,
                judge_index,
                case_index[record["case_id"]],
            ),
        )
    if mode == "incomplete":
        Path(judge_records[-1]["output_path"]).unlink()
    summary = summarize(output_dir)
    audit = audit_workspace(output_dir)
    return {
        "verdict": summary["gate"]["verdict"],
        "summary": summary,
        "audit": audit,
        "counts": {
            "generation_records": len(generation_records),
            "judge_records": len(judge_records),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=MODES, default="green")
    args = parser.parse_args()
    print(json.dumps(run_fixture(args.output, args.mode), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
