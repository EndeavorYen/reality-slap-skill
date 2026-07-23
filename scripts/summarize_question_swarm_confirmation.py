#!/usr/bin/env python3
"""Aggregate H-versus-S quality and dual cost gates."""

import argparse
import collections
import json
from pathlib import Path

from create_question_swarm_confirmation_workspace import load_records
from create_weak_challenge_swarm_judging import (
    CRITICAL_FLAGS,
    validate_judge_payload,
)
from question_swarm_common import (
    break_even_multiplier,
    usage_totals,
    weighted_tokens,
)
from run_open_decision_debate_experiment import load_jsonl, response_status
from summarize_weak_challenge_swarm_experiment import aggregate_candidate


CONDITIONS = ("H", "S")
GUARDRAILS = (
    "fabricated_fact",
    "missed_hard_constraint",
    "unsafe_irreversible_action",
)


def _decode_judges(judge_records):
    by_case_condition = collections.defaultdict(list)
    for record in judge_records:
        payload = json.loads(
            Path(record["output_path"]).read_text(encoding="utf-8")
        )
        validate_judge_payload(record, payload)
        evaluations = {item["label"]: item for item in payload["evaluations"]}
        for label, condition in record["label_to_condition"].items():
            by_case_condition[(record["case_id"], condition)].append(
                evaluations[label]
            )
    case_results = {}
    matches = 0
    decisions = 0
    for case_id in sorted({key[0] for key in by_case_condition}):
        case_results[case_id] = {}
        for condition in CONDITIONS:
            items = by_case_condition[(case_id, condition)]
            if len(items) != 2:
                raise ValueError(
                    f"expected two judges for {case_id}:{condition}"
                )
            candidate = aggregate_candidate(items)
            case_results[case_id][condition] = candidate
            matches += candidate["agreement"]["matches"]
            decisions += candidate["agreement"]["decisions"]
    return (
        case_results,
        round(matches / decisions, 6) if decisions else 0.0,
    )


