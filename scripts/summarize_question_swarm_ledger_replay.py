#!/usr/bin/env python3
"""Aggregate five-way quality and end-to-end cost for the ledger replay."""

import argparse
import collections
import json
from pathlib import Path

from create_open_decision_debate_workspace import write_json
from create_question_swarm_confirmation_workspace import load_records
from create_weak_challenge_swarm_judging import validate_judge_payload
from question_swarm_common import credit_cost, load_credit_rate_card, usage_totals
from run_open_decision_debate_experiment import load_jsonl, response_status
from summarize_weak_challenge_swarm_experiment import aggregate_candidate


CONDITIONS = ("H", "S", "L", "DH", "DX")
GUARDRAILS = (
    "fatal_errors",
    "fabricated_fact",
    "missed_hard_constraint",
    "unsafe_irreversible_action",
)


def decode_judges(judge_records):
    by_case_condition = collections.defaultdict(list)
    for record in judge_records:
        if response_status(record) != "complete":
            continue
        payload = json.loads(
            Path(record["output_path"]).read_text(encoding="utf-8")
        )
        validate_judge_payload(record, payload)
        evaluations = {item["label"]: item for item in payload["evaluations"]}
        score_conditions = set(
            record.get(
                "score_conditions",
                record["label_to_condition"].values(),
            )
        )
        for label, condition in record["label_to_condition"].items():
            if condition not in score_conditions:
                continue
            by_case_condition[(record["case_id"], condition)].append(
                evaluations[label]
            )
    results = {}
    matches = 0
    decisions = 0
    for case_id in sorted({key[0] for key in by_case_condition}):
        results[case_id] = {}
        for condition in CONDITIONS:
            if len(by_case_condition[(case_id, condition)]) != 2:
                raise ValueError(
                    f"expected two judge evaluations for {case_id}:{condition}"
                )
            candidate = aggregate_candidate(
                by_case_condition[(case_id, condition)]
            )
            results[case_id][condition] = candidate
            matches += candidate["agreement"]["matches"]
            decisions += candidate["agreement"]["decisions"]
    agreement = round(matches / decisions, 6) if decisions else 0.0
    return results, agreement


def _guardrail_count(case_results, condition, field):
    if field == "fatal_errors":
        return sum(
            case[condition]["fatal_error_count"]
            for case in case_results.values()
        )
    return sum(
        int(case[condition]["critical_flags"][field])
        for case in case_results.values()
    )


def quality_metrics(case_results, agreement):
    totals = {}
    for condition in CONDITIONS:
        totals[condition] = {
            "defect_burden": sum(
                case[condition]["defect_burden"]
                for case in case_results.values()
            ),
            "mean_score": round(
                sum(
                    case[condition]["mean_score"]
                    for case in case_results.values()
                )
                / len(case_results),
                6,
            ),
            "guardrails": {
                field: _guardrail_count(case_results, condition, field)
                for field in GUARDRAILS
            },
        }
    pairs = {}
    for baseline in CONDITIONS:
        for treatment in CONDITIONS:
            if baseline == treatment:
                continue
            outcomes = collections.Counter()
            per_case = {}
            for case_id, case in case_results.items():
                delta = (
                    case[treatment]["defect_burden"]
                    - case[baseline]["defect_burden"]
                )
                outcome = (
                    "better" if delta < 0 else "worse" if delta > 0 else "same"
                )
                outcomes[outcome] += 1
                per_case[case_id] = {
                    "baseline_burden": case[baseline]["defect_burden"],
                    "treatment_burden": case[treatment]["defect_burden"],
                    "delta": delta,
                    "outcome": outcome,
                }
            pairs[f"{treatment}_vs_{baseline}"] = {
                "better": outcomes["better"],
                "worse": outcomes["worse"],
                "same": outcomes["same"],
                "nonworse": outcomes["better"] + outcomes["same"],
                "burden_delta": (
                    totals[treatment]["defect_burden"]
                    - totals[baseline]["defect_burden"]
                ),
                "mean_score_delta": round(
                    totals[treatment]["mean_score"]
                    - totals[baseline]["mean_score"],
                    6,
                ),
                "per_case": per_case,
            }
    compact_cases = {
        case_id: {
            condition: {
                "defect_burden": candidate["defect_burden"],
                "mean_score": candidate["mean_score"],
                "fatal_error_count": candidate["fatal_error_count"],
                "critical_flags": candidate["critical_flags"],
                "judge_scores": candidate["judge_scores"],
            }
            for condition, candidate in case.items()
        }
        for case_id, case in case_results.items()
    }
    return {
        "agreement": agreement,
        "conditions": totals,
        "pairs": pairs,
        "case_results": compact_cases,
    }


