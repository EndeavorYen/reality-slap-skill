#!/usr/bin/env python3
"""Dry-run or execute Codex scorer requests and append score updates."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


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
            raise ValueError(f"request line {line_number}: invalid JSON: {error}") from error
        requests.append(request)
    return requests


def target_from_mapping(mapping):
    return (
        mapping.get("scenario_id"),
        mapping.get("score_type"),
        mapping.get("configuration"),
    )


def target_from_request(request):
    if request.get("request_type") != "score-update-request":
        raise ValueError("run_scoring_requests.py supports non-blind score-update requests only")

    packet_target = target_from_mapping(
        request.get("packet", {}).get("score_update_target", {})
    )
    template_target = target_from_mapping(request.get("score_update_template", {}))
    if packet_target != template_target or not all(packet_target):
        raise ValueError(f"request target mismatch or incomplete: {packet_target} != {template_target}")
    return packet_target


def load_existing_updates(path):
    updates_path = Path(path)
    if not updates_path.exists():
        return {}

    updates = {}
    for line_number, line in enumerate(
        updates_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            update = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"update line {line_number}: invalid JSON: {error}") from error
        target = target_from_mapping(update)
        if not all(target):
            raise ValueError(f"update line {line_number}: incomplete target {target}")
        updates[target] = update
    return updates


def scoring_prompt(request):
    return (
        "Score this Reality Slap evaluation request.\n"
        "Return exactly one JSON object and no markdown fences.\n"
        "The object must match score_update_template exactly at the top level: "
        "scenario_id, score_type, configuration, and score.\n"
        "Set every score dimension to an integer 0, 1, or 2, and set total to "
        "the sum of the dimensions.\n"
        "Use the supplied rubric_context only. Do not read repo files, memory, or web.\n\n"
        "Scoring request JSON:\n"
        f"{json.dumps(request, indent=2, sort_keys=True)}"
    )


def safe_name(target):
    scenario_id, score_type, configuration = target
    return f"{scenario_id}-{score_type}-{configuration}.json".replace("/", "_")


def response_path_for(response_dir, target):
    return Path(response_dir) / safe_name(target)


def child_log_path_for(child_log_dir, target):
    scenario_id, score_type, configuration = target
    return Path(child_log_dir) / scenario_id / f"{score_type}-{configuration}.log"


def build_command(codex_bin, cwd, output_path, prompt, skip_git_repo_check=False):
    command = [
        codex_bin,
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "-C",
        str(cwd),
        "--output-last-message",
        str(output_path),
    ]
    if skip_git_repo_check:
        command.append("--skip-git-repo-check")
    command.append(prompt)
    return command


def extract_json_object(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1]).strip()
            if stripped.startswith("json\n"):
                stripped = stripped[5:].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def validate_update_matches_request(update, target):
    update_target = target_from_mapping(update)
    if update_target != target:
        raise ValueError(f"scorer returned target {update_target}, expected {target}")
    if not isinstance(update.get("score"), dict):
        raise ValueError(f"scorer returned update without score object for {target}")


def append_update(path, update):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(update, sort_keys=True) + "\n")


def compact_event(event):
    event = dict(event)
    command = list(event["command"])
    prompt = command[-1]
    command[-1] = f"<prompt omitted: {len(prompt)} chars>"
    event["command"] = command
    event["prompt_chars"] = len(prompt)
    return event


def iter_runs(requests, updates_path, include_complete, limit):
    existing = load_existing_updates(updates_path)
    emitted = 0
    for request in requests:
        target = target_from_request(request)
        if not include_complete and target in existing:
            continue
        yield target, request
        emitted += 1
        if limit is not None and emitted >= limit:
            return


def run_requests(
    requests_path,
    updates_path,
    response_dir,
    codex_bin,
    cwd,
    include_complete,
    execute,
    skip_git_repo_check,
    limit,
    child_log_dir=None,
    child_timeout_seconds=None,
    compact_events=False,
):
    requests = load_requests(requests_path)
    mode = "execute" if execute else "dry-run"
    for target, request in iter_runs(requests, updates_path, include_complete, limit):
        prompt = scoring_prompt(request)
        response_path = response_path_for(response_dir, target)
        response_path.parent.mkdir(parents=True, exist_ok=True)
        command = build_command(
            codex_bin,
            cwd,
            response_path,
            prompt,
            skip_git_repo_check=skip_git_repo_check,
        )
        event = {
            "target": {
                "scenario_id": target[0],
                "score_type": target[1],
                "configuration": target[2],
            },
            "mode": mode,
            "response_path": str(response_path),
            "updates_path": str(updates_path),
            "command": command,
        }
        child_log_path = None
        if child_log_dir:
            child_log_path = child_log_path_for(child_log_dir, target)
            event["child_log_path"] = str(child_log_path)
        print(json.dumps(compact_event(event) if compact_events else event, sort_keys=True))

        if not execute:
            continue

        if child_log_path:
            child_log_path.parent.mkdir(parents=True, exist_ok=True)
            log_target = child_log_path.open("w", encoding="utf-8")
        else:
            log_target = subprocess.DEVNULL

        try:
            try:
                subprocess.run(
                    command,
                    cwd=cwd,
                    check=True,
                    stdout=log_target,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=child_timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                response_path.write_text(
                    f"ERROR: scorer child process timed out after {child_timeout_seconds:g} seconds\n",
                    encoding="utf-8",
                )
                print(
                    "scorer child run timed out after "
                    f"{child_timeout_seconds:g} seconds: {target}",
                    file=sys.stderr,
                )
                raise SystemExit(124)
        finally:
            if child_log_path:
                log_target.close()

        update = extract_json_object(response_path.read_text(encoding="utf-8"))
        validate_update_matches_request(update, target)
        append_update(updates_path, update)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--updates", required=True)
    parser.add_argument("--response-dir")
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--cwd", default=Path.cwd())
    parser.add_argument("--include-complete", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--skip-git-repo-check", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--child-log-dir")
    parser.add_argument("--child-timeout-seconds", type=float)
    parser.add_argument("--compact-events", action="store_true")
    args = parser.parse_args()

    response_dir = (
        Path(args.response_dir)
        if args.response_dir
        else Path(args.updates).parent / "scoring-responses"
    )

    try:
        run_requests(
            requests_path=Path(args.requests),
            updates_path=Path(args.updates),
            response_dir=response_dir,
            codex_bin=args.codex_bin,
            cwd=Path(args.cwd),
            include_complete=args.include_complete,
            execute=args.execute,
            skip_git_repo_check=args.skip_git_repo_check,
            limit=args.limit,
            child_log_dir=args.child_log_dir,
            child_timeout_seconds=args.child_timeout_seconds,
            compact_events=args.compact_events,
        )
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
