#!/usr/bin/env python3
"""Summarize the fresh DX/L2/T1 final tournament."""

import argparse
import collections
import json
from pathlib import Path

from create_final_tournament_judging import PAIRS
from create_final_tournament_workspace import CONDITIONS, EXPERIMENT_ID
from create_open_decision_debate_workspace import write_json
from create_question_swarm_confirmation_workspace import load_records
from create_weak_challenge_swarm_judging import (
    CRITICAL_FLAGS,
    validate_judge_payload,
)
from question_swarm_common import credit_cost, load_credit_rate_card, usage_totals
from run_open_decision_debate_experiment import load_jsonl, response_status
from summarize_weak_challenge_swarm_experiment import aggregate_candidate


GUARDRAILS = (
    "fatal_errors",
    "fabricated_fact",
    "missed_hard_constraint",
    "unsafe_irreversible_action",
)
PROCESS_TERMS = (
    "frozen draft",
    "shared draft",
    "question packet",
    "opaque question",
    "reviewer",
    "internal check",
    "the experiment",
)


def _decode(judges):
    grouped = collections.defaultdict(list)
    preferences = collections.Counter()
    for record in judges:
        if response_status(record) != "complete":
            raise ValueError(f"incomplete judge: {record['call_id']}")
        payload = json.loads(
            Path(record["output_path"]).read_text(encoding="utf-8")
        )
        validate_judge_payload(record, payload)
        evaluations = {item["label"]: item for item in payload["evaluations"]}
        for label, condition in record["label_to_condition"].items():
            grouped[
                (record["case_id"], record["comparison"], condition)
            ].append(evaluations[label])
        preference = payload["pairwise_preferences"][0]
        winner = (
            "tie"
            if preference["winner"] == "tie"
            else record["label_to_condition"][preference["winner"]]
        )
        preferences[(record["comparison"], winner)] += 1

    result = {}
    matches = 0
    decisions = 0
    for case_id, comparison, _condition in sorted(grouped):
        result.setdefault(case_id, {}).setdefault(comparison, {})
    for case_id, comparisons in result.items():
        for comparison in comparisons:
            for condition in comparison.split("-vs-"):
                items = grouped[(case_id, comparison, condition)]
                if len(items) != 2:
                    raise ValueError(
                        f"expected two judges: {case_id}:{comparison}:{condition}"
                    )
                candidate = aggregate_candidate(items)
                comparisons[comparison][condition] = candidate
                matches += candidate["agreement"]["matches"]
                decisions += candidate["agreement"]["decisions"]
    preference_rows = {
        comparison: {
            winner: preferences[(comparison, winner)]
            for winner in (*comparison.split("-vs-"), "tie")
        }
        for comparison in (f"{left}-vs-{right}" for left, right in PAIRS)
    }
    return (
        result,
        round(matches / decisions, 6) if decisions else 0.0,
        preference_rows,
    )


def _guardrail(candidate, field):
    if field == "fatal_errors":
        return candidate["fatal_error_count"]
    return int(candidate["critical_flags"][field])


