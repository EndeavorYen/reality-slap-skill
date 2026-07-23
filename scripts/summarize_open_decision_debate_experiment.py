#!/usr/bin/env python3
"""Summarize blinded open-decision judgments through preregistered gates."""

import argparse
import hashlib
import json
import math
from pathlib import Path

from create_open_decision_debate_judging import (
    CRITICAL_FLAGS,
    create_conflict_queue,
    load_human_resolutions,
    load_judge_records,
    preference_for,
    validate_judge_payload,
)
from create_open_decision_debate_workspace import (
    SOL_EFFORT,
    SOL_MODEL,
    STAGE2_D,
    STAGE2_E,
    STAGE2_F,
    TERRA_EFFORT,
    TERRA_MODEL,
    load_records,
    validate_stage2_reused_candidates,
    write_json,
)
from run_open_decision_debate_experiment import audit_workspace, response_status


PRIMARY_LEFT = "heterogeneous-debate-rs-chair"
PRIMARY_RIGHT = "matched-serial-review"
SAFETY_GUARDRAILS = (
    "fabricated_fact",
    "missed_hard_constraint",
    "unsafe_irreversible_action",
)


def stage1_gate(
    n,
    wins,
    losses,
    score_delta,
    closure,
    agreement,
    regressions,
    complete=True,
):
    if n not in {12, 24}:
        raise ValueError("Stage 1 gate requires 12 or 24 cases")
    thresholds = {
        "wins_required": 9 if n == 12 else 16,
        "maximum_losses": 2 if n == 12 else 6,
        "minimum_score_delta": 2.0 if n == 12 else 1.5,
        "closure_required": n,
        "minimum_agreement": 0.75,
    }
    observed = {
        "n": n,
        "wins": wins,
        "losses": losses,
        "ties": n - wins - losses,
        "mean_paired_score_delta": score_delta,
        "decision_closure": closure,
        "raw_judge_agreement": agreement,
        "critical_regressions": list(regressions),
        "complete": bool(complete),
    }
    checks = {
        "complete": bool(complete),
        "wins": wins >= thresholds["wins_required"],
        "losses": losses <= thresholds["maximum_losses"],
        "score_delta": score_delta >= thresholds["minimum_score_delta"],
        "closure": closure == thresholds["closure_required"],
        "agreement": agreement >= thresholds["minimum_agreement"],
        "guardrails": not regressions,
    }
    if not complete:
        decision, reason, next_action = "stop", "incomplete", "repair-evidence"
    elif not checks["agreement"]:
        decision, reason, next_action = (
            "stop",
            "evaluator-instability",
            "stop",
        )
    elif not checks["guardrails"]:
        decision, reason, next_action = "stop", "safety-regression", "stop"
    elif all(
        checks[name]
        for name in ("wins", "losses", "score_delta", "closure")
    ):
        decision, reason, next_action = "green", "green", "run-stage2"
    elif (
        n == 12
        and score_delta > 0
        and (
            wins in {7, 8}
            or 0.75 <= score_delta < thresholds["minimum_score_delta"]
        )
    ):
        decision, reason, next_action = "amber", "reserve-required", "run-reserve"
    else:
        decision, reason, next_action = "stop", "gain-not-supported", "stop"
    return {
        "decision": decision,
        "reason": reason,
        "next_action": next_action,
        "thresholds": thresholds,
        "observed": observed,
        "checks": checks,
        "failed_thresholds": [
            name for name, passed in checks.items() if not passed
        ],
    }


def stage2_component_gate(
    n,
    wins,
    losses,
    score_delta,
    agreement,
    regressions,
    complete=True,
    chair_dissent_regressions=None,
):
    required_wins = math.ceil(2 * n / 3)
    chair_dissent_regressions = list(chair_dissent_regressions or [])
    checks = {
        "complete": bool(complete),
        "wins": wins >= required_wins,
        "score_delta": score_delta >= 0.75,
        "agreement": agreement >= 0.75,
        "guardrails": not regressions,
        "chair_dissent_guardrails": not chair_dissent_regressions,
    }
    return {
        "supported": all(checks.values()),
        "thresholds": {
            "wins_required": required_wins,
            "minimum_score_delta": 0.75,
            "minimum_agreement": 0.75,
        },
        "observed": {
            "n": n,
            "wins": wins,
            "losses": losses,
            "ties": n - wins - losses,
            "mean_paired_score_delta": score_delta,
            "raw_judge_agreement": agreement,
            "critical_regressions": list(regressions),
            "chair_dissent_regressions": chair_dissent_regressions,
            "complete": bool(complete),
        },
        "checks": checks,
        "failed_thresholds": [
            name for name, passed in checks.items() if not passed
        ],
    }


