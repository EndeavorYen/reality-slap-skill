#!/usr/bin/env python3
"""Plan the next resumable Reality Slap A/B run step."""

import argparse
import json
from pathlib import Path

from audit_ab_workspace import audit_workspace
from apply_score_updates import load_scorecard, load_updates
from validate_score_updates import validate_coverage


SUITE_ORDER = ("frame-invariance", "pressure-reversal", "execution-boundary")


def command_for_runner(workspace, suite, limit, execute=False):
    command = [
        "python3",
        "scripts/run_codex_workspace.py",
        "--workspace",
        str(workspace),
        "--suite",
        suite,
        "--limit",
        str(limit),
    ]
    if execute:
        command.append("--execute")
    return command


def scorecard_path_for(workspace):
    return Path(workspace) / "scorecard.json"


def default_score_updates_path(workspace):
    return Path(workspace) / "score-updates.jsonl"


def score_update_validation_command(workspace, score_updates):
    return [
        "python3",
        "scripts/validate_score_updates.py",
        "--scorecard",
        str(scorecard_path_for(workspace)),
        "--updates",
        str(score_updates),
    ]


def apply_score_updates_command(workspace, score_updates):
    return [
        "python3",
        "scripts/apply_score_updates.py",
        "--scorecard",
        str(scorecard_path_for(workspace)),
        "--updates",
        str(score_updates),
        "--in-place",
    ]


def scoring_packets_command(workspace):
    return [
        "python3",
        "scripts/create_scoring_packets.py",
        "--workspace",
        str(workspace),
        "--kind",
        "all",
        "--format",
        "markdown",
    ]


def scoring_requests_command(workspace):
    return [
        "python3",
        "scripts/create_scoring_requests.py",
        "--workspace",
        str(workspace),
        "--kind",
        "all",
    ]


def score_update_validation_report(workspace, score_updates):
    try:
        scorecard = load_scorecard(scorecard_path_for(workspace))
        updates = load_updates(score_updates)
    except ValueError as error:
        return {
            "ok": False,
            "expected_updates": None,
            "provided_updates": None,
            "missing_update_count": None,
            "duplicate_update_count": None,
            "unknown_update_count": None,
            "errors": [str(error)],
        }
    return validate_coverage(scorecard, updates, "all")


def suite_output_missing(audit):
    return {
        suite: values["outputs_total"] - values["outputs_complete"]
        for suite, values in audit["suite_summary"].items()
    }


def first_missing_suite(missing_by_suite):
    for suite in SUITE_ORDER:
        if missing_by_suite.get(suite, 0) > 0:
            return suite
    return None


def plan_next_step(workspace, limit, score_updates=None):
    workspace = Path(workspace)
    score_updates = Path(score_updates) if score_updates else default_score_updates_path(workspace)
    audit = audit_workspace(workspace)
    missing_by_suite = suite_output_missing(audit)
    next_suite = first_missing_suite(missing_by_suite)

    plan = {
        "workspace": str(Path(workspace)),
        "outputs": audit["outputs"],
        "scorecard": audit["scorecard"],
        "suite_output_missing": missing_by_suite,
        "next_suite": next_suite,
        "next_action": "",
    }

    if next_suite:
        plan["next_action"] = "run-live-output-batch"
        plan["dry_run_command"] = command_for_runner(workspace, next_suite, limit)
        plan["execute_command"] = command_for_runner(
            workspace,
            next_suite,
            limit,
            execute=True,
        )
        return plan

    if not audit["scorecard_complete"]:
        plan["score_updates_path"] = str(score_updates)
        plan["scoring_packets_command"] = scoring_packets_command(workspace)
        plan["scoring_requests_command"] = scoring_requests_command(workspace)
        plan["scoring_requests_output"] = str(workspace / "scoring-requests.jsonl")
        plan["score_update_validation_command"] = score_update_validation_command(
            workspace,
            score_updates,
        )
        plan["apply_score_updates_command"] = apply_score_updates_command(
            workspace,
            score_updates,
        )
        if not score_updates.exists():
            plan["next_action"] = "create-scoring-requests"
            return plan

        validation = score_update_validation_report(workspace, score_updates)
        plan["score_update_validation"] = validation
        plan["next_action"] = (
            "apply-score-updates" if validation.get("ok") else "repair-score-updates"
        )
        return plan

    plan["next_action"] = "audit-goal-completion"
    plan["completion_audit_command"] = [
        "python3",
        "scripts/audit_goal_completion.py",
        "--workspace",
        str(workspace),
        "--iteration-log",
        str(Path(workspace) / "iteration-log.json"),
    ]
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--score-updates")
    args = parser.parse_args()

    print(
        json.dumps(
            plan_next_step(Path(args.workspace), args.limit, args.score_updates),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
