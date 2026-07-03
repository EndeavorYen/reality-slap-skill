#!/usr/bin/env python3
"""Dry-run or execute Codex runs for a Reality Slap A/B workspace."""

import argparse
import concurrent.futures
import json
import subprocess
import sys
from pathlib import Path

from expand_eval_bank import SUITE_NAMES


INVALID_OUTPUT_MARKERS = (
    "ERROR: child process timed out after",
    "ERROR: You've hit your usage limit",
)


def load_records(workspace):
    records_path = Path(workspace) / "records.jsonl"
    return [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def output_path_for(workspace, record):
    return Path(workspace) / record["scenario_id"] / record["configuration"] / "output.txt"


def prompt_path_for(workspace, record):
    return Path(workspace) / record["scenario_id"] / record["configuration"] / "prompt.txt"


def output_is_complete(path):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return False
    return not output_invalid_reason(text)


def output_invalid_reason(text):
    stripped = text.strip()
    for marker in INVALID_OUTPUT_MARKERS:
        if stripped.startswith(marker):
            return marker
    return ""


def timeout_message(timeout_seconds):
    return f"ERROR: child process timed out after {timeout_seconds:g} seconds"


def write_timeout_output(run, timeout_seconds):
    output_path = Path(run["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(timeout_message(timeout_seconds) + "\n", encoding="utf-8")


class ChildRunTimeout(RuntimeError):
    pass


def build_command(codex_bin, cwd, output_path, prompt, skip_git_repo_check=False):
    output_path = Path(output_path).absolute()
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


def is_skill_configuration(configuration):
    return configuration.startswith("skill-")


def inline_skill_prompt(prompt, inline_skill_path):
    skill_text = Path(inline_skill_path).read_text(encoding="utf-8").strip()
    return (
        "Use the following Reality Slap skill instructions for this eval response.\n"
        "Apply them silently: do not mention that instructions were injected, and "
        "answer the original prompt directly.\n\n"
        "```markdown\n"
        f"{skill_text}\n"
        "```\n\n"
        "Original eval prompt:\n\n"
        f"{prompt}"
    )


def compact_event(event):
    event = dict(event)
    command = list(event["command"])
    prompt = command[-1]
    command[-1] = f"<prompt omitted: {len(prompt)} chars>"
    event["command"] = command
    event["prompt_chars"] = len(prompt)
    return event


def positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("--jobs must be at least 1")
    return parsed


def child_log_path_for(child_log_dir, run):
    return Path(child_log_dir) / run["scenario_id"] / f"{run['configuration']}.log"


def event_for_run(run, mode, child_log_dir):
    event = dict(run)
    event["mode"] = mode
    if child_log_dir:
        event["child_log_path"] = str(child_log_path_for(child_log_dir, run))
    return event


def execute_run(run, cwd, child_log_dir, child_timeout_seconds):
    child_log_path = child_log_path_for(child_log_dir, run) if child_log_dir else None
    if child_log_path:
        child_log_path.parent.mkdir(parents=True, exist_ok=True)
        with child_log_path.open("w", encoding="utf-8") as log_file:
            try:
                subprocess.run(
                    run["command"],
                    cwd=cwd,
                    check=True,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=child_timeout_seconds,
                )
            except subprocess.TimeoutExpired as error:
                write_timeout_output(run, child_timeout_seconds)
                log_file.write(f"\n{timeout_message(child_timeout_seconds)}\n")
                raise ChildRunTimeout(
                    "child run timed out after "
                    f"{child_timeout_seconds:g} seconds: "
                    f"{run['scenario_id']} {run['configuration']}"
                ) from error
    else:
        try:
            subprocess.run(
                run["command"],
                cwd=cwd,
                check=True,
                timeout=child_timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            write_timeout_output(run, child_timeout_seconds)
            raise ChildRunTimeout(
                "child run timed out after "
                f"{child_timeout_seconds:g} seconds: "
                f"{run['scenario_id']} {run['configuration']}"
            ) from error


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
    for record in load_records(workspace):
        if suite and record["suite"] != suite:
            continue
        if selected_scenarios and record["scenario_id"] not in selected_scenarios:
            continue
        if selected_configurations and record["configuration"] not in selected_configurations:
            continue

        output_path = output_path_for(workspace, record)
        if not include_complete and output_is_complete(output_path):
            continue

        prompt_path = prompt_path_for(workspace, record)
        prompt = prompt_path.read_text(encoding="utf-8")
        skill_inlined = inline_skill_path and is_skill_configuration(record["configuration"])
        if skill_inlined:
            prompt = inline_skill_prompt(prompt, inline_skill_path)
        event = {
            "scenario_id": record["scenario_id"],
            "suite": record["suite"],
            "configuration": record["configuration"],
            "prompt_path": str(prompt_path),
            "output_path": str(output_path),
            "command": build_command(
                codex_bin,
                cwd,
                output_path,
                prompt,
                skip_git_repo_check=skip_git_repo_check,
            ),
        }
        if skill_inlined:
            event["inline_skill_path"] = str(inline_skill_path)
        yield {
            **event,
        }
        emitted += 1
        if limit is not None and emitted >= limit:
            return


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
    runs = list(iter_runs(
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
    ))

    for run in runs:
        event = event_for_run(run, mode, child_log_dir)
        printed_event = compact_event(event) if compact_events else event
        print(json.dumps(printed_event, sort_keys=True))

    if not execute:
        return

    try:
        if jobs == 1 or len(runs) <= 1:
            for run in runs:
                execute_run(run, cwd, child_log_dir, child_timeout_seconds)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
                futures = [
                    executor.submit(
                        execute_run,
                        run,
                        cwd,
                        child_log_dir,
                        child_timeout_seconds,
                    )
                    for run in runs
                ]
                for future in concurrent.futures.as_completed(futures):
                    future.result()
    except ChildRunTimeout as error:
        print(error, file=sys.stderr)
        raise SystemExit(124)


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
        help="Stop the batch if a single child codex run exceeds this many seconds.",
    )
    parser.add_argument(
        "--inline-skill",
        help=(
            "Inline this SKILL.md into skill-* prompts so live evals measure the "
            "same skill guidance deterministically. Baseline prompts are unchanged."
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
        help="Maximum child codex runs to execute in parallel (default: 2).",
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
