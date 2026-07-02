#!/usr/bin/env python3
"""Validate scoring-request JSONL before handing it to a scorer."""

import argparse
import json
import sys
from pathlib import Path

from create_scoring_requests import RUBRIC_SOURCE, create_requests


def load_requests(path):
    requests = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"line {line_number}: invalid JSON: {error}") from error
        request["_line_number"] = line_number
        requests.append(request)
    return requests


def load_mapping(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def target_from_mapping(mapping):
    return (
        mapping.get("scenario_id"),
        mapping.get("score_type"),
        mapping.get("configuration"),
    )


def request_target(request):
    packet = request.get("packet", {})
    target = packet.get("score_update_target", {})
    return target_from_mapping(target)


def template_target(request):
    return target_from_mapping(request.get("score_update_template", {}))


def format_target(target):
    scenario_id, score_type, configuration = target
    return f"{scenario_id} {score_type} {configuration}"


def expected_targets(workspace, kind):
    return {
        request_target(request): request
        for request in create_requests(Path(workspace), kind)
    }


def mapping_entries_by_blind_id(mapping):
    entries = {}
    duplicates = []
    for entry in mapping.get("entries", []):
        blind_id = entry.get("blind_id")
        if not blind_id:
            continue
        if blind_id in entries:
            duplicates.append(blind_id)
            continue
        entries[blind_id] = entry
    return entries, duplicates


def target_is_complete(target):
    return all(target)


def equivalent_path(left, right):
    return Path(left).resolve(strict=False) == Path(right).resolve(strict=False)


def validate_request_shape(request, workspace):
    line = request.get("_line_number", "?")
    errors = []
    if request.get("request_type") != "score-update-request":
        errors.append(f"line {line}: request_type must be score-update-request")

    packet = request.get("packet")
    if not isinstance(packet, dict):
        errors.append(f"line {line}: packet must be an object")
        packet = {}

    template = request.get("score_update_template")
    if not isinstance(template, dict):
        errors.append(f"line {line}: score_update_template must be an object")
        template = {}

    provenance = request.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"line {line}: provenance must be an object")
        provenance = {}

    workspace_value = provenance.get("workspace")
    if not workspace_value:
        errors.append(f"line {line}: provenance.workspace is required")
    elif not equivalent_path(workspace_value, workspace):
        errors.append(
            f"line {line}: provenance.workspace does not match {workspace_value} != {workspace}"
        )

    expected_scorecard = Path(workspace) / "scorecard.json"
    scorecard_value = provenance.get("scorecard")
    if not scorecard_value:
        errors.append(f"line {line}: provenance.scorecard is required")
    elif not equivalent_path(scorecard_value, expected_scorecard):
        errors.append(
            f"line {line}: provenance.scorecard does not match "
            f"{scorecard_value} != {expected_scorecard}"
        )

    if provenance.get("rubric") != RUBRIC_SOURCE:
        errors.append(f"line {line}: provenance.rubric must be {RUBRIC_SOURCE}")

    rubric_context = request.get("rubric_context")
    if not isinstance(rubric_context, dict):
        errors.append(f"line {line}: rubric_context must be an object")
        rubric_context = {}

    if rubric_context.get("source") != RUBRIC_SOURCE:
        errors.append(f"line {line}: rubric_context.source must be {RUBRIC_SOURCE}")

    score_scale = rubric_context.get("score_scale")
    if not isinstance(score_scale, dict):
        errors.append(f"line {line}: rubric_context.score_scale must be an object")
    elif score_scale.get("min") != 0 or score_scale.get("max") != 2:
        errors.append(f"line {line}: rubric_context.score_scale must be 0..2")

    packet_target = target_from_mapping(packet.get("score_update_target", {}))
    scoring_target = target_from_mapping(template)
    if target_is_complete(packet_target) and target_is_complete(scoring_target):
        if packet_target != scoring_target:
            errors.append(
                f"line {line}: template target does not match packet target "
                f"{format_target(scoring_target)} != {format_target(packet_target)}"
            )

    score = template.get("score")
    dimensions = packet.get("score_dimensions", [])
    dimension_guidance = rubric_context.get("dimension_guidance")
    if not isinstance(dimension_guidance, dict):
        errors.append(f"line {line}: rubric_context.dimension_guidance must be an object")
        dimension_guidance = {}

    if not isinstance(score, dict):
        errors.append(f"line {line}: score_update_template.score must be an object")
    elif isinstance(dimensions, list):
        for dimension in dimensions:
            if dimension not in score:
                errors.append(f"line {line}: score template missing {dimension}")
            if dimension not in dimension_guidance:
                errors.append(f"line {line}: rubric context missing {dimension}")
        if "total" not in score:
            errors.append(f"line {line}: score template missing total")

    return errors