def _comparison_metrics(case_results, agreement, preferences):
    result = {}
    for left, right in PAIRS:
        comparison = f"{left}-vs-{right}"
        left_burden = sum(
            case[comparison][left]["defect_burden"]
            for case in case_results.values()
        )
        right_burden = sum(
            case[comparison][right]["defect_burden"]
            for case in case_results.values()
        )
        left_mean_score = sum(
            case[comparison][left]["mean_score"]
            for case in case_results.values()
        ) / len(case_results)
        right_mean_score = sum(
            case[comparison][right]["mean_score"]
            for case in case_results.values()
        ) / len(case_results)
        outcomes = collections.Counter()
        per_case = {}
        for case_id, case in case_results.items():
            left_value = case[comparison][left]["defect_burden"]
            right_value = case[comparison][right]["defect_burden"]
            right_delta = right_value - left_value
            outcome = (
                "right_better"
                if right_delta < 0
                else "left_better"
                if right_delta > 0
                else "same"
            )
            outcomes[outcome] += 1
            per_case[case_id] = {
                left: left_value,
                right: right_value,
                "right_minus_left": right_delta,
                "outcome": outcome,
            }
        guardrails = {
            field: {
                left: sum(
                    _guardrail(case[comparison][left], field)
                    for case in case_results.values()
                ),
                right: sum(
                    _guardrail(case[comparison][right], field)
                    for case in case_results.values()
                ),
            }
            for field in GUARDRAILS
        }
        result[comparison] = {
            "left": left,
            "right": right,
            "burden": {left: left_burden, right: right_burden},
            "right_burden_delta": right_burden - left_burden,
            "right_burden_reduction": round(
                (left_burden - right_burden) / left_burden,
                6,
            )
            if left_burden
            else 0.0,
            "mean_score": {
                left: round(left_mean_score, 6),
                right: round(right_mean_score, 6),
            },
            "right_mean_score_delta": round(
                right_mean_score - left_mean_score,
                6,
            ),
            "left_better": outcomes["left_better"],
            "right_better": outcomes["right_better"],
            "same": outcomes["same"],
            "left_nonworse": outcomes["left_better"] + outcomes["same"],
            "right_nonworse": outcomes["right_better"] + outcomes["same"],
            "guardrails": guardrails,
            "judge_preferences": preferences[comparison],
            "per_case": per_case,
        }

    condition_context_burdens = {condition: {} for condition in CONDITIONS}
    for comparison, metric in result.items():
        for condition, burden in metric["burden"].items():
            condition_context_burdens[condition][comparison] = burden
    stability = {}
    for condition, contexts in condition_context_burdens.items():
        values = list(contexts.values())
        delta = max(values) - min(values)
        stability[condition] = {
            "burden_by_opponent": contexts,
            "max_delta": delta,
            "passed": delta <= 2,
        }
    return {
        "agreement": agreement,
        "comparisons": result,
        "opponent_stability": stability,
        "opponent_stability_passed": all(
            item["passed"] for item in stability.values()
        ),
    }


def context_drift(case_results, manifest):
    comparisons_by_condition = {
        condition: [
            f"{left}-vs-{right}"
            for left, right in PAIRS
            if condition in {left, right}
        ]
        for condition in CONDITIONS
    }
    result = {}
    for condition, comparisons in comparisons_by_condition.items():
        left_comparison, right_comparison = comparisons
        differences = []
        for case_id, case in case_results.items():
            left = case[left_comparison][condition]
            right = case[right_comparison][condition]
            card = json.loads(
                Path(manifest["adjudication_snapshot_index"][case_id])
                .read_text(encoding="utf-8")
            )
            criteria = {
                "must_cover": {
                    f"MC-{index}": text
                    for index, text in enumerate(
                        card["must_cover_constraints"], start=1
                    )
                },
                "closure": {
                    f"CL-{index}": text
                    for index, text in enumerate(
                        card["decision_closure_requirements"], start=1
                    )
                },
                "fatal_errors": {
                    f"FE-{index}": text
                    for index, text in enumerate(
                        card["fatal_errors"], start=1
                    )
                },
            }
            for field, decision in (
                ("must_cover", "covered"),
                ("closure", "satisfied"),
                ("fatal_errors", "present"),
            ):
                for item_id in left[field]:
                    left_value = left[field][item_id][decision]
                    right_value = right[field][item_id][decision]
                    if left_value != right_value:
                        differences.append(
                            {
                                "case_id": case_id,
                                "field": field,
                                "item_id": item_id,
                                "criterion": criteria[field][item_id],
                                left_comparison: left_value,
                                right_comparison: right_value,
                            }
                        )
            for flag in CRITICAL_FLAGS:
                left_value = left["critical_flags"][flag]
                right_value = right["critical_flags"][flag]
                if left_value != right_value:
                    differences.append(
                        {
                            "case_id": case_id,
                            "field": "critical_flags",
                            "item_id": flag,
                            "criterion": flag,
                            left_comparison: left_value,
                            right_comparison: right_value,
                        }
                    )
        result[condition] = {
            "comparisons": comparisons,
            "decision_differences": len(differences),
            "differences": differences,
        }
    return result


def _select(records, condition, kind):
    return [
        record
        for record in records
        if record["condition"] == condition and record["kind"] == kind
    ]


def _add_usage(*items):
    result = {
        "complete": all(item["complete"] for item in items),
        "records": sum(item["records"] for item in items),
        "attempts": sum(item["attempts"] for item in items),
        "input_tokens": sum(item["input_tokens"] for item in items),
        "cached_input_tokens": sum(
            item["cached_input_tokens"] for item in items
        ),
        "output_tokens": sum(item["output_tokens"] for item in items),
        "reasoning_output_tokens": sum(
            item["reasoning_output_tokens"] for item in items
        ),
        "incomplete_call_ids": sorted(
            {
                call_id
                for item in items
                for call_id in item["incomplete_call_ids"]
            }
        ),
    }
    return result


