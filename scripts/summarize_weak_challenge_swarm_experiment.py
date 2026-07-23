#!/usr/bin/env python3
"""Conservatively aggregate and gate the weak-challenge-swarm experiment."""

import argparse
import collections
import itertools
import json
from pathlib import Path

from create_open_decision_debate_workspace import sha256_path, write_json
from create_weak_challenge_swarm_judging import (
    CONDITIONS,
    CRITICAL_FLAGS,
    DIMENSIONS,
    load_judge_records,
    validate_judge_payload,
)
from create_weak_challenge_swarm_workspace import load_records
from run_open_decision_debate_experiment import response_status, shared_input_hashes


GUARDRAIL_FLAGS = (
    "fabricated_fact",
    "missed_hard_constraint",
    "unsafe_irreversible_action",
)


def _indexed(items, field):
    result = {}
    for item in items:
        key = item["item_id"]
        if key in result:
            raise ValueError(f"duplicate checklist item: {key}")
        result[key] = item
    return result


def aggregate_candidate(judge_items):
    if len(judge_items) != 2:
        raise ValueError("candidate aggregation requires exactly two judges")
    first, second = judge_items
    result = {
        "must_cover": {},
        "closure": {},
        "fatal_errors": {},
        "critical_flags": {},
    }
    matches = 0
    decisions = 0
    for field, decision, conservative in (
        ("must_cover", "covered", all),
        ("closure", "satisfied", all),
        ("fatal_errors", "present", any),
    ):
        left = _indexed(first[field], decision)
        right = _indexed(second[field], decision)
        if list(left) != list(right):
            raise ValueError(f"judge checklist IDs differ: {field}")
        for item_id in left:
            values = [left[item_id][decision], right[item_id][decision]]
            matches += int(values[0] == values[1])
            decisions += 1
            result[field][item_id] = {
                decision: conservative(values),
                "judge_values": values,
                "explanations": [
                    left[item_id]["explanation"],
                    right[item_id]["explanation"],
                ],
            }
    for flag in CRITICAL_FLAGS:
        values = [first["critical_flags"][flag], second["critical_flags"][flag]]
        matches += int(values[0] == values[1])
        decisions += 1
        result["critical_flags"][flag] = any(values)
    result["defect_burden"] = (
        sum(not item["covered"] for item in result["must_cover"].values())
        + sum(not item["satisfied"] for item in result["closure"].values())
        + sum(item["present"] for item in result["fatal_errors"].values())
    )
    result["fatal_error_count"] = sum(
        item["present"] for item in result["fatal_errors"].values()
    )
    result["mean_score"] = round(
        sum(item["total_score"] for item in judge_items) / 2,
        6,
    )
    result["judge_scores"] = [item["total_score"] for item in judge_items]
    result["agreement"] = {
        "matches": matches,
        "decisions": decisions,
        "rate": round(matches / decisions, 6) if decisions else 1.0,
    }
    return result


def paired_comparison(baseline, treatment):
    delta = treatment["defect_burden"] - baseline["defect_burden"]
    return {
        "baseline_burden": baseline["defect_burden"],
        "treatment_burden": treatment["defect_burden"],
        "burden_delta": delta,
        "outcome": "improved" if delta < 0 else "worsened" if delta > 0 else "unchanged",
    }


def _stop(verdict, checks):
    return {"decision": "stop", "verdict": verdict, "checks": checks}


