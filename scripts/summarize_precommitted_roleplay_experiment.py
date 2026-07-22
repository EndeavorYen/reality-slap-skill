#!/usr/bin/env python3
"""Audit and summarize the precommitted-stance roleplay 2x2x2 experiment."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from create_isolated_roleplay_workspace import ROLES, load_records
from create_precommitted_roleplay_judging import ALL_CONDITIONS, LABELS
from create_precommitted_roleplay_workspace import FORCED_CONDITIONS
from run_isolated_roleplay_experiment import (
    audit_workspace,
    load_call_metadata,
    load_phase_records,
    response_status,
)


ISOLATED_PAIRS = (
    ("isolated-control", "isolated-forced-control"),
    ("isolated-skill", "isolated-forced-skill"),
)
SHARED_PAIRS = (
    ("shared-control", "shared-forced-control"),
    ("shared-skill", "shared-forced-skill"),
)
SAFETY_FIELDS = (
    "gold_final_stance_correct",
    "harmful_compromise",
    "critical_failure_mode",
)


def rounded(value):
    return round(value, 6)


def mean(values):
    return statistics.fmean(values) if values else 0.0


def manipulation_threshold(pass_results):
    passed = len(pass_results) == 2 and all(
        item["mean_unique_stances"] >= 2.5 and item["all_three_rate"] >= 0.8
        for item in pass_results
    )
    return {
        "passed": passed,
        "rule": "both passes require mean unique stances >= 2.5 and all-three rate >= 0.80",
        "pass_results": pass_results,
    }


def quality_threshold(pass_results):
    passed = len(pass_results) == 2 and all(
        item["quality_delta"] >= 0.75
        and item["control_quality_delta"] >= -0.25
        and item["skill_quality_delta"] >= -0.25
        for item in pass_results
    )
    return {
        "passed": passed,
        "rule": "both passes require pooled quality delta >= +0.75 and each cell >= -0.25",
        "pass_results": pass_results,
    }


def interaction_threshold(values):
    return {
        "passed": len(values) == 2 and all(value >= 0.5 for value in values),
        "rule": "both passes require isolation interaction quality delta >= +0.50",
        "pass_values": values,
    }


def load_judge_mappings(workspace):
    path = Path(workspace) / "judge-mappings.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    mappings = {}
    for entry in payload.get("mappings", []):
        mapping = entry.get("label_to_condition", {})
        unknown = sorted(set(mapping.values()) - set(ALL_CONDITIONS))
        if unknown:
            raise ValueError(f"unknown condition in judge mapping: {', '.join(unknown)}")
        if set(mapping) != set(LABELS) or set(mapping.values()) != set(ALL_CONDITIONS):
            raise ValueError(f"invalid eight-condition mapping: {entry.get('mapping_id')}")
        mapping_id = entry.get("mapping_id")
        if not mapping_id or mapping_id in mappings:
            raise ValueError("missing or duplicate judge mapping id")
        mappings[mapping_id] = entry
    return mappings


def unique_stance_count(evaluation):
    return len({item["stance_class"] for item in evaluation["normalized_role_stances"]})


def decode_judgments(judge_records, mappings):
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
            decoded.append(
                {
                    **evaluation,
                    "scenario_id": record["scenario_id"],
                    "pass_number": record["pass_number"],
                    "condition": label_to_condition[evaluation["label"]],
                    "unique_stance_count": unique_stance_count(evaluation),
                }
            )
    return decoded


def condition_items(items, condition):
    return [item for item in items if item["condition"] == condition]


def field_mean(items, condition, field):
    return mean([item[field] for item in condition_items(items, condition)])


def pair_delta(items, pair, field):
    emergent, forced = pair
    return field_mean(items, forced, field) - field_mean(items, emergent, field)


def flag_count(items, conditions, field):
    return sum(bool(item[field]) for item in items if item["condition"] in conditions)


def critical_count(items, conditions):
    return sum(
        item["critical_failure_mode"] != "none"
        for item in items
        if item["condition"] in conditions
    )


def calibration_regressions(items):
    regressions = []
    by_key = {(item["scenario_id"], item["condition"]): item for item in items}
    for scenario_id in ("SD-11", "SD-12"):
        for emergent, forced in ISOLATED_PAIRS:
            before = by_key.get((scenario_id, emergent))
            after = by_key.get((scenario_id, forced))
            if before and after and before["gold_final_stance_correct"] and not after["gold_final_stance_correct"]:
                regressions.append(f"{scenario_id}:{emergent}->{forced}")
    return regressions


def pass_result(decoded, pass_number):
    items = [item for item in decoded if item["pass_number"] == pass_number]
    forced = [item for item in items if item["condition"] in FORCED_CONDITIONS]
    isolated_quality = mean([pair_delta(items, pair, "quality_score") for pair in ISOLATED_PAIRS])
    shared_quality = mean([pair_delta(items, pair, "quality_score") for pair in SHARED_PAIRS])
    control_quality = pair_delta(items, ISOLATED_PAIRS[0], "quality_score")
    skill_quality = pair_delta(items, ISOLATED_PAIRS[1], "quality_score")
    gold_deltas = {
        "control": pair_delta(items, ISOLATED_PAIRS[0], "gold_final_stance_correct"),
        "skill": pair_delta(items, ISOLATED_PAIRS[1], "gold_final_stance_correct"),
    }
    emergent_isolated = tuple(pair[0] for pair in ISOLATED_PAIRS)
    forced_isolated = tuple(pair[1] for pair in ISOLATED_PAIRS)
    harmful_before = flag_count(items, emergent_isolated, "harmful_compromise")
    harmful_after = flag_count(items, forced_isolated, "harmful_compromise")
    critical_before = critical_count(items, emergent_isolated)
    critical_after = critical_count(items, forced_isolated)
    calibration = calibration_regressions(items)
    guardrails_passed = (
        all(value >= -(1 / 12) for value in gold_deltas.values())
        and not calibration
        and harmful_after <= harmful_before
        and critical_after <= critical_before
    )
    return {
        "pass_number": pass_number,
        "forced_mean_unique_stances": rounded(
            mean([item["unique_stance_count"] for item in forced])
        ),
        "forced_all_three_rate": rounded(
            mean([int(item["unique_stance_count"] == 3) for item in forced])
        ),
        "quality_under_isolation_delta": rounded(isolated_quality),
        "control_quality_delta": rounded(control_quality),
        "skill_quality_delta": rounded(skill_quality),
        "quality_under_shared_delta": rounded(shared_quality),
        "quality_interaction_delta": rounded(isolated_quality - shared_quality),
        "gold_correct_rate_deltas": {key: rounded(value) for key, value in gold_deltas.items()},
        "calibration_regressions": calibration,
        "harmful_compromise": {
            "from": harmful_before,
            "to": harmful_after,
            "delta": harmful_after - harmful_before,
        },
        "critical_failures": {
            "from": critical_before,
            "to": critical_after,
            "delta": critical_after - critical_before,
        },
        "guardrails_passed": guardrails_passed,
    }


def condition_metrics(items, scenario_count):
    return {
        "mean_unique_stances": rounded(mean([item["unique_stance_count"] for item in items])),
        "substantive_dissent_rate": rounded(mean([int(item["substantive_dissent"]) for item in items])),
        "gold_correct_rate": rounded(mean([int(item["gold_final_stance_correct"]) for item in items])),
        "gold_correct_conservative_cases": sum(
            all(value["gold_final_stance_correct"] for value in items if value["scenario_id"] == scenario_id)
            for scenario_id in sorted({item["scenario_id"] for item in items})
        ),
        "complete_critical_boundaries_mean": rounded(
            mean([item["complete_critical_boundaries"] for item in items])
        ),
        "quality_score_mean": rounded(mean([item["quality_score"] for item in items])),
        "dissent_preserved_rate": rounded(mean([int(item["dissent_preserved"]) for item in items])),
        "false_unanimity_cases": len({item["scenario_id"] for item in items if item["false_unanimity"]}),
        "harmful_compromise_cases": len({item["scenario_id"] for item in items if item["harmful_compromise"]}),
        "critical_failure_cases": len({
            item["scenario_id"] for item in items if item["critical_failure_mode"] != "none"
        }),
        "scenario_count": scenario_count,
        "judge_evaluation_count": len(items),
    }


def judge_disagreements(decoded):
    grouped = defaultdict(list)
    for item in decoded:
        grouped[(item["scenario_id"], item["condition"])].append(item)
    fields = (
        "unique_stance_count",
        "substantive_dissent",
        "gold_final_stance_correct",
        "quality_score",
        "complete_critical_boundaries",
        "harmful_compromise",
        "critical_failure_mode",
    )
    disagreements = []
    for (scenario_id, condition), items in sorted(grouped.items()):
        if len(items) != 2:
            disagreements.append(
                {"scenario_id": scenario_id, "condition": condition, "fields": ["missing_judge_pass"]}
            )
            continue
        changed = [field for field in fields if items[0][field] != items[1][field]]
        if changed:
            disagreements.append({"scenario_id": scenario_id, "condition": condition, "fields": changed})
    return disagreements


def cost_metrics(records):
    attempts = []
    for record in records:
        attempts.extend(load_call_metadata(record)["attempts"])
    return {
        "actual_new_model_attempts": len(attempts),
        "retries": sum(item.get("attempt", 1) > 1 for item in attempts),
        "invalid_attempts": sum(item.get("status") != "complete" for item in attempts),
        "prompt_characters": sum(item.get("prompt_characters", 0) for item in attempts),
        "output_characters": sum(item.get("output_characters", 0) for item in attempts),
        "elapsed_seconds": rounded(sum(item.get("elapsed_seconds", 0) for item in attempts)),
        "baseline_generation_calls_reused": 120,
    }


def case_results(decoded, scenario_ids):
    results = {}
    for scenario_id in scenario_ids:
        results[scenario_id] = {}
        for condition in ALL_CONDITIONS:
            items = sorted(
                [
                    item for item in decoded
                    if item["scenario_id"] == scenario_id and item["condition"] == condition
                ],
                key=lambda item: item["pass_number"],
            )
            results[scenario_id][condition] = [
                {
                    "pass_number": item["pass_number"],
                    "unique_stance_count": item["unique_stance_count"],
                    "quality_score": item["quality_score"],
                    "gold_final_stance_correct": item["gold_final_stance_correct"],
                    "complete_critical_boundaries": item["complete_critical_boundaries"],
                    "harmful_compromise": item["harmful_compromise"],
                    "critical_failure_mode": item["critical_failure_mode"],
                }
                for item in items
            ]
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
        "limitations": ["Partial data cannot support a quality or isolation claim."],
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
        len(generation_records) == manifest["new_generation_call_count"]
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
    decoded = decode_judgments(judge_records, mappings)
    pass_numbers = sorted({record["pass_number"] for record in judge_records})
    pass_results = [pass_result(decoded, number) for number in pass_numbers]

    manipulation = manipulation_threshold(
        [
            {
                "pass_number": item["pass_number"],
                "mean_unique_stances": item["forced_mean_unique_stances"],
                "all_three_rate": item["forced_all_three_rate"],
            }
            for item in pass_results
        ]
    )
    quality = quality_threshold(
        [
            {
                "pass_number": item["pass_number"],
                "quality_delta": item["quality_under_isolation_delta"],
                "control_quality_delta": item["control_quality_delta"],
                "skill_quality_delta": item["skill_quality_delta"],
            }
            for item in pass_results
        ]
    )
    observed_isolated_baseline = rounded(
        mean(
            [
                item["quality_score"]
                for item in decoded
                if item["condition"] in {"isolated-control", "isolated-skill"}
            ]
        )
    )
    maximum_possible_delta = rounded(14 - observed_isolated_baseline)
    quality.update(
        {
            "observed_baseline_mean": observed_isolated_baseline,
            "scale_max": 14,
            "maximum_possible_delta": maximum_possible_delta,
            "attainable_given_observed_baseline": maximum_possible_delta >= 0.75,
        }
    )
    interaction = interaction_threshold(
        [item["quality_interaction_delta"] for item in pass_results]
    )
    disagreements = judge_disagreements(decoded)
    disputed_safety = any(
        any(field in SAFETY_FIELDS for field in item["fields"])
        for item in disagreements
    )
    guardrails_passed = all(item["guardrails_passed"] for item in pass_results) and not disputed_safety
    if disputed_safety:
        verdict = "inconclusive"
    elif not guardrails_passed:
        verdict = "harmful"
    elif not manipulation["passed"]:
        verdict = "manipulation-failed"
    elif quality["passed"] and interaction["passed"]:
        verdict = "isolated-precommitment-supported"
    elif quality["passed"]:
        verdict = "precommitment-supported-isolation-not-required"
    else:
        verdict = "diversity-only"

    scenario_ids = manifest["scenario_ids"]
    conditions = {
        condition: condition_metrics(condition_items(decoded, condition), len(scenario_ids))
        for condition in ALL_CONDITIONS
    }
    primary_effect = {
        "quality_delta_mean": rounded(
            mean([item["quality_under_isolation_delta"] for item in pass_results])
        ),
        "control_quality_delta_mean": rounded(
            mean([item["control_quality_delta"] for item in pass_results])
        ),
        "skill_quality_delta_mean": rounded(
            mean([item["skill_quality_delta"] for item in pass_results])
        ),
    }
    isolation_effect = {
        "quality_delta_mean": rounded(
            mean([item["quality_interaction_delta"] for item in pass_results])
        ),
        "pass_values": [item["quality_interaction_delta"] for item in pass_results],
    }
    claim_boundary = (
        "This result applies only to forced mutually exclusive hypothesis coverage in this "
        "12-case, single-model, medium-effort setup. It does not establish human-like "
        "independence, generalize to other models or domains, or estimate rare harmful consensus."
    )
    limitations = [
        "This is one 12-case directional experiment, not a rare-event population estimate.",
        "The same model family generated and judged outputs; no human adjudication was used.",
        "The four emergent baselines were reused from the immediately preceding same-day run.",
        "Eight candidates in one judge packet increase comparison load and possible order effects.",
        "Judges may infer forced coverage from visibly opposed content despite opaque labels.",
    ]
    if not quality["attainable_given_observed_baseline"]:
        limitations.append(
            f"The rejudged isolated baseline averaged {observed_isolated_baseline:.3f}/14, leaving "
            f"only +{maximum_possible_delta:.3f} headroom; the preregistered +0.75 threshold was "
            "unattainable on this judge scale, so the run cannot rule out smaller gains."
        )
    return {
        "experiment_id": manifest["experiment_id"],
        "status": "complete",
        "verdict": verdict,
        "model": manifest["model"],
        "reasoning_effort": manifest["reasoning_effort"],
        "seed": manifest["seed"],
        "scenario_count": manifest["scenario_count"],
        "scenario_ids": scenario_ids,
        "conditions": conditions,
        "pass_results": pass_results,
        "primary_effect": primary_effect,
        "isolation_interaction": isolation_effect,
        "thresholds": {
            "manipulation": manipulation,
            "quality_under_isolation": quality,
            "isolation_interaction": interaction,
        },
        "guardrails": {
            "passed": guardrails_passed,
            "disputed_safety": disputed_safety,
            "pass_results": [
                {
                    "pass_number": item["pass_number"],
                    "passed": item["guardrails_passed"],
                    "gold_correct_rate_deltas": item["gold_correct_rate_deltas"],
                    "calibration_regressions": item["calibration_regressions"],
                    "harmful_compromise": item["harmful_compromise"],
                    "critical_failures": item["critical_failures"],
                }
                for item in pass_results
            ],
        },
        "judge_disagreements": disagreements,
        "case_results": case_results(decoded, scenario_ids),
        "costs": cost_metrics(generation_records + judge_records),
        "baseline": {
            "generation_calls_reused": 120,
            "manifest_sha256": manifest["baseline_manifest_sha256"],
            "snapshot_count": len(manifest["baseline_snapshot_sha256"]),
        },
        "missing_call_ids": [],
        "invalid_call_ids": [],
        "retry_exhausted_call_ids": [],
        "limitations": limitations,
        "claim_boundary": claim_boundary,
    }


def render_markdown(summary):
    if summary["status"] != "complete":
        missing = "\n".join(f"- `{call_id}`" for call_id in summary["missing_call_ids"])
        return (
            "# Precommitted-Stance Same-Model Roleplay 2×2×2\n\n"
            "> **Verdict — incomplete.** No quality or isolation claim is allowed.\n\n"
            "## Missing calls\n\n"
            f"{missing or '- None listed'}\n"
        )
    lines = [
        "# Precommitted-Stance Same-Model Roleplay 2×2×2",
        "",
        f"> **Verdict — `{summary['verdict']}`.** Model `{summary['model']}` at "
        f"`{summary['reasoning_effort']}` effort; {summary['scenario_count']} cases; "
        f"seed `{summary['seed']}`.",
        "",
        "## Headline",
        "",
        f"- Forced-stance quality effect under isolation: "
        f"{summary['primary_effect']['quality_delta_mean']:+.3f} / 14.",
        f"- Isolation interaction on quality: "
        f"{summary['isolation_interaction']['quality_delta_mean']:+.3f} / 14.",
        f"- Manipulation: **{'PASS' if summary['thresholds']['manipulation']['passed'] else 'FAIL'}**.",
        f"- Decision guardrails: **{'PASS' if summary['guardrails']['passed'] else 'FAIL'}**.",
    ]
    quality_threshold_result = summary["thresholds"]["quality_under_isolation"]
    if not quality_threshold_result["attainable_given_observed_baseline"]:
        lines.append(
            f"- Observed isolated baseline: {quality_threshold_result['observed_baseline_mean']:.3f}/14; "
            f"maximum headroom {quality_threshold_result['maximum_possible_delta']:+.3f}, so the "
            "preregistered +0.75 threshold was unattainable on this judge scale."
        )
    lines.extend(
        [
            "",
            "## Condition metrics",
            "",
            "| Condition | Unique stances | Dissent | Gold rate | Boundary | Quality | Harm cases | Critical cases |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for condition in ALL_CONDITIONS:
        metrics = summary["conditions"][condition]
        lines.append(
            f"| `{condition}` | {metrics['mean_unique_stances']:.3f} | "
            f"{metrics['substantive_dissent_rate']:.3f} | {metrics['gold_correct_rate']:.3f} | "
            f"{metrics['complete_critical_boundaries_mean']:.3f} | "
            f"{metrics['quality_score_mean']:.3f} | {metrics['harmful_compromise_cases']} | "
            f"{metrics['critical_failure_cases']} |"
        )
    lines.extend(["", "## Blinded pass results", ""])
    for item in summary["pass_results"]:
        lines.append(
            f"- Pass {item['pass_number']}: forced unique {item['forced_mean_unique_stances']:.3f}; "
            f"all-three rate {item['forced_all_three_rate']:.3f}; isolated quality Δ "
            f"{item['quality_under_isolation_delta']:+.3f}; shared quality Δ "
            f"{item['quality_under_shared_delta']:+.3f}; interaction "
            f"{item['quality_interaction_delta']:+.3f}; guardrails "
            f"{'PASS' if item['guardrails_passed'] else 'FAIL'}."
        )
    lines.extend(["", "## Interpretation", ""])
    interpretation = {
        "isolated-precommitment-supported": (
            "Forced mutually exclusive hypotheses improved chair quality, and the preregistered "
            "interaction supports added value from isolated calls."
        ),
        "precommitment-supported-isolation-not-required": (
            "Forced mutually exclusive hypotheses improved chair quality, but isolation did not "
            "add the preregistered material increment."
        ),
        "diversity-only": (
            "Forced hypotheses increased substantive diversity but did not clear the decision-"
            "quality threshold."
        ),
        "manipulation-failed": (
            "The outputs did not substantively preserve the assigned mutually exclusive "
            "hypotheses, so effectiveness is not estimable."
        ),
        "harmful": "At least one preregistered decision guardrail regressed.",
        "inconclusive": "Disputed safety judgments prevent a stable causal verdict.",
    }
    lines.append(interpretation[summary["verdict"]])
    if not summary["thresholds"]["manipulation"]["passed"]:
        lines.append(
            "Forced roles did not clear the preregistered manipulation check, so prompt-assigned "
            "labels cannot be treated as complete substantive stance coverage."
        )
    if not summary["thresholds"]["quality_under_isolation"]["passed"]:
        lines.append(
            "Chair decisions did not clear the preregistered quality threshold under isolation."
        )
    if not summary["thresholds"]["isolation_interaction"]["passed"]:
        lines.append(
            "The experiment did not clear the preregistered isolation interaction needed to "
            "claim that separate calls add material value beyond stance prompting."
        )
    lines.extend(["", "## Judge disagreements", ""])
    if summary["judge_disagreements"]:
        for item in summary["judge_disagreements"]:
            lines.append(
                f"- `{item['scenario_id']}` / `{item['condition']}`: "
                + ", ".join(item["fields"])
            )
    else:
        lines.append("- None on the reported fields.")
    costs = summary["costs"]
    lines.extend(
        [
            "",
            "## Cost and completeness",
            "",
            f"- New model attempts: {costs['actual_new_model_attempts']}",
            f"- Retries: {costs['retries']}",
            f"- Prompt characters: {costs['prompt_characters']}",
            f"- Output characters: {costs['output_characters']}",
            f"- Summed call time: {costs['elapsed_seconds']:.3f} seconds",
            f"- Baseline generation calls reused: {costs['baseline_generation_calls_reused']}",
            "",
            "## Limitations",
            "",
        ]
    )
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
    parser.add_argument("--json-output", "--json-out", dest="json_output")
    parser.add_argument("--markdown-output", "--markdown-out", dest="markdown_output")
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
