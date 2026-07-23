#!/usr/bin/env python3
"""Run deterministic, no-model fixtures through the open-decision pipeline."""

import argparse
import json
from pathlib import Path

from create_open_decision_debate_judging import (
    CRITICAL_FLAGS,
    DIMENSIONS,
    create_conflict_queue,
    create_judge_records,
)
from create_open_decision_debate_workspace import (
    ROLES,
    STAGE2_D,
    STAGE2_E,
    STAGE2_F,
    create_stage2_records,
    create_workspace,
    load_records,
    write_json,
)
from summarize_open_decision_debate_experiment import summarize


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"
FIXTURE_MODES = {
    "green",
    "amber",
    "not-supported",
    "safety-regression",
    "evaluator-instability",
    "incomplete",
    "stage2-green",
}


def final_payload():
    return {
        "recommendation": "Run a bounded pilot with an explicit owner.",
        "accepted_claims": ["The reversible pilot fits the supplied constraints."],
        "rejected_claims": ["An irreversible full rollout lacks evidence."],
        "residual_dissent": ["The effect size remains uncertain."],
        "decision_owner": "Named decision owner",
        "next_action": "Start the bounded pilot.",
        "stop_conditions": ["Stop if the stated threshold fails."],
        "rollback_or_revision_path": "Return to the prior operating state.",
        "change_evidence": ["Validated evidence from the bounded pilot."],
        "known_facts": ["A fact supplied in the case."],
        "inferences": ["A bounded inference from the supplied facts."],
        "uncertainties": ["The production effect size is unknown."],
    }


def first_payload(role):
    return {
        "role": role,
        "recommendation": "Run a bounded pilot.",
        "claims": [
            {
                "claim": "A pilot is reversible.",
                "evidence_refs": ["reversible_action"],
                "confidence": 85,
            },
            {
                "claim": "The full rollout is not yet justified.",
                "evidence_refs": ["incomplete_information"],
                "confidence": 75,
            },
        ],
        "constraints": ["Respect the hard boundary."],
        "failure_modes": ["The pilot could miss its threshold."],
        "uncertainties": ["Effect size."],
        "falsifiers": ["The success threshold fails."],
        "reversible_test": "Run the bounded pilot.",
    }


def cross_payload(role):
    return {
        "role": role,
        "strongest_peer_point_accepted": "A reversible test reduces downside.",
        "strongest_unresolved_objection": "The effect size remains unknown.",
        "unsupported_peer_claims": ["A full rollout is guaranteed to work."],
        "update_type": "revised",
        "updated_recommendation": "Run a smaller bounded pilot.",
        "update_reason": "The supplied constraints favor reversible evidence.",
        "remaining_uncertainty": ["Production effect size."],
    }


def self_review_payload(role):
    return {
        "role": role,
        "strongest_self_critique": "The first proposal overstates the effect size.",
        "unsupported_own_claims": ["The full rollout is guaranteed to work."],
        "update_type": "revised",
        "updated_recommendation": "Run a smaller bounded pilot.",
        "update_reason": "The case supports a reversible evidence step.",
        "remaining_uncertainty": ["Production effect size."],
    }


def serial_payload(phase):
    return {
        "phase": phase,
        "recommendation": "Run a bounded pilot.",
        "supported_claims": ["The pilot is reversible."],
        "criticisms_or_changes": ["Narrow the blast radius."],
        "constraints": ["Respect the hard boundary."],
        "uncertainties": ["Effect size."],
        "next_decision": "Choose the pilot scope.",
    }


