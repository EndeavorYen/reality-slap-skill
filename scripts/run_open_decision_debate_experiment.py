#!/usr/bin/env python3
"""Execute or audit open-decision debate generation and judging records."""

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import random
import subprocess
import time
from pathlib import Path

from create_open_decision_debate_workspace import (
    DEPENDENCY_PACKET_MARKER,
    load_records,
)
from create_weak_challenge_swarm_workspace import (
    CHALLENGE_PACKET_MARKER,
    DRAFT_MARKER,
)


MAX_ATTEMPTS = 2
INVALID_OUTPUT_MARKERS = (
    "ERROR: child process timed out after",
    "ERROR: You've hit your usage limit",
    "ERROR: child process exited with status",
)
USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_usage_events(text):
    completed = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL event at line {line_number}") from error
        if event.get("type") == "turn.completed":
            completed.append(event)
    if len(completed) != 1:
        raise ValueError(
            "expected exactly one turn.completed usage event, "
            f"found {len(completed)}"
        )
    usage = completed[0].get("usage")
    if not isinstance(usage, dict):
        raise ValueError("turn.completed is missing usage")
    missing = [field for field in USAGE_FIELDS if field not in usage]
    if missing:
        raise ValueError(f"missing usage field: {missing[0]}")
    result = {}
    for field in USAGE_FIELDS:
        value = usage[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"invalid usage field: {field}")
        result[field] = value
    return result


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


def _dependency_payload(dependency):
    return json.loads(Path(dependency["output_path"]).read_text(encoding="utf-8"))


def _weak_swarm_dependencies(record, records_by_id):
    if records_by_id is None:
        raise ValueError("weak-swarm semantic validation requires dependency records")
    dependencies = []
    for call_id in record.get("depends_on", []):
        dependency = records_by_id.get(call_id)
        if dependency is None:
            raise ValueError(f"dependency record is missing: {call_id}")
        dependencies.append(dependency)
    return dependencies


def expected_challenge_ids(record, records_by_id, manifest=None):
    if record.get("kind") != "revision" or record.get("condition") not in {"C0", "C1"}:
        return []
    dependencies = _weak_swarm_dependencies(record, records_by_id)
    challenge_dependencies = [
        dependency for dependency in dependencies if dependency.get("kind") == "challenge"
    ]
    if manifest is not None:
        expected_roles = manifest["challenge_order_by_case"][record["case_id"]]
        observed_roles = [dependency.get("role") for dependency in challenge_dependencies]
        if observed_roles != expected_roles:
            raise ValueError("challenge dependency order differs from manifest")
    identifiers = []
    for dependency in challenge_dependencies:
        payload = _dependency_payload(dependency)
        for index, _challenge in enumerate(payload["challenges"], start=1):
            identifiers.append(f"{dependency['role'].upper()}-{index}")
    return identifiers


def rendered_challenge_packet(record, records_by_id, manifest):
    dependencies = _weak_swarm_dependencies(record, records_by_id)
    if record.get("packet_mode") == "opaque_questions":
        questions = []
        for dependency in dependencies:
            if dependency.get("kind") != "question":
                continue
            payload = _dependency_payload(dependency)
            questions.extend(payload["questions"])
        random.Random(
            f"{manifest['seed']}:{record['call_id']}:opaque-question-packet"
        ).shuffle(questions)
        return [
            {
                "question_id": f"Q-{index}",
                "target": question["target"],
                "question": question["question"],
            }
            for index, question in enumerate(questions, start=1)
        ]
    challenge_dependencies = [
        dependency for dependency in dependencies if dependency.get("kind") == "challenge"
    ]
    expected_roles = manifest["challenge_order_by_case"][record["case_id"]]
    observed_roles = [dependency.get("role") for dependency in challenge_dependencies]
    if observed_roles != expected_roles:
        raise ValueError("challenge dependency order differs from manifest")
    packet = []
    for dependency in challenge_dependencies:
        payload = _dependency_payload(dependency)
        for index, challenge in enumerate(payload["challenges"], start=1):
            packet.append(
                {
                    "challenge_id": f"{dependency['role'].upper()}-{index}",
                    "source_role": dependency["role"],
                    "payload": challenge,
                }
            )
    return packet


