#!/usr/bin/env python3
"""Summarize question-only H/S2/S4 screening and select a provisional arm."""

import argparse
import json
from pathlib import Path

from create_question_swarm_screening_workspace import load_records
from question_swarm_common import (
    break_even_multiplier,
    credit_cost,
    load_credit_rate_card,
    usage_totals,
    weighted_tokens,
)
from run_open_decision_debate_experiment import (
    load_jsonl,
    response_status,
    validate_payload,
)


CONDITIONS = ("H", "S2", "S4")


def validate_question_judge(record, payload):
    schema = json.loads(Path(record["schema_path"]).read_text(encoding="utf-8"))
    validate_payload(payload, schema)
    if payload["case_id"] != record["case_id"]:
        raise ValueError("question judge case_id mismatch")
    evaluations = {
        item["packet_label"]: item for item in payload["packet_evaluations"]
    }
    if set(evaluations) != set(record["packet_labels"]):
        raise ValueError("question judge must evaluate every packet once")
    if len(evaluations) != len(payload["packet_evaluations"]):
        raise ValueError("question judge contains duplicate packet labels")
    for label, evaluation in evaluations.items():
        expected = record["question_ids_by_packet"][label]
        observed = [item["question_id"] for item in evaluation["questions"]]
        if observed != expected or len(set(observed)) != len(expected):
            raise ValueError("question judge must evaluate every question in order")
        for item in evaluation["questions"]:
            if len(set(item["matched_item_ids"])) != len(item["matched_item_ids"]):
                raise ValueError("matched checklist item IDs must be unique")
            if item["duplicate_of"] == item["question_id"]:
                raise ValueError("a question cannot duplicate itself")
    return payload


def _arm_metrics(judge_records):
    arm_data = {
        condition: {
            "covered": set(),
            "fatal": set(),
            "question_count": 0,
            "reviewable_count": 0,
            "duplicate_count": 0,
        }
        for condition in CONDITIONS
    }
    for record in judge_records:
        payload = json.loads(
            Path(record["output_path"]).read_text(encoding="utf-8")
        )
        validate_question_judge(record, payload)
        for packet in payload["packet_evaluations"]:
            condition = record["packet_label_to_condition"][packet["packet_label"]]
            data = arm_data[condition]
            for question in packet["questions"]:
                data["question_count"] += 1
                data["reviewable_count"] += int(question["reviewable"])
                data["duplicate_count"] += int(bool(question["duplicate_of"]))
                for item_id in question["matched_item_ids"]:
                    key = (record["case_id"], item_id)
                    data["covered"].add(key)
                    if item_id.startswith("FE-"):
                        data["fatal"].add(key)
    result = {}
    for condition, data in arm_data.items():
        count = data["question_count"]
        result[condition] = {
            "unique_hidden_item_coverage": len(data["covered"]),
            "fatal_item_coverage": len(data["fatal"]),
            "question_count": count,
            "reviewable_count": data["reviewable_count"],
            "reviewable_fraction": round(data["reviewable_count"] / count, 6)
            if count
            else 0.0,
            "duplicate_count": data["duplicate_count"],
            "duplicate_fraction": round(data["duplicate_count"] / count, 6)
            if count
            else 0.0,
            "_covered": data["covered"],
            "_fatal": data["fatal"],
        }
    return result


