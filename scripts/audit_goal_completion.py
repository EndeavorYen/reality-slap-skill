#!/usr/bin/env python3
"""Audit whether the Reality Slap evaluation goal is actually complete."""

import argparse
import json
import sys
from pathlib import Path

from analyze_failure_patterns import analyze as analyze_failure_patterns
from audit_ab_workspace import audit_workspace
from audit_eval_design import audit as audit_eval_design
from summarize_scorecard import summarize
from validate_eval_bank import DEFAULT_PROFILE, EXPECTED_PROFILES
from validate_scorecard import validate_scorecard


EXPECTED_SKILL_NAME = "reality-slap"


def expected_counts(profile):
    scenarios = sum(EXPECTED_PROFILES[profile].values())
    return {
        "scenarios": scenarios,
        "prompts": scenarios * 4,
        "individual_scores": scenarios * 4,
        "pair_scores": scenarios * 2,
    }


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return {}, "skill frontmatter is missing"

    end_marker = "\n---\n"
    end = text.find(end_marker, 4)
    if end == -1:
        return {}, "skill frontmatter is not closed"

    values = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values, ""


def audit_skill(path):
    path = Path(path)
    report = {
        "path": str(path),
        "exists": path.exists(),
        "frontmatter": {},
        "errors": [],
    }

    if not report["exists"]:
        report["errors"].append("skill file is missing")
        return report

    if path.name != "SKILL.md":
        report["errors"].append("skill path must point to SKILL.md")

    frontmatter, error = parse_frontmatter(path.read_text(encoding="utf-8"))
    report["frontmatter"] = frontmatter
    if error:
        report["errors"].append(error)
        return report

    if frontmatter.get("name") != EXPECTED_SKILL_NAME:
        report["errors"].append(f"skill name must be {EXPECTED_SKILL_NAME}")
    if not frontmatter.get("description"):
        report["errors"].append("skill description is required")

    return report


def infer_profile(workspace, explicit_profile):
    if explicit_profile:
        return explicit_profile

    manifest_path = Path(workspace) / "manifest.json"
    if manifest_path.exists():
        profile = load_json(manifest_path).get("profile")
        if profile in EXPECTED_PROFILES:
            return profile

    return DEFAULT_PROFILE


def workspace_manifest(workspace):
    manifest_path = Path(workspace) / "manifest.json"
    if manifest_path.exists():
        return load_json(manifest_path)
    return {}


def infer_bank(workspace, explicit_bank):
    if explicit_bank:
        return explicit_bank

    source = workspace_manifest(workspace).get("source")
    if source:
        return source

    return "evals/reality-slap-eval-bank.md"


def normalize_path(path):
    return str(Path(path).expanduser().resolve())


def empty_iteration_log(path, required=True):
    return {
        "path": str(path) if path else "",
        "exists": False,
        "required": required,
        "source_scorecard": "",
        "skill_update_count": 0,
        "failure_modes": [],
        "errors": ["iteration log is missing"] if required else [],
    }


def actionable_patterns_by_mode(patterns):
    return {
        pattern["failure_mode"]: pattern
        for pattern in patterns.get("patterns", [])
        if pattern.get("actionable")
    }


def sorted_list(value):
    return sorted(value) if isinstance(value, list) else None


def validate_iteration_pattern_metadata(update, pattern):
    mode = update.get("failure_mode", "")
    errors = []

    if update.get("count") != pattern.get("count"):
        errors.append(
            f"iteration log failure_mode {mode} count does not match scorecard"
        )

    for field in ("scenario_ids", "domains", "suites"):
        observed = sorted_list(update.get(field))
        expected = sorted_list(pattern.get(field))
        if observed is None:
            errors.append(f"iteration log failure_mode {mode} missing {field}")
        elif observed != expected:
            errors.append(
                f"iteration log failure_mode {mode} {field} does not match scorecard"
            )

    return errors


def audit_iteration_log(path, expected_scorecard_path, patterns):
    actionable_patterns = actionable_patterns_by_mode(patterns)
    actionable_modes = set(actionable_patterns)
    if not actionable_modes and not path:
        return empty_iteration_log(path, required=False)

    if not path:
        return empty_iteration_log(path)

    path = Path(path)
    if not path.exists():
        return empty_iteration_log(path)

    errors = []
    data = load_json(path)
    source_scorecard = data.get("source_scorecard", "")
    if not source_scorecard:
        errors.append("iteration log missing source_scorecard")
    elif normalize_path(source_scorecard) != normalize_path(expected_scorecard_path):
        errors.append("iteration log source_scorecard does not match workspace scorecard")

    updates = data.get("skill_updates", [])
    if not isinstance(updates, list):
        updates = []
        errors.append("iteration log skill_updates must be a list")

    failure_modes = []
    for index, update in enumerate(updates, start=1):
        if not isinstance(update, dict):
            errors.append(f"iteration log skill_updates[{index}] must be an object")
            continue
        mode = update.get("failure_mode", "")
        target_file = update.get("file", "")
        change = update.get("change", "")
        evidence = update.get("evidence", "")
        if not mode:
            errors.append(f"iteration log skill_updates[{index}] missing failure_mode")
        else:
            failure_modes.append(mode)
            if mode not in actionable_modes:
                errors.append(
                    f"iteration log failure_mode {mode} is not actionable in scorecard"
                )
            else:
                errors.extend(
                    validate_iteration_pattern_metadata(update, actionable_patterns[mode])
                )
        if target_file != "SKILL.md":
            errors.append(f"iteration log skill_updates[{index}] must target SKILL.md")
        if not change:
            errors.append(f"iteration log skill_updates[{index}] missing change")
        if update.get("applied") is not True:
            errors.append(f"iteration log skill_updates[{index}] is not marked applied")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"iteration log skill_updates[{index}] missing evidence")

    unique_modes = sorted(set(failure_modes))
    missing_modes = sorted(actionable_modes - set(unique_modes))
    if missing_modes:
        errors.append(
            "iteration log missing SKILL.md updates for actionable failure modes: "
            + ", ".join(missing_modes)
        )

    return {
        "path": str(path),
        "exists": True,
        "required": bool(actionable_modes),
        "source_scorecard": source_scorecard,
        "skill_update_count": len(updates),
        "failure_modes": unique_modes,
        "errors": errors,
    }