def _shared_draft(record, records_by_id):
    dependencies = _weak_swarm_dependencies(record, records_by_id)
    drafts = [
        dependency for dependency in dependencies if dependency.get("kind") == "draft"
    ]
    if len(drafts) != 1:
        raise ValueError("weak-swarm record requires exactly one shared draft")
    return _dependency_payload(drafts[0])


def shared_input_hashes(record, records_by_id, manifest):
    draft = _shared_draft(record, records_by_id)
    result = {
        "shared_draft_sha256": sha256_text(
            json.dumps(draft, sort_keys=True, separators=(",", ":"))
        )
    }
    prompt_template = Path(record["prompt_path"]).read_text(encoding="utf-8")
    if CHALLENGE_PACKET_MARKER in prompt_template:
        packet = rendered_challenge_packet(record, records_by_id, manifest)
        result["challenge_packet_sha256"] = sha256_text(
            json.dumps(packet, sort_keys=True, separators=(",", ":"))
        )
    return result


def validate_record_payload(record, payload, records_by_id=None, manifest=None):
    schema = json.loads(Path(record["schema_path"]).read_text(encoding="utf-8"))
    validate_payload(payload, schema)
    if record["kind"] in {"role", "cross_exam", "self_review"}:
        if payload.get("role") != record.get("role"):
            raise ValueError("$.role: must match the record role")
    if record["kind"] == "challenge":
        if payload.get("role") != record.get("role"):
            raise ValueError("$.role: must match the challenger role")
    if record["kind"] == "revision":
        observed = [
            item["challenge_id"] for item in payload["challenge_dispositions"]
        ]
        expected = expected_challenge_ids(record, records_by_id, manifest)
        if observed != expected or len(set(observed)) != len(observed):
            raise ValueError(
                "$.challenge_dispositions: must cover each challenge exactly once"
            )
    if record["kind"] == "serial" and record["phase"] != "final":
        if payload.get("phase") != record["phase"]:
            raise ValueError("$.phase: must match the record phase")
    if record["kind"] == "judge":
        if payload.get("case_id") != record["case_id"]:
            raise ValueError("$.case_id: must match the judge record")
        expected_labels = set(record["candidate_labels"])
        observed_labels = [item["label"] for item in payload["evaluations"]]
        if set(observed_labels) != expected_labels or len(observed_labels) != len(expected_labels):
            raise ValueError("$.evaluations: must contain each candidate label exactly once")
        for item in payload["evaluations"]:
            if record.get("judge_contract") == "weak-challenge-checklist":
                for field in ("must_cover", "closure", "fatal_errors"):
                    observed_ids = [
                        checklist_item["item_id"]
                        for checklist_item in item[field]
                    ]
                    expected_ids = record["checklist_item_ids"][field]
                    if (
                        observed_ids != expected_ids
                        or len(set(observed_ids)) != len(expected_ids)
                    ):
                        raise ValueError(
                            f"$.evaluations.{field}: must contain each checklist "
                            "item exactly once"
                        )
                    for checklist_item in item[field]:
                        if len(checklist_item["explanation"].strip()) < 12:
                            raise ValueError(
                                f"$.evaluations.{field}.explanation: "
                                "must contain a substantive explanation"
                            )
                for explanation in item["critical_explanations"].values():
                    if len(explanation.strip()) < 12:
                        raise ValueError(
                            "$.evaluations.critical_explanations: "
                            "must contain substantive explanations"
                        )
                if len(item["summary"].strip()) < 12:
                    raise ValueError(
                        "$.evaluations.summary: must contain a substantive summary"
                    )
            if item["total_score"] != sum(item["scores"].values()):
                raise ValueError("$.evaluations: total_score must equal the dimension scores")
        ranking = payload["ranking"]
        if set(ranking) != expected_labels or len(set(ranking)) != len(expected_labels):
            raise ValueError("$.ranking: must contain each candidate label exactly once")
        expected_pairs = {
            frozenset(pair) for pair in itertools.combinations(expected_labels, 2)
        }
        observed_pairs = set()
        for item in payload["pairwise_preferences"]:
            pair = frozenset((item["left_label"], item["right_label"]))
            if len(pair) != 2:
                raise ValueError("$.pairwise_preferences: pair labels must be distinct")
            if item["winner"] != "tie" and item["winner"] not in pair:
                raise ValueError("$.pairwise_preferences: winner must belong to the pair")
            if (
                record.get("judge_contract") == "weak-challenge-checklist"
                and len(item["rationale"].strip()) < 12
            ):
                raise ValueError(
                    "$.pairwise_preferences.rationale: "
                    "must contain a substantive rationale"
                )
            observed_pairs.add(pair)
        if (
            observed_pairs != expected_pairs
            or len(payload["pairwise_preferences"]) != len(expected_pairs)
        ):
            raise ValueError(
                "$.pairwise_preferences: must contain every unordered pair exactly once"
            )


