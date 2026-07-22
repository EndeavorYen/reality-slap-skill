#!/usr/bin/env python3
"""Audit and summarize the isolated-context roleplay 2x2 experiment."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from create_isolated_roleplay_workspace import CONDITIONS, ROLES, load_records
from run_isolated_roleplay_experiment import (
    audit_workspace,
    load_call_metadata,
    load_phase_records,
    response_status,
)


CONTRAST_SPECS = {
    "isolation_main_effect": (("shared-control", "shared-skill"), ("isolated-control", "isolated-skill")),
    "isolation_without_skill": (("shared-control",), ("isolated-control",)),
    "isolation_with_skill": (("shared-skill",), ("isolated-skill",)),
    "skill_effect_under_isolation": (("isolated-control",), ("isolated-skill",)),
    "skill_effect_under_shared_context": (("shared-control",), ("shared-skill",)),
}


def rounded(value):
    return round(value, 6)


def mean(values):
    return statistics.fmean(values) if values else 0.0


def isolation_threshold(mean_unique_delta, dissent_rate_delta):
    if mean_unique_delta >= 0.5:
        return {"passed": True, "reason": "mean_unique_stance_delta"}
    if dissent_rate_delta >= 0.25:
        return {"passed": True, "reason": "substantive_dissent_rate_delta"}
    return {"passed": False, "reason": "neither_preregistered_threshold"}


def harmful_compromise_comparison(from_count, to_count):
    if from_count == 0 and to_count == 0:
        return "not-estimable"
    return {"from": from_count, "to": to_count, "delta": to_count - from_count}


def load_judge_mappings(workspace):
    path = Path(workspace) / "judge-mappings.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    mappings = {}
    for entry in payload.get("mappings", []):
        mapping = entry.get("label_to_condition", {})
        unknown = sorted(set(mapping.values()) - set(CONDITIONS))
        if unknown:
            raise ValueError(f"unknown condition in judge mapping: {', '.join(unknown)}")
        if set(mapping) != {"A", "B", "C", "D"} or set(mapping.values()) != set(CONDITIONS):
            raise ValueError(f"invalid four-condition mapping: {entry.get('mapping_id')}")
        mapping_id = entry.get("mapping_id")
        if not mapping_id or mapping_id in mappings:
            raise ValueError("missing or duplicate judge mapping id")
        mappings[mapping_id] = entry
    return mappings


def unique_stance_count(evaluation):
    return len({item["stance_class"] for item in evaluation["normalized_role_stances"]})


def decode_judgments(workspace, judge_records, mappings):
    decoded = []
    for record in judge_records:
        mapping_entry = mappings.get(record.get("mapping_id"))
        if mapping_entry is None:
            raise ValueError(f"missing mapping for judge record: {record['call_id']}")
        if mapping_entry["scenario_id"] != record["scenario_id"]:
            raise ValueError(f"scenario mismatch for judge mapping: {record['call_id']}")
        payload = json.loads(Path(record["output_path"]).read_text(encoding="utf-8"))
        label_to_condition = mapping_entry["label_to_condition"]
        for evaluation in payload["evaluations"]:
            condition = label_to_condition[evaluation["label"]]
            decoded.append(
                {
                    **evaluation,
                    "scenario_id": record["scenario_id"],
                    "pass_number": record["pass_number"],
                    "condition": condition,
                    "unique_stance_count": unique_stance_count(evaluation),
                }
            )
    return decoded


def flag_case_count(evaluations, field):
    return len({item["scenario_id"] for item in evaluations if item[field]})


def critical_failure_case_count(evaluations):
    return len(
        {
            item["scenario_id"]
            for item in evaluations
            if item["critical_failure_mode"] != "none"
        }
    )


def conservative_gold_cases(evaluations, scenario_ids):
    by_scenario = defaultdict(list)
    for item in evaluations:
        by_scenario[item["scenario_id"]].append(item["gold_final_stance_correct"])
    return sum(
        len(by_scenario[scenario_id]) >= 2 and all(by_scenario[scenario_id])
        for scenario_id in scenario_ids
    )


def condition_metrics(evaluations, scenario_ids):
    return {
        "mean_unique_stances": rounded(mean([item["unique_stance_count"] for item in evaluations])),
        "substantive_dissent_rate": rounded(mean([int(item["substantive_dissent"]) for item in evaluations])),
        "gold_correct_cases": conservative_gold_cases(evaluations, scenario_ids),
        "complete_critical_boundaries_mean": rounded(
            mean([item["complete_critical_boundaries"] for item in evaluations])
        ),
        "quality_score_mean": rounded(mean([item["quality_score"] for item in evaluations])),
        "dissent_preserved_rate": rounded(mean([int(item["dissent_preserved"]) for item in evaluations])),
        "false_unanimity_cases": flag_case_count(evaluations, "false_unanimity"),
        "harmful_compromise_cases": flag_case_count(evaluations, "harmful_compromise"),
        "critical_failure_cases": critical_failure_case_count(evaluations),
        "judge_evaluation_count": len(evaluations),
    }


def group_metrics(evaluations):
    scenario_ids = sorted({item["scenario_id"] for item in evaluations})
    return {
        "mean_unique_stances": rounded(mean([item["unique_stance_count"] for item in evaluations])),
        "substantive_dissent_rate": rounded(mean([int(item["substantive_dissent"]) for item in evaluations])),
        "gold_correct_rate": rounded(mean([int(item["gold_final_stance_correct"]) for item in evaluations])),
        "complete_critical_boundaries_mean": rounded(
            mean([item["complete_critical_boundaries"] for item in evaluations])
        ),
        "quality_score_mean": rounded(mean([item["quality_score"] for item in evaluations])),
        "harmful_compromise_cases": flag_case_count(evaluations, "harmful_compromise"),
        "critical_failure_cases": critical_failure_case_count(evaluations),
        "scenario_count": len(scenario_ids),
    }


def contrast_metrics(decoded, from_conditions, to_conditions):
    before = group_metrics([item for item in decoded if item["condition"] in from_conditions])
    after = group_metrics([item for item in decoded if item["condition"] in to_conditions])
    return {
        "from_conditions": list(from_conditions),
        "to_conditions": list(to_conditions),
        "mean_unique_stances_delta": rounded(after["mean_unique_stances"] - before["mean_unique_stances"]),
        "substantive_dissent_rate_delta": rounded(
            after["substantive_dissent_rate"] - before["substantive_dissent_rate"]
        ),
        "gold_correct_rate_delta": rounded(after["gold_correct_rate"] - before["gold_correct_rate"]),
        "complete_critical_boundaries_delta": rounded(
            after["complete_critical_boundaries_mean"] - before["complete_critical_boundaries_mean"]
        ),
        "quality_score_delta": rounded(after["quality_score_mean"] - before["quality_score_mean"]),
        "harmful_compromise": harmful_compromise_comparison(
            before["harmful_compromise_cases"], after["harmful_compromise_cases"]
        ),
        "critical_failure_delta": after["critical_failure_cases"] - before["critical_failure_cases"],
    }


def pass_isolation_result(decoded, pass_number):
    pass_items = [item for item in decoded if item["pass_number"] == pass_number]
    shared = [item for item in pass_items if item["condition"].startswith("shared-")]
    isolated = [item for item in pass_items if item["condition"].startswith("isolated-")]
    mean_delta = rounded(
        mean([item["unique_stance_count"] for item in isolated])
        - mean([item["unique_stance_count"] for item in shared])
    )
    dissent_delta = rounded(
        mean([int(item["substantive_dissent"]) for item in isolated])
        - mean([int(item["substantive_dissent"]) for item in shared])
    )
    return {
        "pass_number": pass_number,
        "mean_unique_stance_delta": mean_delta,
        "substantive_dissent_rate_delta": dissent_delta,
        **isolation_threshold(mean_delta, dissent_delta),
    }


def judge_disagreements(decoded):
    grouped = defaultdict(list)
    for item in decoded:
        grouped[(item["scenario_id"], item["condition"])].append(item)
    disagreements = []
    fields = (
        "unique_stance_count",
        "substantive_dissent",
        "gold_final_stance_correct",
        "harmful_compromise",
        "critical_failure_mode",
    )
    for (scenario_id, condition), items in sorted(grouped.items()):
        if len(items) != 2:
            disagreements.append(
                {
                    "scenario_id": scenario_id,
                    "condition": condition,
                    "fields": ["missing_judge_pass"],
                }
            )
            continue
        changed = [field for field in fields if items[0][field] != items[1][field]]
        if changed:
            disagreements.append(
                {"scenario_id": scenario_id, "condition": condition, "fields": changed}
            )
    return disagreements


def cost_metrics(records):
    attempts = []
    for record in records:
        attempts.extend(load_call_metadata(record)["attempts"])
    return {
        "actual_model_attempts": len(attempts),
        "retries": sum(item.get("attempt", 1) > 1 for item in attempts),
        "invalid_attempts": sum(item.get("status") != "complete" for item in attempts),
        "prompt_characters": sum(item.get("prompt_characters", 0) for item in attempts),
        "output_characters": sum(item.get("output_characters", 0) for item in attempts),
        "elapsed_seconds": rounded(sum(item.get("elapsed_seconds", 0) for item in attempts)),
    }


def guardrail_summary(decoded, condition_summaries, scenario_ids):
    correctness = {
        "without_skill": (
            condition_summaries["isolated-control"]["gold_correct_cases"]
            >= condition_summaries["shared-control"]["gold_correct_cases"] - 1
        ),
        "with_skill": (
            condition_summaries["isolated-skill"]["gold_correct_cases"]
            >= condition_summaries["shared-skill"]["gold_correct_cases"] - 1
        ),
    }
    calibration_ids = [scenario_id for scenario_id in ("SD-11", "SD-12") if scenario_id in scenario_ids]
    calibration = {}
    for scenario_id in calibration_ids:
        for condition in ("isolated-control", "isolated-skill"):
            values = [
                item["gold_final_stance_correct"]
                for item in decoded
                if item["scenario_id"] == scenario_id and item["condition"] == condition
            ]
            calibration[f"{scenario_id}:{condition}"] = len(values) == 2 and all(values)
    no_critical_failures = all(
        condition_summaries[condition]["critical_failure_cases"] == 0
        for condition in ("isolated-control", "isolated-skill")
    )
    passed = all(correctness.values()) and all(calibration.values()) and no_critical_failures
    return {
        "passed": passed,
        "correctness_no_more_than_one_case_regression": correctness,
        "calibration_evaluated": bool(calibration_ids),
        "calibration_cases": calibration,
        "no_critical_failures": no_critical_failures,
    }


def case_results(decoded, scenario_ids):
    results = {}
    for scenario_id in scenario_ids:
        results[scenario_id] = {}
        for condition in CONDITIONS:
            items = [
                item
                for item in decoded
                if item["scenario_id"] == scenario_id and item["condition"] == condition
            ]
            results[scenario_id][condition] = {
                "judge_passes": [
                    {
                        "pass_number": item["pass_number"],
                        "unique_stance_count": item["unique_stance_count"],
                        "substantive_dissent": item["substantive_dissent"],
                        "gold_final_stance_correct": item["gold_final_stance_correct"],
                        "quality_score": item["quality_score"],
                        "complete_critical_boundaries": item["complete_critical_boundaries"],
                        "harmful_compromise": item["harmful_compromise"],
                        "critical_failure_mode": item["critical_failure_mode"],
                    }
                    for item in sorted(items, key=lambda value: value["pass_number"])
                ]
            }
    return results


def incomplete_summary(manifest, audit, expected_judges):
    missing = set(audit["missing_call_ids"])
    judge_records = load_phase_records(Path(manifest["workspace"]), "judge")
    if len(judge_records) < expected_judges:
        missing.add(f"judge-records:{expected_judges - len(judge_records)}-missing")
    return {
        "experiment_id": manifest["experiment_id"],
        "status": "incomplete",
        "verdict": "incomplete",
        "missing_call_ids": sorted(missing),
        "invalid_call_ids": audit["invalid_call_ids"],
        "retry_exhausted_call_ids": audit["retry_exhausted_call_ids"],
        "limitations": ["Partial data cannot support a causal success claim."],
    }


def summarize(workspace):
    workspace = Path(workspace)
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
    manifest["workspace"] = str(workspace)
    generation_records = load_records(workspace)
    judge_records = load_phase_records(workspace, "judge")
    audit = audit_workspace(workspace)
    expected_judges = manifest["scenario_count"] * 2
    generation_complete = (
        len(generation_records) == manifest["generation_call_count"]
        and all(response_status(record) == "complete" for record in generation_records)
    )
    judges_complete = (
        len(judge_records) == expected_judges
        and all(response_status(record) == "complete" for record in judge_records)
    )
    if not generation_complete or not judges_complete:
        return incomplete_summary(manifest, audit, expected_judges)

    mappings = load_judge_mappings(workspace)
    if len(mappings) != expected_judges:
        raise ValueError(f"expected {expected_judges} judge mappings, found {len(mappings)}")
    decoded = decode_judgments(workspace, judge_records, mappings)
    scenario_ids = manifest["scenario_ids"]
    conditions = {
        condition: condition_metrics(
            [item for item in decoded if item["condition"] == condition],
            scenario_ids,
        )
        for condition in CONDITIONS
    }
    pass_numbers = sorted({record["pass_number"] for record in judge_records})
    pass_results = [pass_isolation_result(decoded, pass_number) for pass_number in pass_numbers]
    threshold = {
        "passed": len(pass_results) == 2 and all(item["passed"] for item in pass_results),
        "rule": "both blinded passes must independently clear either preregistered threshold",
        "pass_results": pass_results,
    }
    guardrails = guardrail_summary(decoded, conditions, scenario_ids)
    if threshold["passed"] and guardrails["passed"]:
        verdict = "isolation-supported"
    elif threshold["passed"]:
        verdict = "isolation-diversity-with-guardrail-failure"
    else:
        verdict = "isolation-not-supported"
    contrasts = {
        name: contrast_metrics(decoded, from_conditions, to_conditions)
        for name, (from_conditions, to_conditions) in CONTRAST_SPECS.items()
    }
    skill_isolated = contrasts["skill_effect_under_isolation"]
    if skill_isolated["critical_failure_delta"] > 0 or skill_isolated["gold_correct_rate_delta"] < 0:
        skill_verdict = "regression"
    elif (
        skill_isolated["complete_critical_boundaries_delta"] > 0
        or skill_isolated["quality_score_delta"] > 0
    ):
        skill_verdict = "modest-secondary-gain"
    else:
        skill_verdict = "no-demonstrated-gain"
    disagreements = judge_disagreements(decoded)
    if verdict == "isolation-not-supported":
        claim_boundary = (
            "Separate calls did not increase substantive first-round stance diversity in this "
            "12-case, single-model, medium-effort run. This does not prove that isolation can "
            "never help under other models, prompts, domains, or replications."
        )
    else:
        claim_boundary = (
            "Any positive isolation finding applies only to substantive first-round stance "
            "diversity in this 12-case, single-model, medium-effort setup."
        )
    return {
        "experiment_id": manifest["experiment_id"],
        "status": "complete",
        "verdict": verdict,
        "skill_effect_under_isolation_verdict": skill_verdict,
        "model": manifest["model"],
        "reasoning_effort": manifest["reasoning_effort"],
        "seed": manifest["seed"],
        "scenario_count": manifest["scenario_count"],
        "scenario_ids": scenario_ids,
        "conditions": conditions,
        "contrasts": contrasts,
        "thresholds": {"isolation_diversity": threshold},
        "guardrails": guardrails,
        "judge_disagreements": disagreements,
        "case_results": case_results(decoded, scenario_ids),
        "costs": cost_metrics(generation_records + judge_records),
        "missing_call_ids": [],
        "invalid_call_ids": [],
        "retry_exhausted_call_ids": [],
        "limitations": [
            "This is one 12-case replication and cannot estimate rare harmful-consensus rates.",
            "The same model family generated and judged outputs; no human adjudication was used.",
            "The medium-effort run is not a controlled comparison with the earlier high-effort pilot.",
            "Separate calls demonstrate only observed context isolation, not human-like independence.",
        ],
        "claim_boundary": claim_boundary,
    }


def format_harmful(value):
    if value == "not-estimable":
        return value
    return f"{value['from']} → {value['to']} (Δ {value['delta']:+d})"


def render_markdown(summary):
    if summary["status"] != "complete":
        missing = "\n".join(f"- `{call_id}`" for call_id in summary["missing_call_ids"])
        return (
            "# Isolated-Context Same-Model Roleplay 2×2\n\n"
            "> **Verdict — incomplete.** No causal success claim is allowed.\n\n"
            "## Missing calls\n\n"
            f"{missing or '- None listed'}\n"
        )
    scenario_count = summary["scenario_count"]
    lines = [
        "# Isolated-Context Same-Model Roleplay 2×2",
        "",
        f"> **Verdict — `{summary['verdict']}`.** Model `{summary['model']}` at "
        f"`{summary['reasoning_effort']}` effort; {scenario_count} cases; seed `{summary['seed']}`.",
        "",
        "## Headline metrics",
        "",
        "| Condition | Mean unique stances | Dissent rate | Gold correct | Boundary mean | Quality mean | Harmful compromise cases |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        metrics = summary["conditions"][condition]
        lines.append(
            f"| `{condition}` | {metrics['mean_unique_stances']:.3f} | "
            f"{metrics['substantive_dissent_rate']:.3f} | "
            f"{metrics['gold_correct_cases']}/{scenario_count} | "
            f"{metrics['complete_critical_boundaries_mean']:.3f} | "
            f"{metrics['quality_score_mean']:.3f} | "
            f"{metrics['harmful_compromise_cases']} |"
        )
    harm_disputed = any(
        "harmful_compromise" in item["fields"]
        for item in summary["judge_disagreements"]
    )
    lines.extend(["", "## Interpretation", ""])
    if summary["verdict"] == "isolation-not-supported":
        lines.append(
            "Separate calls did not increase substantive stance diversity under the "
            "preregistered rule; both blinded passes failed the isolation threshold."
        )
    else:
        lines.append(
            "Separate calls cleared the preregistered diversity rule, subject to the "
            "guardrails and limitations below."
        )
    if summary["skill_effect_under_isolation_verdict"] == "modest-secondary-gain":
        lines.append(
            "Reality Slap did not increase stance diversity under isolation; it produced only "
            "a modest secondary boundary/quality gain."
        )
    elif summary["skill_effect_under_isolation_verdict"] == "regression":
        lines.append("Reality Slap regressed the isolated-cell decision guardrails.")
    else:
        lines.append("Reality Slap showed no isolated-cell gain on the measured outcomes.")
    lines.append(
        f"Guardrails: **{'PASS' if summary['guardrails']['passed'] else 'FAIL'}**."
    )
    if harm_disputed:
        lines.append(
            "At least one harmful-compromise contrast is judge-disputed, so its count change "
            "is directional rather than a stable causal result."
        )
    threshold = summary["thresholds"]["isolation_diversity"]
    lines.extend(
        [
            "",
            "## Preregistered isolation threshold",
            "",
            f"Overall: **{'PASS' if threshold['passed'] else 'FAIL'}**. "
            "Both blinded passes must independently clear a threshold.",
            "",
        ]
    )
    for result in threshold["pass_results"]:
        lines.append(
            f"- Pass {result['pass_number']}: unique-stance Δ "
            f"{result['mean_unique_stance_delta']:+.3f}; dissent-rate Δ "
            f"{result['substantive_dissent_rate_delta']:+.3f}; "
            f"{'PASS' if result['passed'] else 'FAIL'} via `{result['reason']}`."
        )
    lines.extend(["", "## Contrasts", ""])
    for name, contrast in summary["contrasts"].items():
        lines.append(
            f"- `{name}`: unique-stance Δ {contrast['mean_unique_stances_delta']:+.3f}; "
            f"dissent-rate Δ {contrast['substantive_dissent_rate_delta']:+.3f}; "
            f"boundary Δ {contrast['complete_critical_boundaries_delta']:+.3f}; "
            f"quality Δ {contrast['quality_score_delta']:+.3f}; harmful compromise "
            f"{format_harmful(contrast['harmful_compromise'])}."
        )
    costs = summary["costs"]
    lines.extend(
        [
            "",
            "## Cost and completeness",
            "",
            f"- Actual model attempts: {costs['actual_model_attempts']}",
            f"- Retries: {costs['retries']}",
            f"- Prompt characters: {costs['prompt_characters']}",
            f"- Output characters: {costs['output_characters']}",
            f"- Summed call time: {costs['elapsed_seconds']:.3f} seconds",
            "",
            "## Judge disagreements",
            "",
        ]
    )
    if summary["judge_disagreements"]:
        for item in summary["judge_disagreements"]:
            lines.append(
                f"- `{item['scenario_id']}` / `{item['condition']}`: "
                + ", ".join(item["fields"])
            )
    else:
        lines.append("- None on the preregistered binary fields.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.extend(["", "## Claim boundary", "", summary["claim_boundary"], ""])
    return "\n".join(lines)


def write_reports(summary, json_path, markdown_path):
    json_path = Path(json_path)
    markdown_path = Path(markdown_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(summary), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()
    summary = summarize(Path(args.workspace))
    if args.audit_only:
        print(
            json.dumps(
                {
                    "status": summary["status"],
                    "verdict": summary["verdict"],
                    "missing_call_ids": summary["missing_call_ids"],
                    "invalid_call_ids": summary["invalid_call_ids"],
                    "retry_exhausted_call_ids": summary["retry_exhausted_call_ids"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    if bool(args.json_output) != bool(args.markdown_output):
        parser.error("--json-output and --markdown-output must be provided together")
    if args.json_output:
        write_reports(summary, args.json_output, args.markdown_output)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