def select_screening_arm(
    metrics,
    luna_to_terra_price_ratio=None,
    rate_card=None,
):
    high = metrics["H"]
    authoritative = rate_card is not None
    terra_rates = (
        rate_card["models"]["gpt-5.6-terra"] if authoritative else None
    )
    luna_rates = (
        rate_card["models"]["gpt-5.6-luna"] if authoritative else None
    )
    eligible = {}
    for condition in ("S2", "S4"):
        item = metrics[condition]
        coverage_ratio = (
            item["unique_hidden_item_coverage"]
            / high["unique_hidden_item_coverage"]
            if high["unique_hidden_item_coverage"]
            else 1.0
        )
        missed_fatal = len(high["_fatal"] - item["_fatal"])
        quality_pass = coverage_ratio >= 0.9 and missed_fatal <= 1
        small_tokens = weighted_tokens(item["usage"])
        high_tokens = weighted_tokens(high["usage"])
        if authoritative:
            high_credits = credit_cost(high["usage"], terra_rates)
            small_credits = credit_cost(item["usage"], luna_rates)
            cost_ratio = (
                small_credits / high_credits if high_credits else None
            )
        else:
            high_credits = small_credits = None
            cost_ratio = (
                luna_to_terra_price_ratio * small_tokens / high_tokens
                if luna_to_terra_price_ratio is not None
                and small_tokens is not None
                and high_tokens
                else None
            )
        cost_pass = cost_ratio is not None and cost_ratio <= 0.7
        eligible[condition] = {
            "coverage_ratio_vs_h": round(coverage_ratio, 6),
            "fatal_items_h_found_but_arm_missed": missed_fatal,
            "quality_pass": quality_pass,
            "challenger_cost_ratio_vs_h": round(cost_ratio, 6)
            if cost_ratio is not None
            else None,
            "high_challenger_credits": high_credits,
            "small_challenger_credits": small_credits,
            "cost_pass": cost_pass,
            "break_even": break_even_multiplier(
                item["usage"],
                high["usage"],
                target_ratio=0.7,
                reference_rates=terra_rates,
            ),
        }
    quality_candidates = [
        condition
        for condition in ("S2", "S4")
        if eligible[condition]["quality_pass"]
    ]
    if not quality_candidates:
        return {
            "selected_arm": None,
            "verdict": "small-swarm-not-quality-effective",
            "arms": eligible,
        }
    if authoritative or luna_to_terra_price_ratio is not None:
        candidates = [
            condition
            for condition in quality_candidates
            if eligible[condition]["cost_pass"]
        ]
        if not candidates:
            return {
                "selected_arm": None,
                "verdict": "small-swarm-not-cost-effective",
                "arms": eligible,
            }
    else:
        candidates = quality_candidates
    candidates.sort(
        key=lambda condition: (
            eligible[condition]["small_challenger_credits"]
            if authoritative
            else weighted_tokens(metrics[condition]["usage"]),
            0 if condition == "S2" else 1,
        )
    )
    selected = candidates[0]
    return {
        "selected_arm": selected,
        "verdict": "screening-pass"
        if authoritative or luna_to_terra_price_ratio is not None
        else "price-unresolved-provisional-selection",
        "arms": eligible,
    }


def summarize_screening(
    workspace,
    luna_to_terra_price_ratio=None,
    rate_card=None,
):
    workspace = Path(workspace)
    manifest = json.loads(
        (workspace / "manifest.json").read_text(encoding="utf-8")
    )
    generation_records = load_records(workspace)
    judge_records = load_jsonl(workspace / "judge-records.jsonl")
    all_records = generation_records + judge_records
    incomplete = [
        record["call_id"]
        for record in all_records
        if response_status(record) != "complete"
    ]
    if incomplete:
        return {
            "experiment_id": manifest["experiment_id"],
            "complete": False,
            "incomplete_call_ids": sorted(incomplete),
            "gate": {"verdict": "incomplete", "selected_arm": None},
        }
    metrics = _arm_metrics(judge_records)
    for condition in CONDITIONS:
        question_records = [
            record
            for record in generation_records
            if record["kind"] == "question"
            and record["condition"] == condition
        ]
        metrics[condition]["usage"] = usage_totals(question_records)
    selection = select_screening_arm(
        metrics,
        luna_to_terra_price_ratio=luna_to_terra_price_ratio,
        rate_card=rate_card,
    )
    public_metrics = {}
    for condition, item in metrics.items():
        public_metrics[condition] = {
            key: value
            for key, value in item.items()
            if not key.startswith("_")
        }
    return {
        "experiment_id": manifest["experiment_id"],
        "stage": "screening",
        "complete": True,
        "case_ids": manifest["case_ids"],
        "price_assumption": {
            "luna_to_terra_unit_price_ratio": luna_to_terra_price_ratio,
            "authoritative_rate_card_available": (
                rate_card is not None
            ),
            "rate_card_source_url": (
                rate_card["source_url"] if rate_card else None
            ),
            "rate_card_retrieved_at": (
                rate_card["retrieved_at"] if rate_card else None
            ),
        },
        "arms": public_metrics,
        "gate": selection,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--luna-to-terra-price-ratio", type=float)
    parser.add_argument("--rate-card")
    parser.add_argument("--output")
    args = parser.parse_args()
    summary = summarize_screening(
        args.workspace,
        luna_to_terra_price_ratio=args.luna_to_terra_price_ratio,
        rate_card=(
            load_credit_rate_card(args.rate_card)
            if args.rate_card
            else None
        ),
    )
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