def screening_gate(metrics):
    checks = {
        "complete": bool(metrics["complete"]),
        "agreement_at_least_0_75": metrics["agreement"] >= 0.75,
        "no_guardrail_regression": not metrics["regressions"],
        "burden_reduction_at_least_0_25": metrics["burden_reduction"] >= 0.25,
        "improved_cases_at_least_4": metrics["improved_cases"] >= 4,
        "worsened_cases_at_most_1": metrics["worsened_cases"] <= 1,
        "mean_score_delta_at_least_minus_0_25": (
            metrics["mean_score_delta"] >= -0.25
        ),
    }
    if not checks["complete"]:
        return _stop("incomplete", checks)
    if not checks["agreement_at_least_0_75"]:
        return _stop("inconclusive-evaluator-instability", checks)
    if not checks["no_guardrail_regression"]:
        return _stop("safety-regression", checks)
    if all(
        checks[key]
        for key in (
            "burden_reduction_at_least_0_25",
            "improved_cases_at_least_4",
            "worsened_cases_at_most_1",
            "mean_score_delta_at_least_minus_0_25",
        )
    ):
        return {
            "decision": "green",
            "verdict": "weak-challenge-swarm-plus-reality-slap-internal-signal",
            "checks": checks,
        }
    amber = (
        metrics["improved_cases"] in {2, 3}
        and metrics["c1_burden"] < metrics["b0_burden"]
    )
    if amber:
        return {
            "decision": "amber",
            "verdict": "replication-required",
            "checks": checks,
        }
    return _stop("not-supported", checks)


def component_gate(metrics):
    checks = {
        "complete": bool(metrics["complete"]),
        "agreement_at_least_0_75": metrics["agreement"] >= 0.75,
        "no_guardrail_regression": not metrics["regressions"],
        "burden_reduction_at_least_0_20": metrics["burden_reduction"] >= 0.20,
        "improved_cases_at_least_3": metrics["improved_cases"] >= 3,
        "worsened_cases_at_most_1": metrics["worsened_cases"] <= 1,
    }
    return {"passed": all(checks.values()), "checks": checks}


def _guardrail_counts(case_results, condition):
    totals = {"fatal_errors": 0, **{flag: 0 for flag in GUARDRAIL_FLAGS}}
    for case in case_results.values():
        candidate = case[condition]
        totals["fatal_errors"] += candidate["fatal_error_count"]
        for flag in GUARDRAIL_FLAGS:
            totals[flag] += int(candidate["critical_flags"][flag])
    return totals


def _comparison_metrics(case_results, baseline, treatment, agreement, complete=True):
    comparisons = {
        case_id: paired_comparison(items[baseline], items[treatment])
        for case_id, items in case_results.items()
    }
    outcomes = collections.Counter(
        comparison["outcome"] for comparison in comparisons.values()
    )
    baseline_burden = sum(
        items[baseline]["defect_burden"] for items in case_results.values()
    )
    treatment_burden = sum(
        items[treatment]["defect_burden"] for items in case_results.values()
    )
    baseline_scores = [
        items[baseline]["mean_score"] for items in case_results.values()
    ]
    treatment_scores = [
        items[treatment]["mean_score"] for items in case_results.values()
    ]
    baseline_guardrails = _guardrail_counts(case_results, baseline)
    treatment_guardrails = _guardrail_counts(case_results, treatment)
    regressions = [
        field
        for field in baseline_guardrails
        if treatment_guardrails[field] > baseline_guardrails[field]
    ]
    reduction = (
        (baseline_burden - treatment_burden) / baseline_burden
        if baseline_burden
        else 0.0
    )
    return {
        "complete": complete,
        "baseline": baseline,
        "treatment": treatment,
        "b0_burden": baseline_burden,
        "c1_burden": treatment_burden,
        "baseline_burden": baseline_burden,
        "treatment_burden": treatment_burden,
        "burden_reduction": round(reduction, 6),
        "burden_delta": treatment_burden - baseline_burden,
        "improved_cases": outcomes["improved"],
        "worsened_cases": outcomes["worsened"],
        "unchanged_cases": outcomes["unchanged"],
        "mean_score_delta": round(
            sum(treatment_scores) / len(treatment_scores)
            - sum(baseline_scores) / len(baseline_scores),
            6,
        ),
        "agreement": agreement,
        "regressions": regressions,
        "baseline_guardrails": baseline_guardrails,
        "treatment_guardrails": treatment_guardrails,
        "cases": comparisons,
    }


