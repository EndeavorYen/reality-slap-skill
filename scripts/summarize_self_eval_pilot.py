#!/usr/bin/env python3
"""Summarize quality, cost, and process isolation for the self-eval pilot."""

import argparse
import collections
import json
from pathlib import Path

from create_open_decision_debate_workspace import write_json
from create_question_swarm_confirmation_workspace import load_records
from create_self_eval_pilot_judging import PAIRS
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
    "self-eval",
    "self evaluation",
    "self-assessment",
    "自評",
    "frozen draft",
    "reviewer",
    "question packet",
    "constraint id",
    "internal check",
    "the experiment",
)


def _decode(judge_records):
    grouped = collections.defaultdict(list)
    for record in judge_records:
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
    result = {}
    matches = 0
    decisions = 0
    for case_id, comparison, _condition in sorted(grouped):
        result.setdefault(case_id, {}).setdefault(comparison, {})
    for case_id, comparisons in result.items():
        for comparison in comparisons:
            pair = tuple(comparison.split("-vs-"))
            for condition in pair:
                items = grouped[(case_id, comparison, condition)]
                if len(items) != 2:
                    raise ValueError(
                        f"expected two judges: {case_id}:{comparison}:{condition}"
                    )
                candidate = aggregate_candidate(items)
                comparisons[comparison][condition] = candidate
                matches += candidate["agreement"]["matches"]
                decisions += candidate["agreement"]["decisions"]
    return result, round(matches / decisions, 6) if decisions else 0.0


def _guardrail_total(case_results, comparison, condition, field):
    candidates = [
        case[comparison][condition] for case in case_results.values()
    ]
    if field == "fatal_errors":
        return sum(item["fatal_error_count"] for item in candidates)
    return sum(int(item["critical_flags"][field]) for item in candidates)


def comparison_metrics(case_results, agreement):
    metrics = {}
    for baseline, treatment in PAIRS:
        comparison = f"{baseline}-vs-{treatment}"
        baseline_burden = sum(
            case[comparison][baseline]["defect_burden"]
            for case in case_results.values()
        )
        treatment_burden = sum(
            case[comparison][treatment]["defect_burden"]
            for case in case_results.values()
        )
        baseline_score = sum(
            case[comparison][baseline]["mean_score"]
            for case in case_results.values()
        ) / len(case_results)
        treatment_score = sum(
            case[comparison][treatment]["mean_score"]
            for case in case_results.values()
        ) / len(case_results)
        outcomes = collections.Counter()
        per_case = {}
        for case_id, case in case_results.items():
            left = case[comparison][baseline]["defect_burden"]
            right = case[comparison][treatment]["defect_burden"]
            delta = right - left
            outcome = (
                "better" if delta < 0 else "worse" if delta > 0 else "same"
            )
            outcomes[outcome] += 1
            per_case[case_id] = {
                "baseline_burden": left,
                "treatment_burden": right,
                "delta": delta,
                "outcome": outcome,
                "baseline_score": case[comparison][baseline]["mean_score"],
                "treatment_score": case[comparison][treatment]["mean_score"],
            }
        guardrails = {
            field: {
                baseline: _guardrail_total(
                    case_results, comparison, baseline, field
                ),
                treatment: _guardrail_total(
                    case_results, comparison, treatment, field
                ),
            }
            for field in GUARDRAILS
        }
        regressions = [
            field
            for field, values in guardrails.items()
            if values[treatment] > values[baseline]
        ]
        metrics[comparison] = {
            "baseline": baseline,
            "treatment": treatment,
            "baseline_burden": baseline_burden,
            "treatment_burden": treatment_burden,
            "burden_delta": treatment_burden - baseline_burden,
            "burden_reduction": round(
                (baseline_burden - treatment_burden) / baseline_burden,
                6,
            )
            if baseline_burden
            else 0.0,
            "baseline_mean_score": round(baseline_score, 6),
            "treatment_mean_score": round(treatment_score, 6),
            "mean_score_delta": round(
                treatment_score - baseline_score,
                6,
            ),
            "better": outcomes["better"],
            "same": outcomes["same"],
            "worse": outcomes["worse"],
            "nonworse": outcomes["better"] + outcomes["same"],
            "guardrails": guardrails,
            "guardrail_regressions": regressions,
            "per_case": per_case,
        }
    return {"agreement": agreement, "comparisons": metrics}


def _records(records, condition, kind):
    return [
        record
        for record in records
        if record["condition"] == condition and record["kind"] == kind
    ]