def _quality_metrics(case_results, agreement):
    h_burden = sum(case["H"]["defect_burden"] for case in case_results.values())
    s_burden = sum(case["S"]["defect_burden"] for case in case_results.values())
    outcomes = collections.Counter()
    paired = {}
    for case_id, case in case_results.items():
        delta = case["S"]["defect_burden"] - case["H"]["defect_burden"]
        outcome = "better" if delta < 0 else "worse" if delta > 0 else "same"
        outcomes[outcome] += 1
        paired[case_id] = {
            "h_burden": case["H"]["defect_burden"],
            "s_burden": case["S"]["defect_burden"],
            "delta": delta,
            "outcome": outcome,
        }
    guardrails = {}
    regressions = []
    for field in ("fatal_errors", *GUARDRAILS):
        if field == "fatal_errors":
            h_count = sum(
                case["H"]["fatal_error_count"] for case in case_results.values()
            )
            s_count = sum(
                case["S"]["fatal_error_count"] for case in case_results.values()
            )
        else:
            h_count = sum(
                int(case["H"]["critical_flags"][field])
                for case in case_results.values()
            )
            s_count = sum(
                int(case["S"]["critical_flags"][field])
                for case in case_results.values()
            )
        guardrails[field] = {"H": h_count, "S": s_count}
        if s_count > h_count:
            regressions.append(field)
    h_score = sum(
        case["H"]["mean_score"] for case in case_results.values()
    ) / len(case_results)
    s_score = sum(
        case["S"]["mean_score"] for case in case_results.values()
    ) / len(case_results)
    checks = {
        "burden_noninferiority_delta_at_most_2": s_burden - h_burden <= 2,
        "nonworse_cases_at_least_6": outcomes["same"] + outcomes["better"] >= 6,
        "no_guardrail_regression": not regressions,
        "mean_score_delta_at_least_minus_0_25": s_score - h_score >= -0.25,
        "agreement_at_least_0_85": agreement >= 0.85,
    }
    return {
        "h_burden": h_burden,
        "s_burden": s_burden,
        "burden_delta": s_burden - h_burden,
        "better_cases": outcomes["better"],
        "worse_cases": outcomes["worse"],
        "same_cases": outcomes["same"],
        "nonworse_cases": outcomes["same"] + outcomes["better"],
        "h_mean_score": round(h_score, 6),
        "s_mean_score": round(s_score, 6),
        "mean_score_delta": round(s_score - h_score, 6),
        "agreement": agreement,
        "guardrails": guardrails,
        "regressions": regressions,
        "paired": paired,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _cost_metrics(records, luna_to_terra=None, sol_to_terra=None):
    questions = {
        condition: [
            record
            for record in records
            if record["kind"] == "question"
            and record["condition"] == condition
        ]
        for condition in ("H", "S")
    }
    revisions = {
        condition: [
            record
            for record in records
            if record["kind"] == "revision"
            and record["condition"] == condition
        ]
        for condition in ("B1", "H", "S")
    }
    usage = {
        "questions": {
            condition: usage_totals(items)
            for condition, items in questions.items()
        },
        "revisions": {
            condition: usage_totals(items)
            for condition, items in revisions.items()
        },
    }
    h_q = weighted_tokens(usage["questions"]["H"])
    s_q = weighted_tokens(usage["questions"]["S"])
    b1_r = weighted_tokens(usage["revisions"]["B1"])
    h_r = weighted_tokens(usage["revisions"]["H"])
    s_r = weighted_tokens(usage["revisions"]["S"])
    complete = all(
        item["complete"]
        for group in usage.values()
        for item in group.values()
    )
    h_increment = max(0, h_r - b1_r) if complete else None
    s_increment = max(0, s_r - b1_r) if complete else None
    rate_complete = luna_to_terra is not None and sol_to_terra is not None
    if complete and rate_complete:
        h_challenger = h_q
        s_challenger = s_q * luna_to_terra
        h_loop = h_challenger + h_increment * sol_to_terra
        s_loop = s_challenger + s_increment * sol_to_terra
        challenger_ratio = s_challenger / h_challenger if h_challenger else None
        loop_ratio = s_loop / h_loop if h_loop else None
    else:
        h_challenger = s_challenger = h_loop = s_loop = None
        challenger_ratio = loop_ratio = None
    sensitivity = {}
    if complete and s_q:
        for sol_ratio in (0.25, 0.5, 1.0, 2.0):
            numerator = (
                0.85 * (h_q + h_increment * sol_ratio)
                - s_increment * sol_ratio
            )
            sensitivity[str(sol_ratio)] = round(max(0, numerator / s_q), 6)
    checks = {
        "usage_complete": complete,
        "authoritative_rate_card_available": rate_complete,
        "challenger_ratio_at_most_0_70": (
            challenger_ratio is not None and challenger_ratio <= 0.7
        ),
        "critique_loop_ratio_at_most_0_85": (
            loop_ratio is not None and loop_ratio <= 0.85
        ),
    }
    return {
        "usage": usage,
        "weighted_tokens": {
            "h_questions": h_q,
            "s_questions": s_q,
            "b1_revision": b1_r,
            "h_revision": h_r,
            "s_revision": s_r,
            "h_review_increment": h_increment,
            "s_review_increment": s_increment,
        },
        "rate_card": {
            "luna_to_terra_unit_price_ratio": luna_to_terra,
            "sol_to_terra_unit_price_ratio": sol_to_terra,
            "authoritative": rate_complete,
        },
        "priced_cost": {
            "h_challenger": h_challenger,
            "s_challenger": s_challenger,
            "h_critique_loop": h_loop,
            "s_critique_loop": s_loop,
            "challenger_ratio_s_vs_h": round(challenger_ratio, 6)
            if challenger_ratio is not None
            else None,
            "critique_loop_ratio_s_vs_h": round(loop_ratio, 6)
            if loop_ratio is not None
            else None,
        },
        "challenger_break_even": break_even_multiplier(
            usage["questions"]["S"],
            usage["questions"]["H"],
            target_ratio=0.7,
        ),
        "max_luna_to_terra_ratio_for_loop_gate_by_sol_ratio": sensitivity,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _verdict(complete, quality, cost):
    if not complete or not cost["checks"]["usage_complete"]:
        return "incomplete"
    if quality["agreement"] < 0.85:
        return "inconclusive-evaluator-instability"
    if quality["regressions"]:
        return "safety-regression"
    if not cost["checks"]["authoritative_rate_card_available"]:
        return "price-unresolved"
    if quality["passed"] and cost["passed"]:
        return "green-command-candidate"
    if quality["passed"]:
        return "quality-only-cost-fail"
    if cost["passed"]:
        return "cost-only-quality-fail"
    return "quality-and-cost-fail"


def summarize_confirmation(
    workspace,
    luna_to_terra=None,
    sol_to_terra=None,
):
    workspace = Path(workspace)
    manifest = json.loads(
        (workspace / "manifest.json").read_text(encoding="utf-8")
    )
    records = load_records(workspace)
    judges = load_jsonl(workspace / "judge-records.jsonl")
    all_records = records + judges
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
            "verdict": "incomplete",
        }
    case_results, agreement = _decode_judges(judges)
    quality = _quality_metrics(case_results, agreement)
    cost = _cost_metrics(
        records,
        luna_to_terra=luna_to_terra,
        sol_to_terra=sol_to_terra,
    )
    return {
        "experiment_id": manifest["experiment_id"],
        "stage": "confirmation",
        "complete": True,
        "selected_arm": manifest["selected_arm"],
        "case_ids": manifest["case_ids"],
        "quality": quality,
        "cost": cost,
        "verdict": _verdict(True, quality, cost),
        "claim_boundary": (
            "Internal eight-case holdout; monetary cost remains unresolved unless "
            "an authoritative relative rate card is supplied."
        ),
    }


def render_markdown(summary):
    quality = summary.get("quality", {})
    cost = summary.get("cost", {})
    weighted = cost.get("weighted_tokens", {})
    lines = [
        "# Cost-Bounded Question Swarm Result",
        "",
        f"- Verdict: `{summary['verdict']}`",
        f"- Complete evidence: `{str(summary.get('complete', False)).lower()}`",
    ]
    if not summary.get("complete"):
        lines.extend(
            [
                f"- Incomplete calls: `{len(summary.get('incomplete_call_ids', []))}`",
                "",
            ]
        )
        return "\n".join(lines) + "\n"
    lines.extend(
        [
            f"- Selected small arm: `{summary['selected_arm']}`",
            "",
            "## Quality",
            "",
            f"- H defect burden: `{quality['h_burden']}`",
            f"- S defect burden: `{quality['s_burden']}`",
            f"- Paired cases: `{quality['better_cases']} better / "
            f"{quality['worse_cases']} worse / {quality['same_cases']} same`",
            f"- Mean score delta (S−H): `{quality['mean_score_delta']:+.3f}/21`",
            f"- Raw checklist agreement: `{quality['agreement'] * 100:.1f}%`",
            f"- Guardrail regressions: `{', '.join(quality['regressions']) or 'none'}`",
            "",
            "## Measured usage",
            "",
            "| Work | Weighted tokens |",
            "| --- | ---: |",
            f"| Terra-high questions | {weighted['h_questions']} |",
            f"| Luna-low swarm questions | {weighted['s_questions']} |",
            f"| Sol B1 revision | {weighted['b1_revision']} |",
            f"| Sol H revision | {weighted['h_revision']} |",
            f"| Sol S revision | {weighted['s_revision']} |",
            "",
            "Weighted tokens are input + output + reasoning-output tokens. They "
            "are measured usage, not dollars.",
            "",
            "## Cost boundary",
            "",
            f"- Maximum Luna/Terra unit-price ratio for the 70% challenger gate: "
            f"`{cost['challenger_break_even']['max_small_to_high_unit_price_ratio']}`",
            "- Monetary verdict remains `price-unresolved` without an authoritative "
            "relative model rate card.",
            "",
            "## Claim boundary",
            "",
            summary["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--luna-to-terra-price-ratio", type=float)
    parser.add_argument("--sol-to-terra-price-ratio", type=float)
    parser.add_argument("--output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()
    summary = summarize_confirmation(
        args.workspace,
        luna_to_terra=args.luna_to_terra_price_ratio,
        sol_to_terra=args.sol_to_terra_price_ratio,
    )
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    if args.markdown_output:
        Path(args.markdown_output).write_text(
            render_markdown(summary),
            encoding="utf-8",
        )
    print(text, end="")


if __name__ == "__main__":
    main()