def validate_blind_request_shape(request, workspace):
    line = request.get("_line_number", "?")
    errors = []
    if request.get("request_type") != "blind-score-update-request":
        errors.append(f"line {line}: request_type must be blind-score-update-request")

    packet = request.get("packet")
    if not isinstance(packet, dict):
        errors.append(f"line {line}: packet must be an object")
        packet = {}

    if "configuration" in packet:
        errors.append(f"line {line}: blinded packet must not expose configuration")
    if "score_update_target" in packet:
        errors.append(f"line {line}: blinded packet must not expose score_update_target")

    template = request.get("blind_score_update_template")
    if not isinstance(template, dict):
        errors.append(f"line {line}: blind_score_update_template must be an object")
        template = {}

    blind_id = request.get("blind_id")
    template_blind_id = template.get("blind_id")
    if not blind_id:
        errors.append(f"line {line}: blind_id is required")
    elif template_blind_id != blind_id:
        errors.append(f"line {line}: blind_score_update_template blind_id mismatch")

    provenance = request.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"line {line}: provenance must be an object")
        provenance = {}

    if provenance.get("blind") is not True:
        errors.append(f"line {line}: provenance.blind must be true")

    workspace_value = provenance.get("workspace")
    if not workspace_value:
        errors.append(f"line {line}: provenance.workspace is required")
    elif not equivalent_path(workspace_value, workspace):
        errors.append(
            f"line {line}: provenance.workspace does not match {workspace_value} != {workspace}"
        )

    expected_scorecard = Path(workspace) / "scorecard.json"
    scorecard_value = provenance.get("scorecard")
    if not scorecard_value:
        errors.append(f"line {line}: provenance.scorecard is required")
    elif not equivalent_path(scorecard_value, expected_scorecard):
        errors.append(
            f"line {line}: provenance.scorecard does not match "
            f"{scorecard_value} != {expected_scorecard}"
        )

    if provenance.get("rubric") != RUBRIC_SOURCE:
        errors.append(f"line {line}: provenance.rubric must be {RUBRIC_SOURCE}")

    rubric_context = request.get("rubric_context")
    if not isinstance(rubric_context, dict):
        errors.append(f"line {line}: rubric_context must be an object")
        rubric_context = {}

    if rubric_context.get("source") != RUBRIC_SOURCE:
        errors.append(f"line {line}: rubric_context.source must be {RUBRIC_SOURCE}")

    score_scale = rubric_context.get("score_scale")
    if not isinstance(score_scale, dict):
        errors.append(f"line {line}: rubric_context.score_scale must be an object")
    elif score_scale.get("min") != 0 or score_scale.get("max") != 2:
        errors.append(f"line {line}: rubric_context.score_scale must be 0..2")

    score = template.get("score")
    dimensions = packet.get("score_dimensions", [])
    dimension_guidance = rubric_context.get("dimension_guidance")
    if not isinstance(dimension_guidance, dict):
        errors.append(f"line {line}: rubric_context.dimension_guidance must be an object")
        dimension_guidance = {}

    if not isinstance(score, dict):
        errors.append(f"line {line}: blind_score_update_template.score must be an object")
    elif isinstance(dimensions, list):
        for dimension in dimensions:
            if dimension not in score:
                errors.append(f"line {line}: score template missing {dimension}")
            if dimension not in dimension_guidance:
                errors.append(f"line {line}: rubric context missing {dimension}")
        if "total" not in score:
            errors.append(f"line {line}: score template missing total")

    return errors