def cost_metrics(records, rate_card):
    rates = rate_card["models"]
    usage = {
        condition: usage_totals(_records(records, condition, "final"))
        for condition in ("A", "B", "C", "D")
    }
    usage["D_questions"] = usage_totals(
        _records(records, "D", "question")
    )
    component = {
        condition: credit_cost(
            usage[condition],
            rates["gpt-5.6-sol"],
        )
        for condition in ("A", "B", "C", "D")
    }
    component["D_questions"] = credit_cost(
        usage["D_questions"],
        rates["gpt-5.6-luna"],
    )
    end_to_end = {
        "A": component["A"],
        "B": component["B"],
        "C": component["C"],
        "D": round(component["D"] + component["D_questions"], 6),
    }
    return {
        "rate_card": rate_card,
        "usage": usage,
        "component_credits": component,
        "end_to_end_credits": end_to_end,
        "ratios_vs_A": {
            condition: round(value / end_to_end["A"], 6)
            for condition, value in end_to_end.items()
        },
        "scope": (
            "Generation only. A/B/C each use one Sol-medium call. D uses two "
            "Luna-low question calls and one Sol-medium final call. Judge cost "
            "is excluded; failed generation attempts, if any, are included."
        ),
    }


def process_leaks(records):
    result = {}
    for condition in ("A", "B", "C", "D"):
        matches = []
        for record in _records(records, condition, "final"):
            text = Path(record["output_path"]).read_text(encoding="utf-8")
            folded = text.casefold()
            found = sorted(term for term in PROCESS_TERMS if term in folded)
            if found:
                matches.append(
                    {"case_id": record["case_id"], "terms": found}
                )
        result[condition] = {
            "count": len(matches),
            "matches": matches,
        }
    return result