def invalid_marker(text):
    stripped = text.strip()
    return next(
        (marker for marker in INVALID_OUTPUT_MARKERS if stripped.startswith(marker)),
        "",
    )


def response_status(record, records_by_id=None, manifest=None):
    path = Path(record["output_path"])
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return "missing"
    text = path.read_text(encoding="utf-8")
    if invalid_marker(text):
        return "invalid"
    try:
        payload = json.loads(text)
        validate_record_payload(record, payload, records_by_id, manifest)
    except (json.JSONDecodeError, OSError, ValueError):
        return "invalid"
    return "complete"


def load_call_metadata(record):
    path = Path(record["metadata_path"])
    if not path.exists():
        return {"call_id": record["call_id"], "attempts": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid call metadata: {record['call_id']}") from error
    if not isinstance(payload.get("attempts"), list):
        raise ValueError(f"invalid call metadata attempts: {record['call_id']}")
    return payload


def save_call_metadata(record, metadata):
    path = Path(record["metadata_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def call_eligibility(record, records_by_id, max_attempts=MAX_ATTEMPTS):
    metadata = load_call_metadata(record)
    attempts = metadata["attempts"]
    latest_invalid_reason = attempts[-1].get("invalid_reason", "") if attempts else ""
    if (
        response_status(record, records_by_id) == "complete"
        and not latest_invalid_reason
    ):
        return "complete"
    if len(attempts) >= max_attempts:
        return "retry-exhausted"
    if any(
        dependency not in records_by_id
        or response_status(records_by_id[dependency], records_by_id) != "complete"
        for dependency in record.get("depends_on", [])
    ):
        return "blocked"
    return "ready"


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_phase_records(workspace, phase):
    workspace = Path(workspace)
    if phase == "generation":
        return load_records(workspace)
    if phase == "judge":
        return load_jsonl(workspace / "judge-records.jsonl")
    raise ValueError(f"unknown phase: {phase}")


def iter_pending_calls(workspace, phase, max_attempts=MAX_ATTEMPTS):
    records = load_phase_records(workspace, phase)
    records_by_id = {record["call_id"]: record for record in records}
    for record in records:
        if call_eligibility(record, records_by_id, max_attempts) == "ready":
            yield record


def dependency_packet(record, records_by_id, manifest):
    dependencies = [records_by_id[call_id] for call_id in record.get("depends_on", [])]
    entries = []
    if record["kind"] == "cross_exam":
        own = next(item for item in dependencies if item.get("role") == record.get("role"))
        peers = [item for item in dependencies if item["call_id"] != own["call_id"]]
        random.Random(f"{manifest['seed']}:{record['call_id']}:peers").shuffle(peers)
        ordered = [("SELF", own)] + [
            (f"PEER-{chr(ord('A') + index)}", item)
            for index, item in enumerate(peers)
        ]
    else:
        shuffled = list(dependencies)
        random.Random(f"{manifest['seed']}:{record['call_id']}:dependencies").shuffle(shuffled)
        prefix = "ARTIFACT" if record["kind"] == "serial" else "RECORD"
        ordered = [
            (f"{prefix}-{chr(ord('A') + index)}", item)
            for index, item in enumerate(shuffled)
        ]
    for label, dependency in ordered:
        entry = {
            "label": label,
            "source_phase": dependency["phase"],
            "payload": json.loads(Path(dependency["output_path"]).read_text(encoding="utf-8")),
        }
        if dependency.get("role"):
            entry["source_role"] = dependency["role"] if label == "SELF" else "anonymous-peer"
        entries.append(entry)
    return entries


def render_prompt(record, records_by_id, manifest):
    prompt = Path(record["prompt_path"]).read_text(encoding="utf-8").rstrip()
    if not record.get("depends_on"):
        return prompt
    for call_id in record["depends_on"]:
        dependency = records_by_id.get(call_id)
        if dependency is None or response_status(dependency, records_by_id, manifest) != "complete":
            raise ValueError(f"dependency is incomplete: {call_id}")
    if DRAFT_MARKER in prompt:
        prompt = prompt.replace(
            DRAFT_MARKER,
            json.dumps(_shared_draft(record, records_by_id), indent=2, sort_keys=True),
        )
    if CHALLENGE_PACKET_MARKER in prompt:
        prompt = prompt.replace(
            CHALLENGE_PACKET_MARKER,
            json.dumps(
                rendered_challenge_packet(record, records_by_id, manifest),
                indent=2,
                sort_keys=True,
            ),
        )
    if DRAFT_MARKER in Path(record["prompt_path"]).read_text(encoding="utf-8"):
        return prompt
    if DEPENDENCY_PACKET_MARKER not in prompt:
        raise ValueError(f"dependency marker missing: {record['call_id']}")
    packet = dependency_packet(record, records_by_id, manifest)
    return prompt.replace(
        DEPENDENCY_PACKET_MARKER,
        json.dumps(packet, indent=2, sort_keys=True),
    )


def build_command(record, codex_bin, cwd, prompt):
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
        "--json",
        "--model",
        record["model"],
        "--config",
        f'model_reasoning_effort="{record["reasoning_effort"]}"',
        "-C",
        str(Path(cwd).absolute()),
        "--skip-git-repo-check",
        "--output-schema",
        str(Path(record["schema_path"]).absolute()),
        "--output-last-message",
        str(Path(record["output_path"]).absolute()),
        prompt,
    ]


def execute_call(record, records_by_id, manifest, codex_bin, cwd, timeout_seconds):
    prompt = render_prompt(record, records_by_id, manifest)
    output_path = Path(record["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    metadata = load_call_metadata(record)
    attempt_number = len(metadata["attempts"]) + 1
    command = build_command(record, codex_bin, cwd, prompt)
    log_path = Path(record["log_path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    events_path = log_path.parent / f"events-attempt-{attempt_number}.jsonl"
    started = time.monotonic()
    timed_out = False
    returncode = 0
    with (
        log_path.open("a", encoding="utf-8") as log_file,
        events_path.open("w", encoding="utf-8") as events_file,
    ):
        log_file.write(f"\n=== attempt {attempt_number} ===\n")
        try:
            result = subprocess.run(
                command,
                check=False,
                text=True,
                stdout=events_file,
                stderr=log_file,
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
    elapsed = time.monotonic() - started
    status = response_status(record, records_by_id, manifest)
    output_text = (
        output_path.read_text(encoding="utf-8")
        if output_path.exists()
        else ""
    )
    usage = None
    usage_error = ""
    try:
        usage = parse_usage_events(events_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        usage_error = str(error)
    if timed_out:
        invalid_reason = "timeout"
    elif returncode != 0:
        invalid_reason = f"exit-{returncode}"
    elif status != "complete":
        invalid_reason = "invalid-output"
    elif usage_error:
        invalid_reason = "missing-usage"
    else:
        invalid_reason = ""
    metadata["call_id"] = record["call_id"]
    metadata["model"] = record["model"]
    metadata["reasoning_effort"] = record["reasoning_effort"]
    attempt = {
            "attempt": attempt_number,
            "returncode": returncode,
            "timed_out": timed_out,
            "invalid_reason": invalid_reason,
            "elapsed_seconds": round(elapsed, 6),
            "prompt_characters": len(prompt),
            "prompt_sha256": sha256_text(prompt),
            "output_characters": len(output_text),
            "output_sha256": sha256_text(output_text),
            "events_path": str(events_path),
            "usage": usage,
            "usage_error": usage_error,
        }
    if DRAFT_MARKER in Path(record["prompt_path"]).read_text(encoding="utf-8"):
        attempt["shared_input_hashes"] = shared_input_hashes(
            record,
            records_by_id,
            manifest,
        )
    metadata["attempts"].append(attempt)
    save_call_metadata(record, metadata)
    return {
        "call_id": record["call_id"],
        "attempt": attempt_number,
        "status": status if not invalid_reason else "invalid",
        "invalid_reason": invalid_reason,
    }


def audit_records(records):
    records_by_id = {record["call_id"]: record for record in records}
    audit = {
        "record_count": len(records),
        "complete_call_ids": [],
        "missing_call_ids": [],
        "invalid_call_ids": [],
        "retry_exhausted_call_ids": [],
        "dependency_blocked_call_ids": [],
        "ready_call_ids": [],
    }
    for record in records:
        status = response_status(record, records_by_id)
        eligibility = call_eligibility(record, records_by_id)
        if status == "complete":
            audit["complete_call_ids"].append(record["call_id"])
        elif status == "missing":
            audit["missing_call_ids"].append(record["call_id"])
        else:
            audit["invalid_call_ids"].append(record["call_id"])
        if eligibility == "retry-exhausted":
            audit["retry_exhausted_call_ids"].append(record["call_id"])
        elif eligibility == "blocked":
            audit["dependency_blocked_call_ids"].append(record["call_id"])
        elif eligibility == "ready":
            audit["ready_call_ids"].append(record["call_id"])
    for key, value in audit.items():
        if isinstance(value, list):
            value.sort()
    audit["complete_count"] = len(audit["complete_call_ids"])
    audit["ready_count"] = len(audit["ready_call_ids"])
    return audit


def audit_workspace(workspace):
    workspace = Path(workspace)
    generation = audit_records(load_phase_records(workspace, "generation"))
    judge_records = load_phase_records(workspace, "judge")
    judge = audit_records(judge_records) if judge_records else {
        "record_count": 0,
        "complete_count": 0,
        "ready_count": 0,
        "complete_call_ids": [],
        "missing_call_ids": [],
        "invalid_call_ids": [],
        "retry_exhausted_call_ids": [],
        "dependency_blocked_call_ids": [],
        "ready_call_ids": [],
    }
    combined = {
        "generation": generation,
        "judge": judge,
    }
    for field in (
        "missing_call_ids",
        "invalid_call_ids",
        "retry_exhausted_call_ids",
        "dependency_blocked_call_ids",
        "ready_call_ids",
    ):
        combined[field] = sorted(generation[field] + judge[field])
    return combined


def run_phase(
    workspace,
    phase,
    codex_bin,
    cwd,
    timeout_seconds,
    max_workers,
    max_attempts=MAX_ATTEMPTS,
):
    workspace = Path(workspace)
    manifest = json.loads((workspace / "manifest.json").read_text(encoding="utf-8"))
    results = []
    while True:
        records = load_phase_records(workspace, phase)
        records_by_id = {record["call_id"]: record for record in records}
        ready = [
            record
            for record in records
            if call_eligibility(record, records_by_id, max_attempts) == "ready"
        ]
        if not ready:
            break
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(
                    execute_call,
                    record,
                    records_by_id,
                    manifest,
                    codex_bin,
                    cwd,
                    timeout_seconds,
                )
                for record in ready
            ]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    return {"results": results, "audit": audit_workspace(workspace)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--phase", choices=("generation", "judge"), required=True)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--cwd", default="/private/tmp")
    parser.add_argument("--timeout-seconds", type=float, default=240)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--max-attempts", type=int, choices=range(1, 4), default=MAX_ATTEMPTS)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if args.audit_only:
        payload = audit_workspace(args.workspace)
    else:
        payload = run_phase(
            args.workspace,
            args.phase,
            args.codex_bin,
            args.cwd,
            args.timeout_seconds,
            args.max_workers,
            args.max_attempts,
        )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