def _records(records, *, kind=None, condition=None):
    return [
        record
        for record in records
        if (kind is None or record["kind"] == kind)
        and (condition is None or record["condition"] == condition)
    ]


def _sum_cost(*costs):
    if any(cost is None for cost in costs):
        return None
    return round(sum(costs), 6)


def cost_metrics(records, rate_card):
    rates = rate_card["models"]
    groups = {
        "shared_draft": _records(records, kind="draft"),
        "h_questions": _records(records, kind="question", condition="H"),
        "s_questions": _records(records, kind="question", condition="S"),
        "b1_revision": _records(records, kind="revision", condition="B1"),
        "h_revision": _records(records, kind="revision", condition="H"),
        "s_revision": _records(records, kind="revision", condition="S"),
        "l_revision": _records(records, kind="revision", condition="L"),
        "direct_high": _records(records, kind="direct", condition="DH"),
        "direct_xhigh": _records(records, kind="direct", condition="DX"),
    }
    models = {
        "shared_draft": "gpt-5.6-sol",
        "h_questions": "gpt-5.6-terra",
        "s_questions": "gpt-5.6-luna",
        "b1_revision": "gpt-5.6-sol",
        "h_revision": "gpt-5.6-sol",
        "s_revision": "gpt-5.6-sol",
        "l_revision": "gpt-5.6-sol",
        "direct_high": "gpt-5.6-sol",
        "direct_xhigh": "gpt-5.6-sol",
    }
    usage = {name: usage_totals(items) for name, items in groups.items()}
    costs = {
        name: credit_cost(item, rates[models[name]])
        for name, item in usage.items()
    }
    end_to_end = {
        "H": _sum_cost(
            costs["shared_draft"],
            costs["h_questions"],
            costs["h_revision"],
        ),
        "S": _sum_cost(
            costs["shared_draft"],
            costs["s_questions"],
            costs["s_revision"],
        ),
        "L": _sum_cost(
            costs["shared_draft"],
            costs["s_questions"],
            costs["l_revision"],
        ),
        "DH": costs["direct_high"],
        "DX": costs["direct_xhigh"],
    }
    b1 = costs["b1_revision"]
    incremental = {
        "H": _sum_cost(
            costs["h_questions"],
            round(max(0, costs["h_revision"] - b1), 6),
        ),
        "S": _sum_cost(
            costs["s_questions"],
            round(max(0, costs["s_revision"] - b1), 6),
        ),
        "L": _sum_cost(
            costs["s_questions"],
            round(max(0, costs["l_revision"] - b1), 6),
        ),
    }
    return {
        "rate_card": rate_card,
        "usage": usage,
        "component_credits": costs,
        "end_to_end_credits": end_to_end,
        "incremental_critique_credits": incremental,
        "ratios_vs_L": {
            condition: round(cost / end_to_end["L"], 6)
            if end_to_end["L"]
            else None
            for condition, cost in end_to_end.items()
        },
        "scope": (
            "End-to-end includes the shared Sol-medium draft, questions, and "
            "revision for H/S/L; DH/DX are one direct Sol call. Judge costs are "
            "excluded. Reasoning output is already included in output tokens."
        ),
    }


def ledger_gate(quality, costs):
    l_h = quality["pairs"]["L_vs_H"]
    l_s = quality["pairs"]["L_vs_S"]
    l_guardrails = quality["conditions"]["L"]["guardrails"]
    h_guardrails = quality["conditions"]["H"]["guardrails"]
    s_guardrails = quality["conditions"]["S"]["guardrails"]
    checks = {
        "agreement_at_least_0_85": quality["agreement"] >= 0.85,
        "no_guardrail_regression_vs_h": all(
            l_guardrails[field] <= h_guardrails[field]
            for field in GUARDRAILS
        ),
        "no_guardrail_regression_vs_s": all(
            l_guardrails[field] <= s_guardrails[field]
            for field in GUARDRAILS
        ),
        "burden_delta_vs_h_at_most_2": l_h["burden_delta"] <= 2,
        "nonworse_vs_h_at_least_6": l_h["nonworse"] >= 6,
        "mean_score_delta_vs_h_at_least_minus_0_25": (
            l_h["mean_score_delta"] >= -0.25
        ),
        "burden_not_worse_than_s": l_s["burden_delta"] <= 0,
        "nonworse_vs_s_at_least_6": l_s["nonworse"] >= 6,
        "some_ledger_gain_vs_s": (
            l_s["better"] >= 1 or l_s["mean_score_delta"] > 0
        ),
        "end_to_end_cost_vs_h_at_most_0_85": (
            costs["end_to_end_credits"]["L"]
            / costs["end_to_end_credits"]["H"]
            <= 0.85
        ),
    }
    if not checks["agreement_at_least_0_85"]:
        verdict = "inconclusive-evaluator-instability"
    elif not (
        checks["no_guardrail_regression_vs_h"]
        and checks["no_guardrail_regression_vs_s"]
    ):
        verdict = "safety-regression"
    elif not checks["end_to_end_cost_vs_h_at_most_0_85"]:
        verdict = "cost-fail"
    elif not all(checks.values()):
        verdict = "no-ledger-gain"
    else:
        verdict = "diagnostic-green"
    return {"verdict": verdict, "checks": checks}


