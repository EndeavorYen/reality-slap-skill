#!/usr/bin/env python3
"""Dry-run or execute the isolated-context roleplay experiment workspace."""

import argparse
import concurrent.futures
import json
import random
import subprocess
import time
from pathlib import Path

from create_isolated_roleplay_workspace import ROLE_OUTPUT_MARKER, load_records


INVALID_OUTPUT_MARKERS = (
    "ERROR: child process timed out after",
    "ERROR: You've hit your usage limit",
    "ERROR: child process exited with status",
)
MAX_ATTEMPTS = 2


def validate_payload(value, schema, path="$"):
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected object")
        required = set(schema.get("required", []))
        missing = sorted(required - set(value))
        if missing:
            raise ValueError(f"{path}: missing required properties: {', '.join(missing)}")
        properties = schema.get("properties", {})
        unexpected = sorted(set(value) - set(properties))
        if schema.get("additionalProperties") is False and unexpected:
            raise ValueError(f"{path}: unexpected properties: {', '.join(unexpected)}")
        for key, child in value.items():
            if key in properties:
                validate_payload(child, properties[key], f"{path}.{key}")
    elif expected_type == "array":
        if not isinstance(value, list):
            raise ValueError(f"{path}: expected array")
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"{path}: fewer than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{path}: more than maxItems")
        for index, child in enumerate(value):
            validate_payload(child, schema.get("items", {}), f"{path}[{index}]")
    elif expected_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"{path}: expected string")
        if len(value) < schema.get("minLength", 0):
            raise ValueError(f"{path}: shorter than minLength")
        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"{path}: value is not in enum")
    elif expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{path}: expected integer")
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path}: above maximum")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"{path}: expected boolean")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: value is not in enum")


def validate_record_payload(record, payload):
    schema = json.loads(Path(record["schema_path"]).read_text(encoding="utf-8"))
    validate_payload(payload, schema)
    if record["kind"] == "meeting":
        roles = [item["role"] for item in payload["roles"]]
        second_round_roles = [item["role"] for item in payload["second_round"]]
        expected = {"executive_sponsor", "evidence_reviewer", "delivery_owner"}
        if set(roles) != expected or len(set(roles)) != 3:
            raise ValueError("$.roles: must contain each role exactly once")
        if set(second_round_roles) != expected or len(set(second_round_roles)) != 3:
            raise ValueError("$.second_round: must contain each role exactly once")
    if record["kind"] == "judge":
        if payload["scenario_id"] != record["scenario_id"]:
            raise ValueError("$.scenario_id: must match the judge record")
        labels = [item["label"] for item in payload["evaluations"]]
        if set(labels) != {"A", "B", "C", "D"} or len(set(labels)) != 4:
            raise ValueError("$.evaluations: must contain each opaque label exactly once")
        expected_roles = {"executive_sponsor", "evidence_reviewer", "delivery_owner"}
        for index, evaluation in enumerate(payload["evaluations"]):
            roles = [item["role"] for item in evaluation["normalized_role_stances"]]
            if set(roles) != expected_roles or len(set(roles)) != 3:
                raise ValueError(
                    f"$.evaluations[{index}].normalized_role_stances: "
                    "must contain each role exactly once"
                )


def invalid_marker(text):
    stripped = text.strip()
    return next((marker for marker in INVALID_OUTPUT_MARKERS if stripped.startswith(marker)), "")


def response_status(record):
    path = Path(record["output_path"])
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return "missing"
    text = path.read_text(encoding="utf-8")
    if invalid_marker(text):
        return "invalid"
    try:
        payload = json.loads(text)
        validate_record_payload(record, payload)
    except (json.JSONDecodeError, ValueError, OSError):
        return "invalid"
    return "complete"


def load_call_metadata(record):
    path = Path(record["metadata_path"])
    if not path.exists():
        return {"call_id": record["call_id"], "attempts": []}
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid call metadata for {record['call_id']}") from error
    attempts = metadata.get("attempts")
    if not isinstance(attempts, list):
        raise ValueError(f"invalid attempts metadata for {record['call_id']}")
    return metadata