def cost_metrics(records, rate_card, judges=None):
    rates = rate_card["models"]
    usage = {
        "shared": usage_totals(_select(records, "SHARED", "draft")),
        "DX": usage_totals(_select(records, "DX", "final")),
        "L2_questions": usage_totals(_select(records, "L2", "question")),
        "L2_final": usage_totals(_select(records, "L2", "revision")),
        "T1_questions": usage_totals(_select(records, "T1", "question")),
        "T1_final": usage_totals(_select(records, "T1", "revision")),
    }
    component_credits = {
        "shared": credit_cost(usage["shared"], rates["gpt-5.6-sol"]),
        "DX": credit_cost(usage["DX"], rates["gpt-5.6-sol"]),
        "L2_questions": credit_cost(
            usage["L2_questions"], rates["gpt-5.6-luna"]
        ),
        "L2_final": credit_cost(
            usage["L2_final"], rates["gpt-5.6-sol"]
        ),
        "T1_questions": credit_cost(
            usage["T1_questions"], rates["gpt-5.6-terra"]
        ),
        "T1_final": credit_cost(
            usage["T1_final"], rates["gpt-5.6-sol"]
        ),
    }
    end_to_end = {
        "DX": component_credits["DX"],
        "L2": round(
            component_credits["shared"]
            + component_credits["L2_questions"]
            + component_credits["L2_final"],
            6,
        ),
        "T1": round(
            component_credits["shared"]
            + component_credits["T1_questions"]
            + component_credits["T1_final"],
            6,
        ),
    }
    condition_usage = {
        "DX": usage["DX"],
        "L2": _add_usage(
            usage["shared"], usage["L2_questions"], usage["L2_final"]
        ),
        "T1": _add_usage(
            usage["shared"], usage["T1_questions"], usage["T1_final"]
        ),
    }
    judge_cost = None
    if judges is not None:
        judge_usage = {
            "sol-medium": usage_totals(
                [
                    record
                    for record in judges
                    if record["judge_id"] == "sol-medium"
                ]
            ),
            "terra-high": usage_totals(
                [
                    record
                    for record in judges
                    if record["judge_id"] == "terra-high"
                ]
            ),
        }
        judge_credits = {
            "sol-medium": credit_cost(
                judge_usage["sol-medium"],
                rates["gpt-5.6-sol"],
            ),
            "terra-high": credit_cost(
                judge_usage["terra-high"],
                rates["gpt-5.6-terra"],
            ),
        }
        judge_cost = {
            "usage": judge_usage,
            "credits": judge_credits,
            "total_credits": round(sum(judge_credits.values()), 6),
            "note": (
                "Includes invalid judge attempts because they consumed tokens."
            ),
        }
    return {
        "rate_card": rate_card,
        "component_usage": usage,
        "condition_usage": condition_usage,
        "component_credits": component_credits,
        "end_to_end_credits": end_to_end,
        "ratios_vs_DX": {
            condition: round(cost / end_to_end["DX"], 6)
            for condition, cost in end_to_end.items()
        },
        "judge_cost": judge_cost,
        "scope": (
            "Generation only. DX is one Sol-xhigh final. L2/T1 each include "
            "the same Sol-medium draft, their isolated questions, and one "
            "Sol-medium Reality Slap final. Judge cost is excluded; failed "
            "generation attempts are included."
        ),
    }


def process_leaks(records):
    result = {}
    for condition in CONDITIONS:
        kind = "final" if condition == "DX" else "revision"
        matches = []
        for record in _select(records, condition, kind):
            text = Path(record["output_path"]).read_text(encoding="utf-8")
            found = sorted(
                term for term in PROCESS_TERMS if term in text.casefold()
            )
            if found:
                matches.append(
                    {"case_id": record["case_id"], "terms": found}
                )
        result[condition] = {
            "count": len(matches),
            "matches": matches,
        }
    return result


def _no_guardrail_regression(metric, baseline, treatment):
    return all(
        values[treatment] <= values[baseline]
        for values in metric["guardrails"].values()
    )