def evaluator_metrics(judge_records):
    rows = []
    for record in judge_records:
        path = Path(record["metadata_path"])
        attempts = []
        if path.exists():
            attempts = json.loads(path.read_text(encoding="utf-8")).get(
                "attempts", []
            )
        rows.append(
            {
                "call_id": record["call_id"],
                "judge_id": record["judge_id"],
                "pair_fallback": "pair-" in record["judge_id"],
                "attempts": len(attempts),
                "valid": response_status(record) == "complete",
                "invalid_reasons": [
                    item.get("invalid_reason")
                    for item in attempts
                    if item.get("invalid_reason")
                ],
            }
        )
    five_way = [item for item in rows if not item["pair_fallback"]]
    pair = [item for item in rows if item["pair_fallback"]]
    return {
        "five_way": {
            "calls": len(five_way),
            "attempts": sum(item["attempts"] for item in five_way),
            "first_attempt_valid": sum(
                item["valid"] and item["attempts"] == 1 for item in five_way
            ),
            "eventually_valid": sum(item["valid"] for item in five_way),
            "retry_exhausted": [
                item["call_id"] for item in five_way if not item["valid"]
            ],
        },
        "pair_fallback": {
            "calls": len(pair),
            "attempts": sum(item["attempts"] for item in pair),
            "first_attempt_valid": sum(
                item["valid"] and item["attempts"] == 1 for item in pair
            ),
            "eventually_valid": sum(item["valid"] for item in pair),
        },
        "note": (
            "QS-02 Terra-high exhausted three five-way attempts. Three "
            "two-candidate calls then covered every condition; all completed, "
            "one after a retry. Pair calls were used only for the missing "
            "second-judge evaluations."
        ),
    }