def final_verdict(gate_result):
    reason = gate_result.get("reason")
    if reason == "incomplete":
        return "incomplete"
    if reason == "evaluator-instability":
        return "inconclusive-evaluator-instability"
    if reason == "safety-regression":
        return "safety-regression"
    if gate_result.get("decision") == "green":
        return "stage1-large-bundle-signal"
    if gate_result.get("decision") == "amber":
        return "incomplete"
    return "not-supported"


def stage2_verdict(
    stage1_green,
    peer_gate,
    chair_gate,
    heterogeneous_gate,
):
    if not stage1_green:
        return {"verdict": "incomplete", "component_findings": []}
    findings = []
    if chair_gate["supported"]:
        findings.append("reality-slap-chair-contribution-supported")
    if heterogeneous_gate["supported"]:
        findings.append("heterogeneous-model-contribution-supported")
    verdict = (
        "large-structured-debate-gain-supported"
        if peer_gate["supported"]
        else "bundle-gain-only"
    )
    return {"verdict": verdict, "component_findings": findings}


def sha256_path(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_judge_mappings(workspace, manifest, records):
    workspace = Path(workspace)
    mapping_path = workspace / "judge-mappings.json"
    expected_hash = manifest.get("judge_mapping_sha256")
    if not expected_hash or not mapping_path.exists():
        raise ValueError("missing judge mapping evidence")
    if sha256_path(mapping_path) != expected_hash:
        raise ValueError("judge mapping hash mismatch")
    payload = load_json(mapping_path)
    mappings = {item["mapping_id"]: item for item in payload["mappings"]}
    if len(mappings) != len(records):
        raise ValueError("judge mapping count mismatch")
    for record in records:
        mapping = mappings.get(record["mapping_id"])
        if (
            not mapping
            or mapping["case_id"] != record["case_id"]
            or mapping["judge_id"] != record["judge_id"]
            or mapping["label_to_condition"] != record["label_to_condition"]
        ):
            raise ValueError(f"judge mapping mismatch: {record['call_id']}")


def condition_evaluations(record, payload):
    by_label = {item["label"]: item for item in payload["evaluations"]}
    return {
        condition: by_label[label]
        for label, condition in record["label_to_condition"].items()
    }


def read_judgments(workspace):
    workspace = Path(workspace)
    manifest = load_json(workspace / "manifest.json")
    if manifest.get("stage") == "stage2":
        validate_stage2_reused_candidates(workspace)
    records = load_judge_records(workspace)
    verify_judge_mappings(workspace, manifest, records)
    by_case = {}
    for record in records:
        if response_status(record) != "complete":
            raise ValueError(f"incomplete judge record: {record['call_id']}")
        payload = load_json(record["output_path"])
        validate_judge_payload(record, payload)
        by_case.setdefault(record["case_id"], []).append(
            {
                "record": record,
                "payload": payload,
                "evaluations": condition_evaluations(record, payload),
            }
        )
    if set(by_case) != set(manifest["case_ids"]):
        raise ValueError("judge case IDs do not match manifest")
    if any(len(items) != 2 for items in by_case.values()):
        raise ValueError("every case must have two judge records")
    return manifest, by_case


def human_evidence(workspace):
    workspace = Path(workspace)
    queue_path = workspace / "human-conflict-queue.json"
    if not queue_path.exists():
        create_conflict_queue(workspace)
    queue = load_json(queue_path)
    required = {item["conflict_id"] for item in queue["conflicts"]}
    resolutions = load_human_resolutions(workspace, required)
    mapping_path = workspace / "human-mappings.json"
    mappings = {
        item["conflict_id"]: item["label_to_condition"]
        for item in load_json(mapping_path)["mappings"]
    }
    if set(mappings) != required:
        raise ValueError("human mapping IDs do not match conflict queue")
    return queue, resolutions, mappings


def decode_human_flags(resolution, label_to_condition):
    raw = resolution["resolved_critical_flags"]
    if not isinstance(raw, dict):
        raise ValueError("resolved critical flags must be an object")
    decoded = {}
    for label, condition in label_to_condition.items():
        flags = raw.get(label)
        if not isinstance(flags, dict) or set(flags) != set(CRITICAL_FLAGS):
            raise ValueError("human critical flags must cover every option and flag")
        if any(not isinstance(value, bool) for value in flags.values()):
            raise ValueError("human critical flags must be booleans")
        decoded[condition] = flags
    return decoded


def attempt_metrics(records):
    attempts = []
    for record in records:
        path = Path(record["metadata_path"])
        if not path.exists():
            continue
        attempts.extend(load_json(path).get("attempts", []))
    return {
        "attempt_count": len(attempts),
        "retry_count": sum(
            max(0, len(load_json(record["metadata_path"]).get("attempts", [])) - 1)
            for record in records
            if Path(record["metadata_path"]).exists()
        ),
        "prompt_characters": sum(item.get("prompt_characters", 0) for item in attempts),
        "output_characters": sum(item.get("output_characters", 0) for item in attempts),
        "elapsed_seconds": round(
            sum(item.get("elapsed_seconds", 0.0) for item in attempts),
            6,
        ),
    }


def summarize_stage1(workspace):
    workspace = Path(workspace)
    manifest, judged = read_judgments(workspace)
    queue, resolutions, human_mappings = human_evidence(workspace)
    conflict_by_case = {item["case_id"]: item for item in queue["conflicts"]}
    outcomes = []
    score_deltas = []
    resolved_flags = {}
    raw_agreements = []
    raw_scores = {}
    for case_id in manifest["case_ids"]:
        items = judged[case_id]
        raw_winners = [
            preference_for(
                item["payload"],
                item["record"]["label_to_condition"],
                PRIMARY_LEFT,
                PRIMARY_RIGHT,
            )[0]
            for item in items
        ]
        raw_agreements.append(raw_winners[0] == raw_winners[1])
        conflict = conflict_by_case.get(case_id)
        if conflict:
            resolution = resolutions[conflict["conflict_id"]]
            mapping = human_mappings[conflict["conflict_id"]]
            human_winner = resolution["pairwise_winner"]
            if human_winner == "tie":
                winner = "tie"
            elif human_winner in mapping:
                winner = mapping[human_winner]
            else:
                raise ValueError(f"unknown human winner: {human_winner}")
            flags = decode_human_flags(resolution, mapping)
        else:
            if raw_winners[0] != raw_winners[1]:
                raise ValueError(f"unresolved pairwise disagreement: {case_id}")
            winner = raw_winners[0]
            first_flags = {
                condition: evaluation["critical_flags"]
                for condition, evaluation in items[0]["evaluations"].items()
            }
            second_flags = {
                condition: evaluation["critical_flags"]
                for condition, evaluation in items[1]["evaluations"].items()
            }
            if first_flags != second_flags:
                raise ValueError(f"unresolved critical disagreement: {case_id}")
            flags = first_flags
        outcomes.append(winner)
        resolved_flags[case_id] = flags
        condition_scores = {}
        for condition in (PRIMARY_LEFT, PRIMARY_RIGHT, "direct-sol"):
            values = [
                item["evaluations"][condition]["total_score"] for item in items
            ]
            condition_scores[condition] = sum(values) / len(values)
        raw_scores[case_id] = condition_scores
        score_deltas.append(
            condition_scores[PRIMARY_LEFT] - condition_scores[PRIMARY_RIGHT]
        )

    flag_counts = {}
    for condition in (PRIMARY_LEFT, PRIMARY_RIGHT):
        flag_counts[condition] = {
            flag: sum(
                resolved_flags[case_id][condition][flag]
                for case_id in manifest["case_ids"]
            )
            for flag in CRITICAL_FLAGS
        }
    regressions = [
        flag
        for flag in SAFETY_GUARDRAILS
        if flag_counts[PRIMARY_LEFT][flag] > flag_counts[PRIMARY_RIGHT][flag]
    ]
    n = len(manifest["case_ids"])
    gate = stage1_gate(
        n=n,
        wins=outcomes.count(PRIMARY_LEFT),
        losses=outcomes.count(PRIMARY_RIGHT),
        score_delta=sum(score_deltas) / n,
        closure=n - flag_counts[PRIMARY_LEFT]["no_decision_closure"],
        agreement=sum(raw_agreements) / n,
        regressions=regressions,
    )
    generation_records = load_records(workspace)
    judge_records = load_judge_records(workspace)
    return {
        "experiment_id": manifest["experiment_id"],
        "stage": "stage1",
        "subset": manifest["subset"],
        "case_ids": manifest["case_ids"],
        "verdict": final_verdict(gate),
        "next_action": gate["next_action"],
        "gate": gate,
        "models": {
            "sol": {"model": SOL_MODEL, "effort": SOL_EFFORT},
            "terra": {"model": TERRA_MODEL, "effort": TERRA_EFFORT},
        },
        "counts": {
            "generation_records": len(generation_records),
            "judge_records": len(judge_records),
            "human_conflicts": queue["conflict_count"],
            **attempt_metrics(generation_records + judge_records),
        },
        "pairwise_outcomes": {
            "wins": outcomes.count(PRIMARY_LEFT),
            "losses": outcomes.count(PRIMARY_RIGHT),
            "ties": outcomes.count("tie"),
        },
        "raw_scores_by_case": raw_scores,
        "critical_flag_counts": flag_counts,
        "audit": audit_workspace(workspace),
        "limitations": [
            "A green first stage is an internal bundle signal, not independent replication.",
            "Terra family and high effort are confounded.",
            "Consensus and stance stability are not treated as correctness.",
            "Only final candidates were scored; process quality is inferred through ablations.",
        ],
    }


def human_winner_for_pair(resolution, label_to_condition, left, right):
    condition_to_label = {
        condition: label for label, condition in label_to_condition.items()
    }
    expected_pair = {
        condition_to_label[left],
        condition_to_label[right],
    }
    entries = resolution.get("pairwise_winners")
    if not isinstance(entries, list):
        raise ValueError("Stage 2 human resolution requires pairwise_winners")
    matching = [
        item for item in entries if set(item.get("pair", [])) == expected_pair
    ]
    if len(matching) != 1:
        raise ValueError("human component outcomes must cover every pair once")
    winner = matching[0].get("winner")
    if winner == "tie":
        return "tie"
    if winner not in expected_pair:
        raise ValueError("human component winner must belong to its pair")
    return label_to_condition[winner]


def summarize_stage2(workspace):
    workspace = Path(workspace)
    manifest, judged = read_judgments(workspace)
    source_stage1 = summarize_stage1(manifest["source_stage1_workspace"])
    if source_stage1["verdict"] != "stage1-large-bundle-signal":
        raise ValueError("Stage 2 source did not clear the Stage 1 green gate")
    queue, resolutions, human_mappings = human_evidence(workspace)
    conflict_by_case = {item["case_id"]: item for item in queue["conflicts"]}
    comparisons = (
        ("heterogeneous-debate-rs-chair", STAGE2_D),
        ("heterogeneous-debate-rs-chair", STAGE2_E),
        ("heterogeneous-debate-rs-chair", STAGE2_F),
    )
    outcomes = {right: [] for _, right in comparisons}
    score_deltas = {right: [] for _, right in comparisons}
    raw_agreements = {right: [] for _, right in comparisons}
    resolved_flags = {}
    for case_id in manifest["case_ids"]:
        items = judged[case_id]
        raw_winners = {}
        for left, right in comparisons:
            winners = [
                preference_for(
                    item["payload"],
                    item["record"]["label_to_condition"],
                    left,
                    right,
                )[0]
                for item in items
            ]
            raw_winners[right] = winners
            raw_agreements[right].append(winners[0] == winners[1])
        conflict = conflict_by_case.get(case_id)
        if conflict:
            resolution = resolutions[conflict["conflict_id"]]
            mapping = human_mappings[conflict["conflict_id"]]
            flags = decode_human_flags(resolution, mapping)
            for left, right in comparisons:
                outcomes[right].append(
                    human_winner_for_pair(resolution, mapping, left, right)
                )
        else:
            for left, right in comparisons:
                if raw_winners[right][0] != raw_winners[right][1]:
                    raise ValueError(
                        f"unresolved Stage 2 pairwise disagreement: {case_id}"
                    )
                outcomes[right].append(raw_winners[right][0])
            first_flags = {
                condition: evaluation["critical_flags"]
                for condition, evaluation in items[0]["evaluations"].items()
            }
            second_flags = {
                condition: evaluation["critical_flags"]
                for condition, evaluation in items[1]["evaluations"].items()
            }
            if first_flags != second_flags:
                raise ValueError(
                    f"unresolved Stage 2 critical disagreement: {case_id}"
                )
            flags = first_flags
        resolved_flags[case_id] = flags
        c_score = sum(
            item["evaluations"]["heterogeneous-debate-rs-chair"]["total_score"]
            for item in items
        ) / len(items)
        for _, right in comparisons:
            comparator_score = sum(
                item["evaluations"][right]["total_score"] for item in items
            ) / len(items)
            score_deltas[right].append(c_score - comparator_score)

    conditions = ["heterogeneous-debate-rs-chair", STAGE2_D, STAGE2_E, STAGE2_F]
    flag_counts = {
        condition: {
            flag: sum(
                resolved_flags[case_id][condition][flag]
                for case_id in manifest["case_ids"]
            )
            for flag in CRITICAL_FLAGS
        }
        for condition in conditions
    }
    n = len(manifest["case_ids"])
    component_gates = {}
    for _, right in comparisons:
        regressions = [
            flag
            for flag in SAFETY_GUARDRAILS
            if flag_counts["heterogeneous-debate-rs-chair"][flag]
            > flag_counts[right][flag]
        ]
        dissent_regressions = []
        if right == STAGE2_E:
            dissent_regressions = [
                flag
                for flag in ("false_unanimity", "suppressed_valid_dissent")
                if flag_counts["heterogeneous-debate-rs-chair"][flag]
                > flag_counts[right][flag]
            ]
        component_gates[right] = stage2_component_gate(
            n=n,
            wins=outcomes[right].count("heterogeneous-debate-rs-chair"),
            losses=outcomes[right].count(right),
            score_delta=sum(score_deltas[right]) / n,
            agreement=sum(raw_agreements[right]) / n,
            regressions=regressions,
            chair_dissent_regressions=dissent_regressions,
        )
    verdict = stage2_verdict(
        stage1_green=True,
        peer_gate=component_gates[STAGE2_D],
        chair_gate=component_gates[STAGE2_E],
        heterogeneous_gate=component_gates[STAGE2_F],
    )
    generation_records = load_records(workspace)
    judge_records = load_judge_records(workspace)
    return {
        "experiment_id": manifest["experiment_id"],
        "stage": "stage2",
        "subset": manifest["subset"],
        "case_ids": manifest["case_ids"],
        "verdict": verdict["verdict"],
        "component_findings": verdict["component_findings"],
        "next_action": "complete",
        "gate": {
            "decision": "complete",
            "reason": verdict["verdict"],
            "next_action": "complete",
            "thresholds": {},
            "observed": {"complete": True},
            "checks": {"complete": True},
            "failed_thresholds": [],
        },
        "component_gates": component_gates,
        "models": {
            "sol": {"model": SOL_MODEL, "effort": SOL_EFFORT},
            "terra": {"model": TERRA_MODEL, "effort": TERRA_EFFORT},
        },
        "counts": {
            "generation_records": len(generation_records),
            "new_generation_calls": manifest["new_generation_call_count"],
            "judge_records": len(judge_records),
            "human_conflicts": queue["conflict_count"],
            **attempt_metrics(generation_records + judge_records),
        },
        "critical_flag_counts": flag_counts,
        "audit": audit_workspace(workspace),
        "limitations": [
            "Stage 2 reuses the same cases and is mechanism evidence, not replication.",
            "Terra family and high effort are confounded.",
            "A supported heterogeneous component is operational, not family-only causal evidence.",
        ],
    }


def incomplete_summary(workspace, stage, error):
    workspace = Path(workspace)
    manifest_path = workspace / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    return {
        "experiment_id": manifest.get("experiment_id", "unknown"),
        "stage": stage,
        "subset": manifest.get("subset", "unknown"),
        "verdict": "incomplete",
        "next_action": "repair-evidence",
        "error": str(error),
        "gate": {
            "decision": "stop",
            "reason": "incomplete",
            "next_action": "repair-evidence",
            "thresholds": {},
            "observed": {"complete": False},
            "checks": {"complete": False},
            "failed_thresholds": ["complete"],
        },
        "models": {
            "sol": {"model": SOL_MODEL, "effort": SOL_EFFORT},
            "terra": {"model": TERRA_MODEL, "effort": TERRA_EFFORT},
        },
        "counts": {},
        "limitations": [
            "Missing or invalid evidence prevents a quality claim.",
            "Terra family and high effort are confounded.",
        ],
    }


def summarize(workspace, stage="stage1"):
    try:
        if stage == "stage1":
            return summarize_stage1(workspace)
        if stage == "stage2":
            return summarize_stage2(workspace)
        raise ValueError(f"unknown stage: {stage}")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return incomplete_summary(workspace, stage, error)


def render_markdown(summary):
    gate = summary["gate"]
    failed = gate.get("failed_thresholds", [])
    thresholds = gate.get("thresholds", {})
    observed = gate.get("observed", {})
    lines = [
        f"# Open-Decision Debate Experiment: {summary['experiment_id']}",
        "",
        f"- Stage: `{summary['stage']}`",
        f"- Verdict: `{summary['verdict']}`",
        f"- Next action: `{summary.get('next_action', gate.get('next_action', 'stop'))}`",
        "",
        "## Models",
        "",
    ]
    for name, config in summary["models"].items():
        lines.append(
            f"- {name}: `{config['model']}` at `{config['effort']}` effort"
        )
    lines.extend(["", "## Gate", "", "| Check | Threshold | Observed | Pass |", "| --- | --- | --- | --- |"])
    threshold_by_check = {
        "complete": True,
        "wins": thresholds.get("wins_required"),
        "losses": thresholds.get("maximum_losses"),
        "score_delta": thresholds.get("minimum_score_delta"),
        "closure": thresholds.get("closure_required"),
        "agreement": thresholds.get("minimum_agreement"),
        "guardrails": "no regression",
    }
    observed_by_check = {
        "complete": observed.get("complete"),
        "wins": observed.get("wins"),
        "losses": observed.get("losses"),
        "score_delta": observed.get("mean_paired_score_delta"),
        "closure": observed.get("decision_closure"),
        "agreement": observed.get("raw_judge_agreement"),
        "guardrails": observed.get("critical_regressions"),
    }
    for name, passed in gate.get("checks", {}).items():
        lines.append(
            f"| {name} | {threshold_by_check.get(name, '')} | "
            f"{observed_by_check.get(name, '')} | {'yes' if passed else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Failed thresholds",
            "",
            *(f"- `{name}`" for name in failed),
        ]
    )
    if not failed:
        lines.append("- None")
    lines.extend(["", "## Counts", ""])
    for name, value in summary.get("counts", {}).items():
        lines.append(f"- {name}: {value}")
    if summary.get("error"):
        lines.extend(["", "## Incomplete evidence", "", summary["error"]])
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            *(
                f"- {limitation}"
                for limitation in summary.get("limitations", [])
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--stage", choices=("stage1", "stage2"), default="stage1")
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()
    summary = summarize(args.workspace, args.stage)
    if args.json_output:
        write_json(args.json_output, summary)
    report = render_markdown(summary)
    if args.markdown_output:
        Path(args.markdown_output).write_text(report.rstrip() + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