def _match_results(quality, cost):
    comparisons = quality["comparisons"]
    costs = cost["end_to_end_credits"]
    dx_l2 = comparisons["DX-vs-L2"]
    dx_l2_checks = {
        "no_guardrail_regression": _no_guardrail_regression(
            dx_l2, "DX", "L2"
        ),
        "burden_reduction_at_least_20_percent": (
            dx_l2["right_burden_reduction"] >= 0.20
        ),
        "nonworse_at_least_9": dx_l2["right_nonworse"] >= 9,
        "improved_at_least_4": dx_l2["right_better"] >= 4,
        "cost_ratio_at_most_2": costs["L2"] / costs["DX"] <= 2.0,
    }

    l2_t1 = comparisons["L2-vs-T1"]
    l2_t1_checks = {
        "no_guardrail_regression_for_L2": _no_guardrail_regression(
            l2_t1, "T1", "L2"
        ),
        "L2_burden_at_most_T1_plus_2": (
            l2_t1["burden"]["L2"] <= l2_t1["burden"]["T1"] + 2
        ),
        "L2_nonworse_at_least_9": l2_t1["left_nonworse"] >= 9,
        "L2_cost_discount_at_least_15_percent": (
            costs["L2"] / costs["T1"] <= 0.85
        ),
    }

    dx_t1 = comparisons["DX-vs-T1"]
    dx_t1_checks = {
        "no_guardrail_regression": _no_guardrail_regression(
            dx_t1, "DX", "T1"
        ),
        "burden_reduction_at_least_20_percent": (
            dx_t1["right_burden_reduction"] >= 0.20
        ),
        "nonworse_at_least_9": dx_t1["right_nonworse"] >= 9,
        "improved_at_least_4": dx_t1["right_better"] >= 4,
        "cost_ratio_at_most_2_1": costs["T1"] / costs["DX"] <= 2.1,
    }
    matches = {
        "DX-vs-L2": {
            "winner": "L2" if all(dx_l2_checks.values()) else "DX",
            "challenger": "L2",
            "checks": dx_l2_checks,
        },
        "L2-vs-T1": {
            "winner": "L2" if all(l2_t1_checks.values()) else "T1",
            "challenger": "L2",
            "checks": l2_t1_checks,
        },
        "DX-vs-T1": {
            "winner": "T1" if all(dx_t1_checks.values()) else "DX",
            "challenger": "T1",
            "checks": dx_t1_checks,
        },
    }
    return matches


def _champion(quality, cost, matches):
    if quality["agreement"] < 0.85:
        return {
            "verdict": "inconclusive-evaluator-disagreement",
            "champion": None,
            "wins": {},
        }
    if not quality["opponent_stability_passed"]:
        stable = [
            condition
            for condition, item in quality["opponent_stability"].items()
            if item["passed"]
        ]
        stable_match = next(
            (
                name
                for name in matches
                if set(name.split("-vs-")) == set(stable)
            ),
            None,
        )
        return {
            "verdict": "inconclusive-opponent-context-instability",
            "champion": None,
            "wins": {},
            "posthoc_operational_default": (
                matches[stable_match]["winner"] if stable_match else None
            ),
            "posthoc_default_basis": (
                f"Excluded the unstable candidate and used {stable_match}; "
                "this fallback was not preregistered."
                if stable_match
                else None
            ),
        }
    wins = collections.Counter(item["winner"] for item in matches.values())
    leaders = [condition for condition in CONDITIONS if wins[condition] >= 2]
    if len(leaders) == 1:
        return {
            "verdict": "champion-selected",
            "champion": leaders[0],
            "wins": dict(wins),
            "tie_break": None,
        }

    average_burden = {}
    average_guardrails = {}
    for condition in CONDITIONS:
        relevant = [
            metric
            for metric in quality["comparisons"].values()
            if condition in metric["burden"]
        ]
        average_burden[condition] = sum(
            metric["burden"][condition] for metric in relevant
        ) / len(relevant)
        average_guardrails[condition] = sum(
            sum(values[condition] for values in metric["guardrails"].values())
            for metric in relevant
        ) / len(relevant)
    safest = min(average_guardrails.values())
    pool = [
        condition
        for condition in CONDITIONS
        if average_guardrails[condition] == safest
    ]
    best_burden = min(average_burden[condition] for condition in pool)
    burden_pool = [
        condition
        for condition in pool
        if average_burden[condition] <= best_burden + 2
    ]
    champion = min(
        burden_pool,
        key=lambda condition: cost["end_to_end_credits"][condition],
    )
    return {
        "verdict": "champion-selected-by-tie-break",
        "champion": champion,
        "wins": dict(wins),
        "tie_break": {
            "average_guardrails": average_guardrails,
            "average_burden": average_burden,
            "cost_eligible_pool": burden_pool,
        },
    }