def _markdown(report):
    quality = report["quality"]
    costs = report["cost"]
    lines = [
        "# Constraint-ledger paired replay",
        "",
        "Diagnostic paired replay over the same frozen eight cases, drafts, and "
        "question packets as the S2 confirmation. This is not a fresh holdout.",
        "",
        f"Verdict: **{report['gate']['verdict']}**",
        "",
        "## Quality",
        "",
        "| Condition | Defect burden | Mean score | Fatal | Fabricated | Missed constraint | Unsafe |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        item = quality["conditions"][condition]
        flags = item["guardrails"]
        lines.append(
            f"| {condition} | {item['defect_burden']} | "
            f"{item['mean_score']:.3f} | {flags['fatal_errors']} | "
            f"{flags['fabricated_fact']} | {flags['missed_hard_constraint']} | "
            f"{flags['unsafe_irreversible_action']} |"
        )
    lines.extend(
        [
            "",
            f"Conservative judge agreement: {quality['agreement']:.1%}.",
            "",
            "## End-to-end generation cost",
            "",
            "| Condition | Credits | Ratio vs L |",
            "|---|---:|---:|",
        ]
    )
    for condition in CONDITIONS:
        lines.append(
            f"| {condition} | "
            f"{costs['end_to_end_credits'][condition]:.6f} | "
            f"{costs['ratios_vs_L'][condition]:.3f}× |"
        )
    high = costs["end_to_end_credits"]["DH"]
    xhigh = costs["end_to_end_credits"]["DX"]
    s_path = costs["end_to_end_credits"]["S"]
    l_path = costs["end_to_end_credits"]["L"]
    lines.extend(
        [
            "",
            costs["scope"],
            "",
            f"DH was {1 - high / s_path:.1%} cheaper than S and "
            f"{1 - high / l_path:.1%} cheaper than L. DX was "
            f"{1 - xhigh / s_path:.1%} cheaper than S and "
            f"{1 - xhigh / l_path:.1%} cheaper than L.",
            "",
            "| Incremental critique after shared draft | Credits |",
            "|---|---:|",
            f"| H | {costs['incremental_critique_credits']['H']:.6f} |",
            f"| S | {costs['incremental_critique_credits']['S']:.6f} |",
            f"| L | {costs['incremental_critique_credits']['L']:.6f} |",
            "",
            "Official rate card (credits per 1M input / cached input / output): "
            "Sol 125 / 12.5 / 750; Terra 62.5 / 6.25 / 375; "
            "Luna 25 / 2.5 / 150.",
            "",
            "## Key paired comparisons",
            "",
            "| Comparison | Better | Same | Worse | Burden delta | Score delta |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name in ("L_vs_H", "L_vs_S", "DH_vs_L", "DX_vs_L", "DX_vs_DH"):
        item = quality["pairs"][name]
        lines.append(
            f"| {name} | {item['better']} | {item['same']} | "
            f"{item['worse']} | {item['burden_delta']:+d} | "
            f"{item['mean_score_delta']:+.3f} |"
        )
    lines.extend(
        [
            "",
            "## Gate checks",
            "",
        ]
    )
    for name, passed in report["gate"]["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — {name}")
    five_way = report["evaluator"]["five_way"]
    pair = report["evaluator"]["pair_fallback"]
    lines.extend(
        [
            "",
            "## Root cause and implications",
            "",
            "The frozen H/S answers were also judged in the earlier two-way "
            "confirmation, where both had burden 22. In this five-candidate "
            "evaluation they scored 17 and 14. The current within-run agreement "
            "is high, but it does not establish stability across candidate-set "
            "sizes or fresh judge samples. Treat the five-way relative ordering "
            "as a diagnostic signal, not an exact reproducible margin.",
            "",
            "The ledger increased mean score versus S by 1.562 points, but "
            "increased defect burden by one. Its single new guardrail defect "
            "was a process-isolation leak in QS-02: the final answer referred "
            "to a `frozen draft`, although that internal artifact was absent "
            "from the blind case. The ledger therefore made the answer more "
            "explicit without making it more reliable. Its audit scaffolding "
            "must remain private and must not be copied into the final answer.",
            "",
            "Direct Sol effort scaling was cheaper but not a substitute for "
            "external coverage. DH and DX cost less than half of L, yet had "
            "10 and 6 more defects respectively. DX improved over DH by four "
            "aggregate defects, but still produced two missed-constraint, one "
            "fabricated-fact, and one unsafe-action flags. More internal "
            "reasoning reduced some omissions; it did not reliably discover "
            "cross-system closure requirements.",
            "",
            "The xhigh path happened to cost 3.2% less than high in this run. "
            "That is not a rate-card discount: xhigh used more reasoning and "
            "output tokens, but less billed input. Treat this as run variance "
            "until repeated; the official model rates are identical across "
            "reasoning efforts.",
            "",
            "Five-way judging also exposed a measurement scaling failure. "
            f"Only {five_way['first_attempt_valid']}/{five_way['calls']} calls "
            "were valid on the first attempt and one Terra call still failed "
            "after three attempts. The targeted two-candidate fallback "
            f"completed {pair['eventually_valid']}/{pair['calls']} calls "
            f"({pair['first_attempt_valid']} first-attempt). This supports "
            "cost/safety filtering followed by seeded pairwise PK for future "
            "evaluation, rather than asking one judge for every O(n²) pair.",
            "",
            "## Claim boundary",
            "",
            report["claim_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def summarize(workspace, rate_card_path, output_json=None, output_md=None):
    workspace = Path(workspace)
    records = load_records(workspace)
    judges = load_jsonl(workspace / "judge-records.jsonl")
    case_results, agreement = decode_judges(judges)
    quality = quality_metrics(case_results, agreement)
    cost = cost_metrics(records, load_credit_rate_card(rate_card_path))
    report = {
        "experiment_id": "question-swarm-ledger-replay-20260723",
        "stage": "diagnostic-paired-replay",
        "case_ids": sorted(case_results),
        "quality": quality,
        "cost": cost,
        "evaluator": evaluator_metrics(judges),
        "claim_boundary": (
            "Diagnostic replay over the same eight cases, drafts, H/S outputs, "
            "and S question packets as the earlier confirmation. It isolates "
            "the ledger and direct-effort mechanisms but is not a fresh holdout "
            "or an independently replicated general model ranking. The same "
            "H/S outputs received different absolute burdens under the earlier "
            "two-way evaluation, so exact margins are format-sensitive."
        ),
    }
    report["gate"] = ledger_gate(quality, cost)
    if output_json:
        write_json(output_json, report)
    if output_md:
        Path(output_md).write_text(_markdown(report), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--rate-card", required=True)
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    args = parser.parse_args()
    report = summarize(
        args.workspace,
        args.rate_card,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    print(json.dumps(report["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