def build_checks(
    design,
    skill,
    workspace,
    scorecard_errors,
    summary,
    patterns,
    iteration_log,
    expected,
):
    errors = []

    if not design.get("ok"):
        errors.append("eval design audit is not passing")

    errors.extend(skill["errors"])

    integrity = workspace.get("integrity", {"ok": True, "errors": []})
    if not integrity.get("ok", True):
        errors.append("workspace integrity is not passing")
        errors.extend(integrity.get("errors", []))

    if workspace["scenario_count"] != expected["scenarios"]:
        errors.append(
            f"expected {expected['scenarios']} workspace scenarios, found {workspace['scenario_count']}"
        )
    if workspace["prompt_count"] != expected["prompts"]:
        errors.append(
            f"expected {expected['prompts']} prompt records, found {workspace['prompt_count']}"
        )
    if workspace["outputs"]["complete"] != expected["prompts"]:
        errors.append(
            f"live outputs are incomplete: {workspace['outputs']['complete']} / {expected['prompts']}"
        )
    if workspace["scorecard"]["individual_complete"] != expected["individual_scores"]:
        errors.append(
            "scorecard is incomplete: "
            f"{workspace['scorecard']['individual_complete']} / {expected['individual_scores']} individual scores"
        )
    if workspace["scorecard"]["pair_complete"] != expected["pair_scores"]:
        errors.append(
            "scorecard is incomplete: "
            f"{workspace['scorecard']['pair_complete']} / {expected['pair_scores']} pair scores"
        )
    if scorecard_errors:
        errors.extend(scorecard_errors)

    if summary["verdict"] == "incomplete":
        errors.append("summary verdict is incomplete")
    if summary["pair_score_delta"] is None or summary["pair_score_delta"] < 0:
        errors.append(
            f"skill pair-score delta is negative: {summary['pair_score_delta']}"
        )
    if (
        summary["skill_individual_average"] is None
        or summary["baseline_individual_average"] is None
        or summary["skill_individual_average"] < summary["baseline_individual_average"]
    ):
        errors.append("skill individual average is below baseline")

    errors.extend(iteration_log["errors"])

    return errors


def audit_goal(args):
    profile = infer_profile(args.workspace, args.profile)
    bank = infer_bank(args.workspace, args.bank)
    expected = expected_counts(profile)
    design = audit_eval_design(bank, args.rubric, args.runbook, profile)
    skill = audit_skill(args.skill)
    workspace = audit_workspace(args.workspace)
    scorecard = load_json(Path(args.workspace) / "scorecard.json")
    scorecard_errors = validate_scorecard(scorecard)
    summary = summarize(scorecard)
    patterns = analyze_failure_patterns(scorecard)
    iteration_log = audit_iteration_log(
        args.iteration_log,
        Path(args.workspace) / "scorecard.json",
        patterns,
    )

    errors = build_checks(
        design,
        skill,
        workspace,
        scorecard_errors,
        summary,
        patterns,
        iteration_log,
        expected,
    )

    return {
        "ok": not errors,
        "profile": profile,
        "bank": bank,
        "expected": expected,
        "errors": errors,
        "design": design,
        "skill": skill,
        "workspace": workspace["workspace"],
        "workspace_integrity": workspace.get("integrity", {"ok": True, "errors": []}),
        "outputs": workspace["outputs"],
        "invalid_outputs": workspace.get("invalid_outputs", []),
        "scorecard": workspace["scorecard"],
        "summary": summary,
        "failure_patterns": patterns,
        "iteration_log": iteration_log,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--bank")
    parser.add_argument("--rubric", default="evals/scoring-rubric.md")
    parser.add_argument("--runbook", default="evals/ab-test-runbook.md")
    parser.add_argument("--skill", default="SKILL.md")
    parser.add_argument("--iteration-log")
    parser.add_argument(
        "--profile",
        choices=sorted(EXPECTED_PROFILES),
        default=None,
        help="Expected active completion profile.",
    )
    args = parser.parse_args()

    result = audit_goal(args)
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result["ok"]:
        for error in result["errors"]:
            print(error, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