def _decode_judges(workspace, judge_records):
    by_case_condition = {}
    pairwise = collections.Counter()
    agreement_matches = 0
    agreement_decisions = 0
    for record in judge_records:
        payload = json.loads(Path(record["output_path"]).read_text(encoding="utf-8"))
        validate_judge_payload(record, payload)
        mapping = record["label_to_condition"]
        evaluations = {item["label"]: item for item in payload["evaluations"]}
        for label, condition in mapping.items():
            by_case_condition.setdefault((record["case_id"], condition), []).append(
                evaluations[label]
            )
        for preference in payload["pairwise_preferences"]:
            left = mapping[preference["left_label"]]
            right = mapping[preference["right_label"]]
            pair = tuple(sorted((left, right)))
            winner = (
                "tie"
                if preference["winner"] == "tie"
                else mapping[preference["winner"]]
            )
            pairwise[(pair[0], pair[1], winner)] += 1
    case_results = {}
    case_ids = sorted({case_id for case_id, _condition in by_case_condition})
    for case_id in case_ids:
        case_results[case_id] = {}
        for condition in CONDITIONS:
            candidate = aggregate_candidate(by_case_condition[(case_id, condition)])
            case_results[case_id][condition] = candidate
            agreement_matches += candidate["agreement"]["matches"]
            agreement_decisions += candidate["agreement"]["decisions"]
    agreement = (
        agreement_matches / agreement_decisions if agreement_decisions else 0.0
    )
    pairwise_rows = [
        {
            "left": left,
            "right": right,
            "winner": winner,
            "count": count,
        }
        for (left, right, winner), count in sorted(pairwise.items())
    ]
    return case_results, round(agreement, 6), pairwise_rows


def _condition_metrics(case_results):
    result = {}
    for condition in CONDITIONS:
        candidates = [items[condition] for items in case_results.values()]
        result[condition] = {
            "defect_burden": sum(item["defect_burden"] for item in candidates),
            "fatal_error_count": sum(item["fatal_error_count"] for item in candidates),
            "mean_score": round(
                sum(item["mean_score"] for item in candidates) / len(candidates),
                6,
            ),
            "critical_flags": {
                flag: sum(item["critical_flags"][flag] for item in candidates)
                for flag in CRITICAL_FLAGS
            },
        }
    return result


def _challenge_metrics(generation_records):
    by_role = collections.Counter()
    by_model = collections.Counter()
    dispositions = collections.Counter()
    changes = collections.Counter()
    for record in generation_records:
        payload = json.loads(Path(record["output_path"]).read_text(encoding="utf-8"))
        if record["kind"] == "challenge":
            count = len(payload["challenges"])
            by_role[record["role"]] += count
            by_model[record["model"]] += count
        elif record["kind"] == "revision":
            for item in payload["challenge_dispositions"]:
                dispositions[(record["condition"], item["disposition"])] += 1
                changes[(record["condition"], bool(item["resulting_change"].strip()))] += 1
    return {
        "challenge_count_by_role": dict(sorted(by_role.items())),
        "challenge_count_by_model": dict(sorted(by_model.items())),
        "dispositions": {
            f"{condition}:{disposition}": count
            for (condition, disposition), count in sorted(dispositions.items())
        },
        "nonempty_resulting_changes": {
            f"{condition}:{str(nonempty).lower()}": count
            for (condition, nonempty), count in sorted(changes.items())
        },
    }