def save_call_metadata(record, metadata):
    path = Path(record["metadata_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def call_eligibility(record, records_by_id):
    if response_status(record) == "complete":
        return "complete"
    if len(load_call_metadata(record)["attempts"]) >= MAX_ATTEMPTS:
        return "retry-exhausted"
    if any(response_status(records_by_id[call_id]) != "complete" for call_id in record.get("depends_on", [])):
        return "blocked"
    return "ready"


def load_phase_records(workspace, phase):
    if phase == "generation":
        return load_records(workspace)
    if phase == "judge":
        path = Path(workspace) / "judge-records.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    raise ValueError(f"unknown phase: {phase}")


def iter_pending_calls(workspace, phase):
    records = load_phase_records(workspace, phase)
    records_by_id = {record["call_id"]: record for record in records}
    for record in records:
        if call_eligibility(record, records_by_id) == "ready":
            yield record


def render_prompt(record, records_by_id, manifest):
    prompt = Path(record["prompt_path"]).read_text(encoding="utf-8").rstrip()
    if record["kind"] != "chair" or not record.get("depends_on"):
        return prompt
    role_records = []
    for call_id in record["depends_on"]:
        dependency = records_by_id[call_id]
        if response_status(dependency) != "complete":
            raise ValueError(f"chair dependency is incomplete: {call_id}")
        role_records.append(
            {
                "role": dependency["role"],
                "sealed_record": json.loads(Path(dependency["output_path"]).read_text(encoding="utf-8")),
            }
        )
    random.Random(f"{manifest['seed']}:{record['call_id']}").shuffle(role_records)
    return prompt.replace(ROLE_OUTPUT_MARKER, json.dumps(role_records, indent=2, sort_keys=True))


def build_command(record, manifest, codex_bin, cwd, prompt):
    return [
        codex_bin,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--model",
        manifest["model"],
        "--config",
        f'model_reasoning_effort="{manifest["reasoning_effort"]}"',
        "-C",
        str(Path(cwd).absolute()),
        "--skip-git-repo-check",
        "--output-schema",
        str(Path(record["schema_path"]).absolute()),
        "--output-last-message",
        str(Path(record["output_path"]).absolute()),
        prompt,
    ]


def attempt_invalid_reason(record, returncode, timed_out):
    if timed_out:
        return "timeout"
    if returncode != 0:
        return f"exit-{returncode}"
    if response_status(record) != "complete":
        return "invalid-output"
    return ""


def execute_call(record, records_by_id, manifest, codex_bin, cwd, timeout_seconds):
    prompt = render_prompt(record, records_by_id, manifest)
    output_path = Path(record["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    metadata = load_call_metadata(record)
    attempt_number = len(metadata["attempts"]) + 1
    command = build_command(record, manifest, codex_bin, cwd, prompt)
    started = time.monotonic()
    timed_out = False
    returncode = 0
    log_path = Path(record["log_path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n=== attempt {attempt_number} ===\n")
        try:
            result = subprocess.run(
                command,
                check=False,
                text=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=timeout_seconds,
            )
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            returncode = 124
            output_path.write_text(
                f"ERROR: child process timed out after {timeout_seconds:g} seconds\n",
                encoding="utf-8",
            )
    if returncode != 0 and not output_path.exists():
        output_path.write_text(
            f"ERROR: child process exited with status {returncode}\n",
            encoding="utf-8",
        )
    elapsed = time.monotonic() - started
    status = response_status(record)
    attempt = {
        "attempt": attempt_number,
        "elapsed_seconds": round(elapsed, 6),
        "invalid_reason": attempt_invalid_reason(record, returncode, timed_out),
        "output_characters": output_path.stat().st_size if output_path.exists() else 0,
        "prompt_characters": len(prompt),
        "returncode": returncode,
        "status": status,
    }
    metadata["attempts"].append(attempt)
    metadata["call_id"] = record["call_id"]
    metadata["final_status"] = status
    save_call_metadata(record, metadata)
    return attempt


def run_workspace(workspace, phase, execute, jobs=2, limit=None, timeout_seconds=300, codex_bin="codex", cwd=Path("/private/tmp")):
    workspace = Path(workspace)
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
    records = load_phase_records(workspace, phase)
    records_by_id = {record["call_id"]: record for record in records}
    executed = []
    if not execute:
        pending = list(iter_pending_calls(workspace, phase))
        if limit is not None:
            pending = pending[:limit]
        return {
            "mode": "dry-run",
            "phase": phase,
            "ready_call_count": len(pending),
            "ready_call_ids": [record["call_id"] for record in pending],
        }

    while True:
        pending = [record for record in records if call_eligibility(record, records_by_id) == "ready"]
        remaining = None if limit is None else limit - len(executed)
        if remaining is not None:
            if remaining <= 0:
                break
            pending = pending[:remaining]
        if not pending:
            break
        if jobs == 1 or len(pending) == 1:
            batch = [
                (record, execute_call(record, records_by_id, manifest, codex_bin, cwd, timeout_seconds))
                for record in pending
            ]
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
                futures = {
                    executor.submit(
                        execute_call,
                        record,
                        records_by_id,
                        manifest,
                        codex_bin,
                        cwd,
                        timeout_seconds,
                    ): record
                    for record in pending
                }
                batch = [(futures[future], future.result()) for future in concurrent.futures.as_completed(futures)]
        executed.extend({"call_id": record["call_id"], **attempt} for record, attempt in batch)
    return {
        "mode": "execute",
        "phase": phase,
        "executed_attempt_count": len(executed),
        "attempts": executed,
        "audit": audit_workspace(workspace),
    }


def audit_workspace(workspace):
    generation = load_phase_records(workspace, "generation")
    judge = load_phase_records(workspace, "judge")
    all_records = generation + judge
    by_id = {record["call_id"]: record for record in all_records}
    statuses = {record["call_id"]: response_status(record) for record in all_records}
    exhausted = [
        record["call_id"]
        for record in all_records
        if statuses[record["call_id"]] != "complete"
        and len(load_call_metadata(record)["attempts"]) >= MAX_ATTEMPTS
    ]
    blocked = [
        record["call_id"]
        for record in all_records
        if any(statuses.get(call_id) != "complete" for call_id in record.get("depends_on", []))
    ]
    return {
        "generation_total": len(generation),
        "generation_complete": sum(statuses[record["call_id"]] == "complete" for record in generation),
        "judge_total": len(judge),
        "judge_complete": sum(statuses[record["call_id"]] == "complete" for record in judge),
        "invalid_call_ids": sorted(call_id for call_id, status in statuses.items() if status == "invalid"),
        "missing_call_ids": sorted(call_id for call_id, status in statuses.items() if status == "missing"),
        "retry_exhausted_call_ids": sorted(exhausted),
        "dependency_blocked_call_ids": sorted(blocked),
        "complete": bool(all_records) and all(status == "complete" for status in statuses.values()),
    }


def positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--phase", choices=("generation", "judge"), required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--jobs", type=positive_int, default=2)
    parser.add_argument("--limit", type=positive_int)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--cwd", default="/private/tmp")
    args = parser.parse_args()
    result = run_workspace(
        workspace=Path(args.workspace),
        phase=args.phase,
        execute=args.execute,
        jobs=args.jobs,
        limit=args.limit,
        timeout_seconds=args.timeout_seconds,
        codex_bin=args.codex_bin,
        cwd=Path(args.cwd),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
