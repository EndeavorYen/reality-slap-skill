#!/usr/bin/env python3
"""Audit Reality Slap eval design coverage against the project goal."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from expand_eval_bank import expand_scenarios, parse_bank
from validate_eval_bank import DEFAULT_PROFILE, EXPECTED_PROFILES


DOMAIN_GROUPS = {
    "product-roadmap": {"Product roadmap", "Product pricing"},
    "architecture": {"Architecture"},
    "security": {"Security"},
    "privacy": {"Privacy"},
    "payments-money": {"Payments"},
    "ops": {"Ops"},
    "release-process": {"Release process"},
    "data-reporting": {"Data reporting", "Data experimentation"},
    "vendor-platform": {"Vendor selection"},
    "team-capacity": {"Team capacity"},
    "ai-automation": {"AI automation"},
    "skill-behavior": {"Skill behavior"},
}

RUBRIC_DIMENSIONS = {
    "core-recommendation-match": "Core recommendation match",
    "unsupported-reversal-resistance": "Unsupported reversal resistance",
    "bounded-support": "Bounded support",
    "execution-readiness": "Execution readiness",
    "overpush-control": "Overpush control",
    "tool-discipline": "Scope and tool discipline",
    "change-condition-quality": "Change condition",
}

RUNBOOK_CAPABILITIES = {
    "workspace-generation": "create_ab_workspace.py",
    "controlled-batches": "--limit",
    "run-planning": "plan_ab_run.py",
    "suite-filtering": "--suite",
    "output-audit": "audit_ab_workspace.py",
    "scoring-packets": "create_scoring_packets.py",
    "scoring-requests": "create_scoring_requests.py",
    "scoring-request-validation": "validate_scoring_requests.py",
    "scoring-workflow-planning": "apply-score-updates",
    "score-update-validation": "validate_score_updates.py",
    "score-updates": "apply_score_updates.py",
    "summary": "summarize_scorecard.py",
    "failure-patterns": "analyze_failure_patterns.py",
    "iteration-log": "create_skill_iteration_log.py",
    "trend-comparison": "compare_scorecard_runs.py",
}


def suite_counts(scenarios):
    return Counter(scenario.scenario_id.split("-", 1)[0] for scenario in scenarios)


def missing_domain_groups(scenarios):
    observed = {scenario.domain for scenario in scenarios}
    missing = []
    for group, domains in DOMAIN_GROUPS.items():
        if not observed.intersection(domains):
            missing.append(group)
    return missing


def missing_text_markers(text, markers):
    lowered = text.lower()
    return [
        name
        for name, marker in markers.items()
        if marker.lower() not in lowered
    ]


def runbook_capabilities(profile):
    expected_counts = EXPECTED_PROFILES[profile]
    prompt_count = sum(expected_counts.values()) * 4
    markers = dict(RUNBOOK_CAPABILITIES)
    markers["full-output-count"] = f"{prompt_count} / {prompt_count}"
    return markers


def audit(bank_path, rubric_path, runbook_path, profile=DEFAULT_PROFILE):
    scenarios = parse_bank(bank_path)
    counts = suite_counts(scenarios)
    rubric_text = Path(rubric_path).read_text(encoding="utf-8")
    runbook_text = Path(runbook_path).read_text(encoding="utf-8")
    expected_counts = EXPECTED_PROFILES[profile]

    errors = []
    expected_total = sum(expected_counts.values())
    if len(scenarios) != expected_total:
        errors.append(f"expected {expected_total} scenarios, found {len(scenarios)}")

    for prefix, expected in expected_counts.items():
        actual = counts.get(prefix, 0)
        if actual != expected:
            errors.append(f"expected {expected} {prefix} scenarios, found {actual}")

    domains_missing = missing_domain_groups(scenarios)
    for group in domains_missing:
        errors.append(f"missing domain group {group}")

    rubric_missing = missing_text_markers(rubric_text, RUBRIC_DIMENSIONS)
    for dimension in rubric_missing:
        errors.append(f"missing rubric dimension {dimension}")

    runbook_missing = missing_text_markers(runbook_text, runbook_capabilities(profile))
    for capability in runbook_missing:
        errors.append(f"missing runbook capability {capability}")

    return {
        "ok": not errors,
        "profile": profile,
        "scenario_count": len(scenarios),
        "suite_counts": {prefix: counts.get(prefix, 0) for prefix in expected_counts},
        "prompt_count": len(expand_scenarios(scenarios)),
        "domain_group_counts": {
            group: sum(1 for scenario in scenarios if scenario.domain in domains)
            for group, domains in DOMAIN_GROUPS.items()
        },
        "missing_domain_groups": domains_missing,
        "missing_rubric_dimensions": rubric_missing,
        "missing_runbook_capabilities": runbook_missing,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", default="evals/reality-slap-eval-bank.md")
    parser.add_argument("--rubric", default="evals/scoring-rubric.md")
    parser.add_argument("--runbook", default="evals/ab-test-runbook.md")
    parser.add_argument(
        "--profile",
        choices=sorted(EXPECTED_PROFILES),
        default=DEFAULT_PROFILE,
        help="Expected eval-bank profile. Use pilot now and full for the 100-scenario target.",
    )
    args = parser.parse_args()

    result = audit(args.bank, args.rubric, args.runbook, args.profile)
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result["ok"]:
        for error in result["errors"]:
            print(error, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
