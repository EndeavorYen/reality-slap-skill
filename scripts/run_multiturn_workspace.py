#!/usr/bin/env python3
"""Dry-run or execute true multi-turn Codex runs for a Reality Slap workspace."""

import argparse
import concurrent.futures
import json
import re
import subprocess
import sys
from pathlib import Path

from expand_eval_bank import SUITE_NAMES
from run_codex_workspace import (
    INVALID_OUTPUT_MARKERS,
    inline_skill_prompt,
    is_skill_configuration,
    positive_int,
    timeout_message,
)


class ChildRunTimeout(RuntimeError):
    pass


class MissingSessionId(RuntimeError):
    pass


def load_records(workspace):
    records_path = Path(workspace) / "records.jsonl"
    return [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def output_invalid_reason(text):
    stripped = text.strip()
    for marker in INVALID_OUTPUT_MARKERS:
        if stripped.startswith(marker):
            return marker
    return ""


def output_is_complete(path):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return False
    return not output_invalid_reason(text)


def read_turns(workspace, record):
    turns_path = Path(workspace) / record["turns_path"]
    return [
        json.loads(line)
        for line in turns_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_dir_for(workspace, record):
    return Path(workspace) / record["scenario_id"] / record["configuration"]


def final_output_path_for(workspace, record):
    return Path(workspace) / record["output_path"]


def turn_output_path_for(workspace, record, turn):
    return run_dir_for(workspace, record) / turn["output_path"]


def transcript_path_for(workspace, record):
    return Path(workspace) / record["transcript_path"]


def child_log_path_for(child_log_dir, run):
    return Path(child_log_dir) / run["scenario_id"] / f"{run['configuration']}.log"


def absolute(path):
    return str(Path(path).absolute())


def build_initial_command(codex_bin, cwd, output_path, prompt, skip_git_repo_check=False):
    command = [
        codex_bin,
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "-C",
        str(cwd),
        "--output-last-message",
        absolute(output_path),
    ]
    if skip_git_repo_check:
        command.append("--skip-git-repo-check")
    command.append(prompt)
    return command


def build_resume_command(codex_bin, session_id, output_path, prompt, skip_git_repo_check=False):
    command = [
        codex_bin,
        "exec",
        "resume",
        "--json",
        "--output-last-message",
        absolute(output_path),
    ]
    if skip_git_repo_check:
        command.append("--skip-git-repo-check")
    command.extend([session_id, prompt])
    return command


def find_session_id(value):
    if isinstance(value, dict):
        for key in ("session_id", "conversation_id", "thread_id"):
            found = value.get(key)
            if isinstance(found, str) and found:
                return found
        for child in value.values():
            found = find_session_id(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_session_id(child)
            if found:
                return found
    return ""


def parse_session_id(stdout):
    for line in stdout.splitlines():
        try:
            found = find_session_id(json.loads(line))
        except json.JSONDecodeError:
            found = ""
        if found:
            return found

    match = re.search(r"session[_ -]?id[\"':=\s]+([A-Za-z0-9._-]+)", stdout)
    if match:
        return match.group(1)
    return ""


def write_timeout_output(path, timeout_seconds):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(timeout_message(timeout_seconds) + "\n", encoding="utf-8")


def append_child_log(child_log_path, command, result=None, timeout_seconds=None):
    if not child_log_path:
        return
    child_log_path.parent.mkdir(parents=True, exist_ok=True)
    with child_log_path.open("a", encoding="utf-8") as log_file:
        command_for_log = list(command)
        if command_for_log:
            command_for_log[-1] = f"<prompt omitted: {len(command_for_log[-1])} chars>"
        log_file.write(json.dumps({"command": command_for_log}, sort_keys=True) + "\n")
        if result is not None:
            if result.stdout:
                log_file.write(result.stdout)
            if result.stderr:
                log_file.write(result.stderr)
        if timeout_seconds is not None:
            log_file.write(f"\n{timeout_message(timeout_seconds)}\n")


def run_child(command, cwd, child_log_path, child_timeout_seconds, timeout_output_path):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            capture_output=True,
            timeout=child_timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        write_timeout_output(timeout_output_path, child_timeout_seconds)
        append_child_log(child_log_path, command, timeout_seconds=child_timeout_seconds)
        raise ChildRunTimeout(
            "child run timed out after "
            f"{child_timeout_seconds:g} seconds"
        ) from error

    append_child_log(child_log_path, command, result=result)
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        raise subprocess.CalledProcessError(
            result.returncode,
            command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def prompt_for_turn(turn, record, inline_skill_path, turn_index):
    prompt = turn["prompt"]
    if (
        turn_index == 0
        and inline_skill_path
        and is_skill_configuration(record["configuration"])
    ):
        return inline_skill_prompt(prompt, inline_skill_path)
    return prompt


def execute_run(run, cwd, child_log_dir, child_timeout_seconds, inline_skill_path):
    record = run["record"]
    workspace = run["workspace"]
    child_log_path = child_log_path_for(child_log_dir, run) if child_log_dir else None
    turns = read_turns(workspace, record)
    session_id = ""
    transcript_turns = []

    for index, turn in enumerate(turns):
        output_path = turn_output_path_for(workspace, record, turn)
        prompt = prompt_for_turn(turn, record, inline_skill_path, index)
        if index == 0:
            command = build_initial_command(
                run["codex_bin"],
                cwd,
                output_path,
                prompt,
                skip_git_repo_check=run["skip_git_repo_check"],
            )
        else:
            if not session_id:
                raise MissingSessionId(
                    f"missing session id before {record['scenario_id']} "
                    f"{record['configuration']} {turn['turn_id']}"
                )
            command = build_resume_command(
                run["codex_bin"],
                session_id,
                output_path,
                prompt,
                skip_git_repo_check=run["skip_git_repo_check"],
            )

        result = run_child(
            command,
            cwd,
            child_log_path,
            child_timeout_seconds,
            output_path,
        )
        if index == 0:
            session_id = parse_session_id(result.stdout)
            if not session_id:
                raise MissingSessionId(
                    "could not extract session id from first turn stdout for "
                    f"{record['scenario_id']} {record['configuration']}"
                )

        assistant_output = output_path.read_text(encoding="utf-8")
        transcript_turns.append(
            {
                "turn_id": turn["turn_id"],
                "kind": turn["kind"],
                "prompt": prompt,
                "assistant_output": assistant_output,
                "output_path": str(output_path),
            }
        )

    final_output_path = final_output_path_for(workspace, record)
    final_output_path.write_text(transcript_turns[-1]["assistant_output"], encoding="utf-8")
    transcript_path_for(workspace, record).write_text(
        json.dumps(
            {
                "scenario_id": record["scenario_id"],
                "configuration": record["configuration"],
                "session_id": session_id,
                "turns": transcript_turns,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def compact_event(event):
    event = dict(event)
    if "initial_command" in event:
        command = list(event["initial_command"])
        prompt = command[-1]
        command[-1] = f"<prompt omitted: {len(prompt)} chars>"
        event["initial_command"] = command
        event["initial_prompt_chars"] = len(prompt)
    return event


def iter_runs(
    workspace,
    codex_bin,
    cwd,
    include_complete,
    suite,
    scenarios,
    configurations,
    skip_git_repo_check,
    limit,
    inline_skill_path=None,
):
    emitted = 0
    selected_scenarios = set(scenarios)
    selected_configurations = set(configurations)
    workspace = Path(workspace)
    for record in load_records(workspace):
        if suite and record["suite"] != suite:
            continue
        if selected_scenarios and record["scenario_id"] not in selected_scenarios:
            continue
        if selected_configurations and record["configuration"] not in selected_configurations:
            continue

        output_path = final_output_path_for(workspace, record)
        if not include_complete and output_is_complete(output_path):
            continue

        turns = read_turns(workspace, record)
        initial_prompt_text = prompt_for_turn(turns[0], record, inline_skill_path, 0)
        event = {
            "scenario_id": record["scenario_id"],
            "suite": record["suite"],
            "configuration": record["configuration"],
            "turn_count": len(turns),
            "requires_persisted_session": True,
            "turns_path": str((workspace / record["turns_path"]).absolute()),
            "output_path": str(output_path.absolute()),
            "transcript_path": str(transcript_path_for(workspace, record).absolute()),
            "initial_command": build_initial_command(
                codex_bin,
                cwd,
                turn_output_path_for(workspace, record, turns[0]),
                initial_prompt_text,
                skip_git_repo_check=skip_git_repo_check,
            ),
            "record": record,
            "workspace": workspace,
            "codex_bin": codex_bin,
            "skip_git_repo_check": skip_git_repo_check,
        }
        if inline_skill_path and is_skill_configuration(record["configuration"]):
            event["inline_skill_path"] = str(inline_skill_path)
        yield event
        emitted += 1
        if limit is not None and emitted >= limit:
            return


def printable_event(run, mode, child_log_dir):
    event = {
        key: value
        for key, value in run.items()
        if key not in {"record", "workspace", "codex_bin", "skip_git_repo_check"}
    }
    event["mode"] = mode
    if child_log_dir:
        event["child_log_path"] = str(child_log_path_for(child_log_dir, run))
    return event


def run_workspace(
    workspace,
    codex_bin,
    cwd,
    include_complete,
    execute,
    suite,
    scenarios,
    configurations,
    skip_git_repo_check,
    limit,
    child_log_dir=None,
    child_timeout_seconds=None,
    inline_skill_path=None,
    compact_events=False,
    jobs=2,
):
    mode = "execute" if execute else "dry-run"
    runs = list(
        iter_runs(
            workspace,
            codex_bin,
            cwd,
            include_complete,
            suite,
            scenarios,
            configurations,
            skip_git_repo_check,
            limit,
            inline_skill_path=inline_skill_path,
        )
    )

    for run in runs:
        event = printable_event(run, mode, child_log_dir)
        printed_event = compact_event(event) if compact_events else event
        print(json.dumps(printed_event, sort_keys=True))

    if not execute:
        return

    try:
        if jobs == 1 or len(runs) <= 1:
            for run in runs:
                execute_run(
                    run,
                    cwd,
                    child_log_dir,
                    child_timeout_seconds,
                    inline_skill_path,
                )
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
                futures = [
                    executor.submit(
                        execute_run,
                        run,
                        cwd,
                        child_log_dir,
                        child_timeout_seconds,
                        inline_skill_path,
                    )
                    for run in runs
                ]
                for future in concurrent.futures.as_completed(futures):
                    future.result()
    except ChildRunTimeout as error:
        print(error, file=sys.stderr)
        raise SystemExit(124)
    except MissingSessionId as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--cwd", default=Path.cwd())
    parser.add_argument("--include-complete", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--skip-git-repo-check",
        action="store_true",
        help="Pass through to codex exec when using a neutral cwd outside a Git repo.",
    )
    parser.add_argument(
        "--suite",
        choices=sorted(set(SUITE_NAMES.values())),
    )
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument(
        "--configuration",
        action="append",
        choices=(
            "baseline-positive",
            "baseline-negative",
            "skill-positive",
            "skill-negative",
        ),
        default=[],
        help="Run only the selected prompt configuration. May be repeated.",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--child-log-dir",
        help="Capture child codex stdout/stderr into per-run log files.",
    )
    parser.add_argument(
        "--child-timeout-seconds",
        type=float,
        help="Stop the batch if a single child codex turn exceeds this many seconds.",
    )
    parser.add_argument(
        "--inline-skill",
        help=(
            "Inline this SKILL.md into the first skill-* turn only, so later "
            "pressure turns measure session retention instead of reinjection."
        ),
    )
    parser.add_argument(
        "--compact-events",
        action="store_true",
        help="Omit full prompts from emitted JSONL events while keeping execution unchanged.",
    )
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=2,
        help="Maximum multi-turn runs to execute in parallel (default: 2).",
    )
    args = parser.parse_args()

    run_workspace(
        workspace=args.workspace,
        codex_bin=args.codex_bin,
        cwd=Path(args.cwd),
        include_complete=args.include_complete,
        execute=args.execute,
        suite=args.suite,
        scenarios=args.scenario,
        configurations=args.configuration,
        skip_git_repo_check=args.skip_git_repo_check,
        limit=args.limit,
        child_log_dir=args.child_log_dir,
        child_timeout_seconds=args.child_timeout_seconds,
        inline_skill_path=args.inline_skill,
        compact_events=args.compact_events,
        jobs=args.jobs,
    )


if __name__ == "__main__":
    main()