def _pair_gate(name, metric, costs, leaks):
    baseline = metric["baseline"]
    treatment = metric["treatment"]
    caps = {
        "A-vs-B": 1.15,
        "A-vs-C": 1.15,
        "B-vs-C": 1.15,
        "C-vs-D": 1.25,
    }
    checks = {
        "no_guardrail_regression": not metric["guardrail_regressions"],
        "burden_reduction_at_least_20_percent": (
            metric["burden_reduction"] >= 0.20
        ),
        "nonworse_at_least_3_of_4": metric["nonworse"] >= 3,
        "some_quality_gain": (
            metric["better"] >= 1 or metric["mean_score_delta"] >= 0.25
        ),
        "mean_score_delta_at_least_minus_0_25": (
            metric["mean_score_delta"] >= -0.25
        ),
        "cost_ratio_within_cap": (
            costs[treatment] / costs[baseline] <= caps[name]
        ),
        "no_process_leak_regression": (
            leaks[treatment]["count"] <= leaks[baseline]["count"]
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def gate(quality, costs, leaks):
    pair_gates = {
        name: _pair_gate(
            name,
            metric,
            costs["end_to_end_credits"],
            leaks,
        )
        for name, metric in quality["comparisons"].items()
    }
    if quality["agreement"] < 0.85:
        self_eval_verdict = "inconclusive-evaluator-instability"
        premortem_verdict = "inconclusive-evaluator-instability"
    else:
        if any(
            not pair_gates[name]["checks"]["no_guardrail_regression"]
            for name in ("A-vs-B", "A-vs-C")
        ):
            self_eval_verdict = "self-eval-safety-regression"
        elif (
            pair_gates["A-vs-B"]["passed"]
            and pair_gates["A-vs-C"]["passed"]
        ):
            self_eval_verdict = "simple-self-eval-signal"
        elif pair_gates["A-vs-C"]["passed"]:
            self_eval_verdict = "structured-self-eval-signal"
        else:
            self_eval_verdict = "no-self-eval-signal"
        if not pair_gates["C-vs-D"]["checks"]["no_guardrail_regression"]:
            premortem_verdict = "premortem-safety-regression"
        elif pair_gates["C-vs-D"]["passed"]:
            premortem_verdict = "premortem-additive-signal"
        else:
            premortem_verdict = "no-premortem-signal"
    verdict = f"{self_eval_verdict}__{premortem_verdict}"
    return {
        "verdict": verdict,
        "self_eval_verdict": self_eval_verdict,
        "premortem_verdict": premortem_verdict,
        "agreement_at_least_0_85": quality["agreement"] >= 0.85,
        "pair_gates": pair_gates,
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
    lines = [
        "# Private self-evaluation fresh pilot",
        "",
        f"Verdict: **{report['gate']['verdict']}**",
        "",
        "Four fresh cases; Reality Slap was used only on the Sol-medium final "
        "decision calls. A/B/C used one Sol call each. D used two Luna-low "
        "pre-mortem question calls and one Sol final call.",
        "",
        "## Paired quality",
        "",
        "| Comparison | Burden baseline→treatment | Better / same / worse | Score delta | Guardrail regressions |",
        "|---|---:|---:|---:|---|",
    ]
    for name, item in quality["comparisons"].items():
        regressions = ", ".join(item["guardrail_regressions"]) or "none"
        lines.append(
            f"| {name} | {item['baseline_burden']}→"
            f"{item['treatment_burden']} ({item['burden_delta']:+d}; "
            f"{item['burden_reduction']:+.1%}) | "
            f"{item['better']} / {item['same']} / {item['worse']} | "
            f"{item['mean_score_delta']:+.3f} | {regressions} |"
        )
    lines.extend(
        [
            "",
            f"Conservative checklist agreement: {quality['agreement']:.1%}.",
            "",
            "## Generation cost",
            "",
            "| Condition | Credits | Ratio vs A | Process leaks |",
            "|---|---:|---:|---:|",
        ]
    )
    for condition in ("A", "B", "C", "D"):
        lines.append(
            f"| {condition} | {cost['end_to_end_credits'][condition]:.6f} | "
            f"{cost['ratios_vs_A'][condition]:.3f}× | "
            f"{report['process_leaks'][condition]['count']} |"
        )
    lines.extend(["", cost["scope"], "", "## Gates", ""])
    for name, item in report["gate"]["pair_gates"].items():
        lines.append(
            f"### {name}: {'PASS' if item['passed'] else 'FAIL'}"
        )
        lines.append("")
        for check, passed in item["checks"].items():
            lines.append(f"- {'PASS' if passed else 'FAIL'} — {check}")
        lines.append("")
    a_usage = cost["usage"]["A"]
    b_usage = cost["usage"]["B"]
    judge_execution = report["execution"]["judges"]
    lines.extend(
        [
            "## Root cause and non-trivial implications",
            "",
            "The exact `請自評` treatment did more work without improving the "
            "decision set. Relative to A, B used "
            f"{b_usage['reasoning_output_tokens'] / a_usage['reasoning_output_tokens']:.2f}× "
            "reasoning tokens and "
            f"{b_usage['output_tokens'] / a_usage['output_tokens']:.2f}× "
            "output tokens, cost 15.7% more, and increased aggregate burden by "
            "one. In SE-04 its rewrite dropped controls already present in A, "
            "including explicit expiry for exceptions. Self-review is not "
            "monotonic accumulation; revision can delete good constraints.",
            "",
            "Structured private self-evaluation was more efficient than the "
            "generic instruction, but still did not clear the preregistered "
            "effect threshold. C tied A at burden 10, with two cases better, one "
            "unchanged, and one worse, while costing 3.2% more. This is a mixed "
            "screening signal, not evidence that quality becomes much better.",
            "",
            "The Luna pre-mortem questions successfully surfaced relevant "
            "issues, but discovery did not guarantee adoption. In SE-02 a Luna "
            "question explicitly asked how the conflicting export/deletion "
            "outcome would be communicated to the customer; D's final answer "
            "still omitted a concrete customer-visible outcome and received a "
            "missed-hard-constraint flag. The bottleneck moved from issue search "
            "to main-model disposition.",
            "",
            "Two-candidate judging was operationally more reliable than the "
            "earlier five-candidate format: "
            f"{judge_execution['first_attempt_valid']}/"
            f"{judge_execution['calls']} calls were valid on the first attempt "
            f"and {judge_execution['eventually_valid']}/"
            f"{judge_execution['calls']} eventually completed. However, total "
            "scores remained opponent- and judge-sensitive; one SE-03 B/C judge "
            "scored both candidates 20 while the other scored both 0. The "
            "checklist burden, not the total score, remains the primary signal.",
            "",
        ]
    )
    lines.extend(
        [
            "## Claim boundary",
            "",
            report["claim_boundary"],
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def summarize(workspace, rate_card_path, output_json=None, output_md=None):
    workspace = Path(workspace)
    records = load_records(workspace)
    judges = load_jsonl(workspace / "judge-records.jsonl")
    case_results, agreement = _decode(judges)
    quality = comparison_metrics(case_results, agreement)
    cost = cost_metrics(records, load_credit_rate_card(rate_card_path))
    leaks = process_leaks(records)
    report = {
        "experiment_id": "private-self-eval-pilot-20260723",
        "stage": "fresh-pilot",
        "case_ids": sorted(case_results),
        "quality": quality,
        "cost": cost,
        "process_leaks": leaks,
        "execution": {
            "generation": execution_metrics(records),
            "judges": execution_metrics(judges),
        },
        "claim_boundary": (
            "Fresh four-case diagnostic pilot with one generation sample per "
            "condition and two judges per planned pair. It can screen mechanisms "
            "but cannot establish a general quality improvement or stable effect "
            "size without a larger fresh confirmation."
        ),
    }
    report["gate"] = gate(quality, cost, leaks)
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