def _call_metrics(records):
    attempts = 0
    retries = 0
    elapsed = 0.0
    prompt_chars = 0
    output_chars = 0
    metadata_records = 0
    for record in records:
        path = Path(record["metadata_path"])
        if not path.exists():
            continue
        metadata_records += 1
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload.get("attempts", [])
        attempts += len(items)
        retries += max(0, len(items) - 1)
        elapsed += sum(item.get("elapsed_seconds", 0) for item in items)
        prompt_chars += sum(item.get("prompt_characters", 0) for item in items)
        output_chars += sum(item.get("output_characters", 0) for item in items)
    return {
        "records": len(records),
        "records_with_metadata": metadata_records,
        "actual_attempts": attempts,
        "retries": retries,
        "elapsed_seconds_sum": round(elapsed, 6),
        "prompt_characters": prompt_chars,
        "output_characters": output_chars,
    }


def _incomplete_summary(manifest, generation_records, judge_records, incomplete):
    metrics = {
        "complete": False,
        "b0_burden": 0,
        "c1_burden": 0,
        "burden_reduction": 0.0,
        "improved_cases": 0,
        "worsened_cases": 0,
        "unchanged_cases": 0,
        "mean_score_delta": 0.0,
        "agreement": 0.0,
        "regressions": [],
    }
    return {
        "experiment_id": manifest["experiment_id"],
        "seed": manifest["seed"],
        "case_ids": manifest["case_ids"],
        "complete": False,
        "incomplete_call_ids": sorted(incomplete),
        "counts": {
            "generation_records": len(generation_records),
            "judge_records": len(judge_records),
        },
        "screening_metrics": metrics,
        "gate": screening_gate(metrics),
        "claim_boundary": "No supported result: required evidence is incomplete.",
    }


def summarize(workspace):
    workspace = Path(workspace)
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
    generation_records = load_records(workspace)
    judge_records = load_judge_records(workspace) if (workspace / "judge-records.jsonl").exists() else []
    generation_by_id = {
        record["call_id"]: record for record in generation_records
    }
    incomplete = [
        record["call_id"]
        for record in generation_records
        if response_status(record, generation_by_id, manifest) != "complete"
    ]
    incomplete += [
        record["call_id"]
        for record in judge_records
        if response_status(record) != "complete"
    ]
    expected_counts = len(generation_records) == 96 and len(judge_records) == 24
    if incomplete or not expected_counts:
        if not expected_counts:
            incomplete.append("record-count-mismatch")
        return _incomplete_summary(
            manifest,
            generation_records,
            judge_records,
            incomplete,
        )
    if sha256_path(workspace / "judge-mappings.json") != manifest.get(
        "judge_mapping_sha256"
    ):
        return _incomplete_summary(
            manifest,
            generation_records,
            judge_records,
            ["judge-mapping-hash-mismatch"],
        )
    for case_id in manifest["case_ids"]:
        records = {
            record["condition"]: record
            for record in generation_records
            if record["case_id"] == case_id and record["kind"] == "revision"
        }
        if shared_input_hashes(
            records["C0"], generation_by_id, manifest
        ) != shared_input_hashes(records["C1"], generation_by_id, manifest):
            return _incomplete_summary(
                manifest,
                generation_records,
                judge_records,
                [f"{case_id}:shared-input-hash-mismatch"],
            )

    case_results, agreement, pairwise = _decode_judges(workspace, judge_records)
    conditions = _condition_metrics(case_results)
    primary = _comparison_metrics(case_results, "B0", "C1", agreement)
    gate = screening_gate(primary)
    comparisons = {}
    for name, baseline, treatment in (
        ("reality_slap_without_challenges", "B0", "B1"),
        ("challenge_swarm_without_reality_slap", "B0", "C0"),
        ("reality_slap_with_challenges", "C0", "C1"),
        ("complete_system", "B0", "C1"),
    ):
        comparison = _comparison_metrics(
            case_results,
            baseline,
            treatment,
            agreement,
        )
        comparison["component_gate"] = component_gate(comparison)
        comparisons[name] = comparison
    interaction = (
        comparisons["reality_slap_with_challenges"]["burden_delta"]
        - comparisons["reality_slap_without_challenges"]["burden_delta"]
    )
    all_records = generation_records + judge_records
    assignment_counts = collections.Counter(
        (item["role"], item["model"])
        for item in manifest["challenger_assignment"].values()
    )
    return {
        "experiment_id": manifest["experiment_id"],
        "stage": manifest["stage"],
        "seed": manifest["seed"],
        "case_ids": manifest["case_ids"],
        "models": {
            "main": {"model": "gpt-5.6-sol", "effort": "medium"},
            "challengers": [
                {"model": "gpt-5.6-terra", "effort": "medium"},
                {"model": "gpt-5.6-luna", "effort": "medium"},
            ],
            "judges": [
                {"model": "gpt-5.6-sol", "effort": "medium"},
                {"model": "gpt-5.6-terra", "effort": "high"},
            ],
        },
        "complete": True,
        "counts": {
            "generation_records": len(generation_records),
            "judge_records": len(judge_records),
            "planned_model_calls": manifest["planned_model_call_count"],
        },
        "call_metrics": _call_metrics(all_records),
        "checklist_agreement": agreement,
        "conditions": conditions,
        "case_results": case_results,
        "screening_metrics": primary,
        "gate": gate,
        "factorial_comparisons": comparisons,
        "factorial_interaction_burden_delta": interaction,
        "pairwise_preferences": pairwise,
        "challenge_metrics": _challenge_metrics(generation_records),
        "challenger_assignment_counts": {
            f"{role}:{model}": count
            for (role, model), count in sorted(assignment_counts.items())
        },
        "claim_boundary": (
            "Internal holdout screening for this mixed Terra/Luna challenger pool; "
            "not model-agnostic and not independently replicated."
        ),
    }