def validate_requests(workspace, requests, kind):
    expected = expected_targets(workspace, kind)
    seen = {}
    missing_targets = []
    duplicate_targets = []
    unknown_targets = []
    errors = []

    for request in requests:
        errors.extend(validate_request_shape(request, workspace))

        target = request_target(request)
        line = request.get("_line_number", "?")
        if not target_is_complete(target):
            errors.append(f"line {line}: scoring request target is incomplete")
            unknown_targets.append(target)
            continue

        if target not in expected:
            errors.append(f"unknown scoring request {format_target(target)}")
            unknown_targets.append(target)
            continue

        if target in seen:
            errors.append(f"duplicate scoring request {format_target(target)}")
            duplicate_targets.append(target)
            continue

        seen[target] = request

    missing_targets = sorted(set(expected).difference(seen))
    for target in missing_targets:
        errors.append(f"missing scoring request {format_target(target)}")

    return {
        "ok": not errors,
        "expected_requests": len(expected),
        "provided_requests": len(requests),
        "covered_requests": len(seen),
        "missing_request_count": len(missing_targets),
        "duplicate_request_count": len(duplicate_targets),
        "unknown_request_count": len(unknown_targets),
        "missing_targets": [format_target(target) for target in missing_targets],
        "duplicate_targets": [format_target(target) for target in duplicate_targets],
        "unknown_targets": [format_target(target) for target in unknown_targets],
        "errors": errors,
    }


def validate_blind_requests(workspace, requests, mapping, kind):
    expected = set(expected_targets(workspace, kind))
    entries, duplicate_blind_ids = mapping_entries_by_blind_id(mapping)
    seen = {}
    errors = []
    unknown_targets = []
    duplicate_targets = []

    for blind_id in duplicate_blind_ids:
        errors.append(f"duplicate blind mapping {blind_id}")

    mapping_targets = {}
    for blind_id, entry in entries.items():
        target = target_from_mapping(entry.get("score_update_target", {}))
        if not target_is_complete(target):
            errors.append(f"blind mapping {blind_id} target is incomplete")
            unknown_targets.append(target)
            continue
        if target not in expected:
            errors.append(f"blind mapping {blind_id} targets unknown score {format_target(target)}")
            unknown_targets.append(target)
            continue
        mapping_targets[blind_id] = target

    missing_mapping_targets = sorted(expected.difference(set(mapping_targets.values())))
    for target in missing_mapping_targets:
        errors.append(f"missing blind mapping for {format_target(target)}")

    for request in requests:
        errors.extend(validate_blind_request_shape(request, workspace))
        blind_id = request.get("blind_id")
        line = request.get("_line_number", "?")
        if not blind_id:
            unknown_targets.append((None, None, None))
            continue
        if blind_id not in mapping_targets:
            errors.append(f"unknown blind scoring request {blind_id}")
            unknown_targets.append((blind_id, None, None))
            continue
        if blind_id in seen:
            errors.append(f"duplicate blind scoring request {blind_id}")
            duplicate_targets.append((blind_id, None, None))
            continue
        seen[blind_id] = request

    missing_blind_ids = sorted(set(mapping_targets).difference(seen))
    for blind_id in missing_blind_ids:
        errors.append(f"missing blind scoring request {blind_id}")

    return {
        "ok": not errors,
        "expected_requests": len(mapping_targets),
        "provided_requests": len(requests),
        "covered_requests": len(seen),
        "missing_request_count": len(missing_blind_ids),
        "duplicate_request_count": len(duplicate_targets),
        "unknown_request_count": len(unknown_targets),
        "missing_targets": missing_blind_ids,
        "duplicate_targets": [target[0] for target in duplicate_targets],
        "unknown_targets": [target[0] for target in unknown_targets],
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--kind", choices=("individual", "pair", "all"), default="all")
    parser.add_argument("--blind", action="store_true")
    parser.add_argument("--mapping")
    args = parser.parse_args()

    try:
        requests = load_requests(args.requests)
        mapping = load_mapping(args.mapping) if args.mapping else None
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

    if args.blind and mapping is None:
        raise SystemExit("--blind requires --mapping")

    report = (
        validate_blind_requests(Path(args.workspace), requests, mapping, args.kind)
        if args.blind
        else validate_requests(Path(args.workspace), requests, args.kind)
    )
    print(json.dumps(report, indent=2, sort_keys=True))

    if not report["ok"]:
        for error in report["errors"]:
            print(error, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