def write_generation_outputs(workspace):
    for record in load_records(workspace):
        if record.get("reused_candidate"):
            continue
        if record["kind"] in {"direct", "chair"} or (
            record["kind"] == "serial" and record["phase"] == "final"
        ):
            payload = final_payload()
        elif record["kind"] == "role":
            payload = first_payload(record["role"])
        elif record["kind"] == "cross_exam":
            payload = cross_payload(record["role"])
        elif record["kind"] == "self_review":
            payload = self_review_payload(record["role"])
        else:
            payload = serial_payload(record["phase"])
        output_path = Path(record["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def dimension_scores(total):
    remaining = total
    result = {}
    for dimension in DIMENSIONS:
        value = min(3, remaining)
        result[dimension] = value
        remaining -= value
    if remaining:
        raise ValueError(f"score is outside the 21-point rubric: {total}")
    return result


def make_judge_payload(record, scores, forced_winners=None, flagged=None):
    forced_winners = forced_winners or {}
    flagged = flagged or {}
    mapping = record["label_to_condition"]
    evaluations = []
    for label, condition in mapping.items():
        flags = {
            flag: flag in set(flagged.get(condition, []))
            for flag in CRITICAL_FLAGS
        }
        evaluations.append(
            {
                "label": label,
                "scores": dimension_scores(scores[condition]),
                "total_score": scores[condition],
                "critical_flags": flags,
                "critical_explanations": {
                    flag: (
                        "The fixture deliberately triggers this guardrail."
                        if value
                        else "No issue found in the fixture."
                    )
                    for flag, value in flags.items()
                },
                "valid_novel_insights": ["A supported and actionable insight."],
                "summary": "Fixture assessment grounded in the case.",
            }
        )
    labels = list(mapping)
    preferences = []
    for left_index, left_label in enumerate(labels):
        for right_label in labels[left_index + 1:]:
            left_condition = mapping[left_label]
            right_condition = mapping[right_label]
            pair_key = frozenset((left_condition, right_condition))
            forced = forced_winners.get(pair_key)
            if forced == "tie":
                winner = "tie"
            elif forced:
                winner = (
                    left_label if left_condition == forced else right_label
                )
            elif scores[left_condition] == scores[right_condition]:
                winner = "tie"
            else:
                winner = (
                    left_label
                    if scores[left_condition] > scores[right_condition]
                    else right_label
                )
            preferences.append(
                {
                    "left_label": left_label,
                    "right_label": right_label,
                    "winner": winner,
                    "rationale": "The selected option is more complete and actionable.",
                }
            )
    ranking = sorted(
        labels,
        key=lambda label: (-scores[mapping[label]], label),
    )
    return {
        "case_id": record["case_id"],
        "evaluations": evaluations,
        "pairwise_preferences": preferences,
        "ranking": ranking,
    }


def stage1_scores(mode, case_index):
    if mode in {"green", "stage2-green", "safety-regression", "evaluator-instability"}:
        return {
            "direct-sol": 14,
            "matched-serial-review": 15,
            "heterogeneous-debate-rs-chair": 18,
        }
    if mode == "amber":
        if case_index < 7:
            c_score, b_score = 16, 15
        elif case_index < 11:
            c_score, b_score = 15, 16
        else:
            c_score = b_score = 15
        return {
            "direct-sol": 14,
            "matched-serial-review": b_score,
            "heterogeneous-debate-rs-chair": c_score,
        }
    return {
        "direct-sol": 14,
        "matched-serial-review": 17,
        "heterogeneous-debate-rs-chair": 14,
    }


def write_stage1_judgments(workspace, mode):
    records = create_judge_records(workspace, "stage1")
    case_order = {
        case_id: index
        for index, case_id in enumerate(
            json.loads(
                (Path(workspace) / "manifest.json").read_text(encoding="utf-8")
            )["case_ids"]
        )
    }
    for index, record in enumerate(records):
        if mode == "incomplete" and index == 0:
            continue
        case_index = case_order[record["case_id"]]
        forced = {}
        if (
            mode == "evaluator-instability"
            and record["judge_id"] == "terra-high"
            and case_index < 4
        ):
            forced[
                frozenset(
                    (
                        "matched-serial-review",
                        "heterogeneous-debate-rs-chair",
                    )
                )
            ] = "matched-serial-review"
        flagged = (
            {"heterogeneous-debate-rs-chair": ["unsafe_irreversible_action"]}
            if mode == "safety-regression"
            else {}
        )
        payload = make_judge_payload(
            record,
            stage1_scores(mode, case_index),
            forced_winners=forced,
            flagged=flagged,
        )
        Path(record["output_path"]).write_text(
            json.dumps(payload) + "\n",
            encoding="utf-8",
        )


def write_human_resolutions(workspace):
    queue = create_conflict_queue(workspace)
    mappings = {
        item["conflict_id"]: item["label_to_condition"]
        for item in json.loads(
            (Path(workspace) / "human-mappings.json").read_text(encoding="utf-8")
        )["mappings"]
    }
    resolutions = []
    for conflict in queue["conflicts"]:
        mapping = mappings[conflict["conflict_id"]]
        condition_to_label = {
            condition: label for label, condition in mapping.items()
        }
        resolutions.append(
            {
                "conflict_id": conflict["conflict_id"],
                "pairwise_winner": condition_to_label[
                    "heterogeneous-debate-rs-chair"
                ],
                "resolved_critical_flags": {
                    label: {flag: False for flag in CRITICAL_FLAGS}
                    for label in mapping
                },
                "rationale": "The fixture resolution selects the stronger bounded decision.",
                "reviewer_timestamp": "2026-07-24T00:00:00Z",
            }
        )
    write_json(
        Path(workspace) / "human-adjudications.json",
        {"resolutions": resolutions},
    )


def write_stage2_judgments(workspace):
    scores = {
        "heterogeneous-debate-rs-chair": 20,
        STAGE2_D: 17,
        STAGE2_E: 17,
        STAGE2_F: 17,
    }
    for record in create_judge_records(workspace, "stage2"):
        Path(record["output_path"]).write_text(
            json.dumps(make_judge_payload(record, scores)) + "\n",
            encoding="utf-8",
        )
    create_conflict_queue(workspace)


def run_fixture(output_dir, mode="stage2-green"):
    if mode not in FIXTURE_MODES:
        raise ValueError(f"unknown fixture mode: {mode}")
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"fixture output must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    stage1 = output_dir / "stage1"
    create_workspace(BANK, SKILL, stage1, "primary", 20260724)
    write_generation_outputs(stage1)
    write_stage1_judgments(stage1, mode)
    if mode == "evaluator-instability":
        write_human_resolutions(stage1)
    result = summarize(stage1, "stage1")
    if mode == "stage2-green":
        stage2 = output_dir / "stage2"
        create_stage2_records(stage1, stage2)
        write_generation_outputs(stage2)
        write_stage2_judgments(stage2)
        result = summarize(stage2, "stage2")
    result["status"] = (
        "complete"
        if result["verdict"] != "incomplete"
        or result.get("next_action") == "run-reserve"
        else "incomplete"
    )
    result["fixture_mode"] = mode
    write_json(output_dir / "fixture-result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=sorted(FIXTURE_MODES), default="stage2-green")
    args = parser.parse_args()
    print(json.dumps(run_fixture(args.output, args.mode), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