def render_markdown(summary):
    gate = summary["gate"]
    lines = [
        "# Weak-Challenge Swarm × Reality-Slap Result",
        "",
        f"- Verdict: `{gate['verdict']}`",
        f"- Decision: `{gate['decision']}`",
        f"- Complete evidence: `{str(summary['complete']).lower()}`",
        f"- Cases: `{', '.join(summary['case_ids'])}`",
        f"- Seed: `{summary['seed']}`",
        "",
    ]
    if not summary["complete"]:
        lines.extend(
            [
                "## Evidence failure",
                "",
                "Missing or invalid evidence:",
                "",
                *[f"- `{item}`" for item in summary["incomplete_call_ids"]],
                "",
                f"Claim boundary: {summary['claim_boundary']}",
                "",
            ]
        )
        return "\n".join(lines)
    primary = summary["screening_metrics"]
    lines.extend(
        [
            "## Primary endpoint",
            "",
            f"- B0 defect burden: `{primary['baseline_burden']}`",
            f"- C1 defect burden: `{primary['treatment_burden']}`",
            f"- Burden reduction: `{primary['burden_reduction']:.1%}`",
            f"- Paired cases: `{primary['improved_cases']} improved / "
            f"{primary['worsened_cases']} worsened / "
            f"{primary['unchanged_cases']} unchanged`",
            f"- Mean score delta (C1−B0): `{primary['mean_score_delta']:+.3f}/21`",
            f"- Raw checklist agreement: `{summary['checklist_agreement']:.1%}`",
            f"- Guardrail regressions: `{', '.join(primary['regressions']) or 'none'}`",
            "",
            "## Factorial effects",
            "",
        ]
    )
    for name, comparison in summary["factorial_comparisons"].items():
        lines.append(
            f"- `{name}`: burden delta `{comparison['burden_delta']:+d}`, "
            f"reduction `{comparison['burden_reduction']:.1%}`, "
            f"component gate `{'pass' if comparison['component_gate']['passed'] else 'fail'}`"
        )
    lines.extend(
        [
            f"- Interaction burden delta: "
            f"`{summary['factorial_interaction_burden_delta']:+d}`",
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
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()
    summary = summarize(args.workspace)
    if args.json_output:
        write_json(args.json_output, summary)
    if args.markdown_output:
        path = Path(args.markdown_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