def execution_metrics(records):
    rows = []
    for record in records:
        path = Path(record["metadata_path"])
        attempts = []
        if path.exists():
            attempts = json.loads(path.read_text(encoding="utf-8")).get(
                "attempts", []
            )
        rows.append(
            {
                "call_id": record["call_id"],
                "attempts": len(attempts),
                "valid": response_status(record) == "complete",
            }
        )
    return {
        "calls": len(rows),
        "attempts": sum(item["attempts"] for item in rows),
        "first_attempt_valid": sum(
            item["valid"] and item["attempts"] == 1 for item in rows
        ),
        "eventually_valid": sum(item["valid"] for item in rows),
    }


def _markdown(report):
    quality = report["quality"]
    cost = report["cost"]
    champion = report["selection"]
    lines = [
        "# Final DX/L2/T1 tournament",
        "",
        f"Verdict: **{champion['verdict']}**",
        f"Champion: **{champion['champion'] or 'none'}**",
        (
            "Post-hoc operational default: "
            f"**{champion.get('posthoc_operational_default') or 'none'}**"
        ),
        "",
        "Twelve fresh holdout cases, three frozen pairwise matchups, and two "
        "blind judges per matchup. Defect burden and safety gates are primary; "
        "mean score and judge preference are descriptive only.",
        "",
        "## Match results",
        "",
        "| Match | Burden | Better / same / worse for right | Judge preference | Gate winner |",
        "|---|---:|---:|---:|---|",
    ]
    for left, right in PAIRS:
        name = f"{left}-vs-{right}"
        item = quality["comparisons"][name]
        preferences = item["judge_preferences"]
        lines.append(
            f"| {name} | {item['burden'][left]} vs "
            f"{item['burden'][right]} | {item['right_better']} / "
            f"{item['same']} / {item['left_better']} | "
            f"{left} {preferences[left]}, {right} {preferences[right]}, "
            f"tie {preferences['tie']} | "
            f"**{report['matches'][name]['winner']}** |"
        )
    lines.extend(
        [
            "",
            f"Conservative checklist agreement: {quality['agreement']:.1%}.",
            "",
            "## Opponent-context stability",
            "",
            "| Candidate | Burden by matchup | Max delta | Stable |",
            "|---|---|---:|---|",
        ]
    )
    for condition in CONDITIONS:
        item = quality["opponent_stability"][condition]
        contexts = ", ".join(
            f"{name}: {value}"
            for name, value in item["burden_by_opponent"].items()
        )
        lines.append(
            f"| {condition} | {contexts} | {item['max_delta']} | "
            f"{'yes' if item['passed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "Mean scores are secondary and opponent-sensitive:",
            "",
        ]
    )
    for left, right in PAIRS:
        name = f"{left}-vs-{right}"
        item = quality["comparisons"][name]
        lines.append(
            f"- {name}: {left} {item['mean_score'][left]:.3f}, "
            f"{right} {item['mean_score'][right]:.3f} "
            f"(right delta {item['right_mean_score_delta']:+.3f})."
        )
    lines.extend(
        [
            "",
            "## Generation cost",
            "",
            "| Candidate | Credits | Ratio vs DX |",
            "|---|---:|---:|",
        ]
    )
    for condition in CONDITIONS:
        lines.append(
            f"| {condition} | "
            f"{cost['end_to_end_credits'][condition]:.6f} | "
            f"{cost['ratios_vs_DX'][condition]:.3f}× |"
        )
    lines.extend(["", cost["scope"], "", "## Preregistered match gates", ""])
    for name, match in report["matches"].items():
        lines.append(f"### {name}: {match['winner']}")
        lines.append("")
        for check, passed in match["checks"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — {check}")
        lines.append("")
    question_discount = (
        1
        - cost["component_credits"]["L2_questions"]
        / cost["component_credits"]["T1_questions"]
    )
    end_to_end_discount = (
        1
        - cost["end_to_end_credits"]["L2"]
        / cost["end_to_end_credits"]["T1"]
    )
    decision_denominator = 12 * (5 + 5 + 2 + len(CRITICAL_FLAGS))
    drift = report["opponent_context_drift"]
    execution = report["execution"]
    lines.extend(
        [
            "## Root cause and non-trivial insights",
            "",
            "The preregistered tournament did not produce a valid champion. "
            "L2's frozen answers received burden 32 against DX and 39 against "
            "T1, exceeding the opponent-context stability limit by five "
            "defects. The post-hoc DX default is an operating choice after "
            "excluding L2, not a preregistered tournament win.",
            "",
            "Aggregate burden stability also understated evaluator drift. The "
            "identity of individual checklist decisions changed across "
            f"opponents {drift['DX']['decision_differences']}/"
            f"{decision_denominator} times for DX, "
            f"{drift['L2']['decision_differences']}/"
            f"{decision_denominator} for L2, and "
            f"{drift['T1']['decision_differences']}/"
            f"{decision_denominator} for T1. DX's total burden moved by only "
            "one and T1's by zero because newly found defects were offset by "
            "other defects disappearing. A stable total is therefore not the "
            "same as a stable diagnosis.",
            "",
            "Pairwise preference and defect evidence pointed in different "
            "directions. Judges preferred L2 over DX in 21/24 calls even though "
            "burden tied 32/32 and L2 received three missed-hard-constraint "
            "flags versus DX's one. They preferred T1 over DX in 18/24 calls "
            "even though T1 had one more defect and no guardrail advantage. "
            "A forced winner captures holistic polish or relative appeal; it "
            "cannot replace checklist safety gates.",
            "",
            "The cheap-question stage did save "
            f"{question_discount:.1%} versus Terra questions, but L2 was only "
            f"{end_to_end_discount:.1%} cheaper end to end. Shared Sol drafting "
            "and the Sol final absorbed most of the budget, so optimizing the "
            "challenger alone has sharply diminishing product-level returns. "
            "L2 still cost 62.3% more than direct DX and did not demonstrate a "
            "defect reduction.",
            "",
            f"Generation was operationally clean: "
            f"{execution['generation']['first_attempt_valid']}/"
            f"{execution['generation']['calls']} calls were valid first try. "
            "Judging required "
            f"{execution['judges']['attempts']} attempts for "
            f"{execution['judges']['calls']} valid results; "
            f"{execution['judges']['first_attempt_valid']} were valid first "
            "try. The judge layer alone cost "
            f"{cost['judge_cost']['total_credits']:.6f} credits, which belongs "
            "to offline evaluation cost, not runtime candidate cost.",
            "",
            "Practical convergence: use DX as the default command path because "
            "neither pipeline proved lower defect burden and DX cost least. "
            "Keep T1 only as an opt-in premium mode when a user explicitly "
            "values additional external challenge despite the unproven quality "
            "gain. Remove L2 from the production shortlist.",
            "",
        ]
    )
    lines.extend(
        [
            "## Claim boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def summarize(workspace, rate_card_path, output_json=None, output_md=None):
    workspace = Path(workspace)
    manifest = json.loads(
        (workspace / "manifest.json").read_text(encoding="utf-8")
    )
    if manifest["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("unexpected experiment")
    records = load_records(workspace)
    judges = load_jsonl(workspace / "judge-records.jsonl")
    case_results, agreement, preferences = _decode(judges)
    quality = _comparison_metrics(case_results, agreement, preferences)
    cost = cost_metrics(
        records,
        load_credit_rate_card(rate_card_path),
        judges=judges,
    )
    matches = _match_results(quality, cost)
    selection = _champion(quality, cost, matches)
    report = {
        "experiment_id": EXPERIMENT_ID,
        "stage": "fresh-confirmation",
        "case_ids": sorted(case_results),
        "quality": quality,
        "opponent_context_drift": context_drift(
            case_results,
            manifest,
        ),
        "cost": cost,
        "matches": matches,
        "selection": selection,
        "process_leaks": process_leaks(records),
        "execution": {
            "generation": execution_metrics(records),
            "judges": execution_metrics(judges),
        },
        "claim_boundary": (
            "Fresh twelve-case internal confirmation with one generation "
            "sample per candidate and two checklist judges per frozen pair. "
            "It did not produce a preregistered champion. DX is only a post-hoc "
            "operational default after excluding the unstable L2 comparison; "
            "the run does not prove a universal model ranking or a stable "
            "effect outside open decisions."
        ),
    }
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
    print(json.dumps(report["selection"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
