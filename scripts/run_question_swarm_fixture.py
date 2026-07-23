#!/usr/bin/env python3
"""Exercise the confirmation pipeline and verdicts without model calls."""

import argparse
import json
from pathlib import Path

from create_question_swarm_confirmation_judging import (
    create_confirmation_judges,
)
from create_question_swarm_confirmation_workspace import (
    create_confirmation_workspace,
    load_records,
)
from create_weak_challenge_swarm_judging import CRITICAL_FLAGS, DIMENSIONS
from summarize_question_swarm_confirmation import summarize_confirmation


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "evals" / "question-swarm-holdout-bank.json"
SKILL = ROOT / "SKILL.md"
MODES = (
    "green",
    "quality-fail",
    "cost-fail",
    "safety-regression",
    "price-unresolved",
    "evaluator-instability",
    "incomplete",
)


def _write(record, payload):
    path = Path(record["output_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _metadata(record, usage):
    path = Path(record["metadata_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "call_id": record["call_id"],
                "model": record["model"],
                "reasoning_effort": record["reasoning_effort"],
                "attempts": [
                    {
                        "attempt": 1,
                        "returncode": 0,
                        "invalid_reason": "",
                        "usage": usage,
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _usage(input_tokens, output_tokens=10, reasoning_tokens=10):
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": 0,
        "output_tokens": output_tokens,
        "reasoning_output_tokens": reasoning_tokens,
    }


def _final(label):
    return {
        "recommendation": f"Run the bounded {label} path.",
        "accepted_claims": ["A reversible test is supported."],
        "rejected_claims": ["An irreversible rollout is unsupported."],
        "residual_dissent": ["The effect size is uncertain."],
        "decision_owner": "Named owner",
        "next_action": "Run the bounded step.",
        "stop_conditions": ["Stop if the supplied threshold fails."],
        "rollback_or_revision_path": "Return to the previous state.",
        "change_evidence": ["Measured threshold evidence."],
        "known_facts": ["A supplied case fact."],
        "inferences": ["A bounded step limits downside."],
        "uncertainties": ["Outcome magnitude."],
    }


def _complete_generation(workspace, mode):
    records = load_records(workspace)
    for record in records:
        if record["kind"] == "draft":
            payload = _final("draft")
            usage = _usage(100)
        elif record["kind"] == "question":
            payload = {
                "lens": record["role"],
                "questions": [
                    {
                        "target": "A specific draft claim",
                        "question": "What supplied condition could invalidate this claim?",
                    }
                ],
            }
            if record["condition"] == "H":
                usage = _usage(1000, 100, 100)
            else:
                usage = (
                    _usage(1000, 100, 100)
                    if mode == "cost-fail"
                    else _usage(15, 5, 5)
                )
        else:
            payload = {
                "challenge_dispositions": [],
                "final_decision": _final(record["condition"]),
            }
            usage = _usage(
                100
                if record["condition"] == "B1"
                else 110
                if record["condition"] == "H"
                else 105
            )
        _write(record, payload)
        _metadata(record, usage)
    return records


def _binary_items(item_ids, decision_name, value):
    return [
        {
            "item_id": item_id,
            decision_name: value,
            "explanation": "Fixture checklist decision.",
        }
        for item_id in item_ids
    ]


def _judge_payload(record, mode, judge_index, case_index):
    evaluations = []
    for label in record["candidate_labels"]:
        condition = record["label_to_condition"][label]
        invert = mode == "evaluator-instability" and judge_index == 1
        must_cover = _binary_items(
            record["checklist_item_ids"]["must_cover"],
            "covered",
            not invert,
        )
        if mode == "quality-fail" and condition == "S" and case_index < 3:
            must_cover[0]["covered"] = False
        closure = _binary_items(
            record["checklist_item_ids"]["closure"],
            "satisfied",
            not invert,
        )
        fatal = _binary_items(
            record["checklist_item_ids"]["fatal_errors"],
            "present",
            invert,
        )
        flags = {flag: invert for flag in CRITICAL_FLAGS}
        if (
            mode == "safety-regression"
            and condition == "S"
            and case_index == 0
        ):
            flags["fabricated_fact"] = True
        scores = {dimension: 3 for dimension in DIMENSIONS}
        evaluations.append(
            {
                "label": label,
                "must_cover": must_cover,
                "closure": closure,
                "fatal_errors": fatal,
                "critical_flags": flags,
                "critical_explanations": {
                    flag: "Fixture critical-flag decision."
                    for flag in CRITICAL_FLAGS
                },
                "scores": scores,
                "total_score": 21,
                "summary": "Fixture final-decision assessment.",
            }
        )
    left, right = record["candidate_labels"]
    return {
        "case_id": record["case_id"],
        "evaluations": evaluations,
        "pairwise_preferences": [
            {
                "left_label": left,
                "right_label": right,
                "winner": "tie",
                "rationale": "Fixture pair is tied.",
            }
        ],
        "ranking": list(record["candidate_labels"]),
    }


def run_fixture(output_dir, mode):
    if mode not in MODES:
        raise ValueError(f"unknown fixture mode: {mode}")
    output_dir = Path(output_dir)
    create_confirmation_workspace(BANK, SKILL, "S2", output_dir)
    generation = _complete_generation(output_dir, mode)
    judges = create_confirmation_judges(output_dir)
    case_index = {
        case_id: index
        for index, case_id in enumerate(
            json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )["case_ids"]
        )
    }
    for record in judges:
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
        _metadata(record, _usage(50))
    if mode == "incomplete":
        Path(judges[-1]["output_path"]).unlink()
    if mode == "price-unresolved":
        summary = summarize_confirmation(output_dir)
    else:
        summary = summarize_confirmation(
            output_dir,
            luna_to_terra=1.0 if mode == "cost-fail" else 0.1,
            sol_to_terra=0.5,
        )
    return {
        "mode": mode,
        "verdict": summary["verdict"],
        "summary": summary,
        "counts": {
            "generation": len(generation),
            "judges": len(judges),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=MODES, default="green")
    args = parser.parse_args()
    print(
        json.dumps(
            run_fixture(args.output, args.mode),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
