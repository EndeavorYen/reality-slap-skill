#!/usr/bin/env python3
"""Dry-run or execute Codex runs for a Reality Slap A/B workspace."""

import argparse
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


def iter_runs(
    workspace,
    codex_bin,
    cwd,
    include_complete,
    suite,
    scenarios,
    skip_git_repo_check,
    limit,
    inline_skill_path=None,
):
    emitted = 0
    selected_scenarios = set(scenarios)
    for record in load_records(workspace):
        if suite and record["suite"] != suite:
            continue
        if selected_scenarios and record["scenario_id"] not in selected_scenarios:
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
    skip_git_repo_check,
    limit,
    child_log_dir=None,
    child_timeout_seconds=None,
    inline_skill_path=None,
    compact_events=False,
):
    mode = "execute" if execute else "dry-run"
    for run in iter_runs(
        workspace,
        codex_bin,
        cwd,
        include_complete,
        suite,
        scenarios,
        skip_git_repo_check,
        limit,
        inline_skill_path=inline_skill_path,
    ):
        event = dict(run)
        event["mode"] = mode
        child_log_path = None
        if child_log_dir:
            child_log_path = (
                Path(child_log_dir)
                / run["scenario_id"]
                / f"{run['configuration']}.log"
            )
            event["child_log_path"] = str(child_log_path)
        printed_event = compact_event(event) if compact_events else event
        print(json.dumps(printed_event, sort_keys=True))
        if execute:
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
                    except subprocess.TimeoutExpired:
                        write_timeout_output(run, child_timeout_seconds)
                        log_file.write(f"\n{timeout_message(child_timeout_seconds)}\n")
                        print(
                            "child run timed out after "
                            f"{child_timeout_seconds:g} seconds: "
                            f"{run['scenario_id']} {run['configuration']}",
                            file=sys.stderr,
                        )
                        raise SystemExit(124)
            else:
                try:
                    subprocess.run(
                        run["command"],
                        cwd=cwd,
                        check=True,
                        timeout=child_timeout_seconds,
                    )
                except subprocess.TimeoutExpired:
                    write_timeout_output(run, child_timeout_seconds)
                    print(
                        "child run timed out after "
                        f"{child_timeout_seconds:g} seconds: "
                        f"{run['scenario_id']} {run['configuration']}",
                        file=sys.stderr,
                    )
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
        choices=sorted(SUITE_NAMES.values()),
    )
    parser.add_argument("--scenario", action="append", default=[])
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
    args = parser.parse_args()

    run_workspace(
        workspace=args.workspace,
        codex_bin=args.codex_bin,
        cwd=Path(args.cwd),
        include_complete=args.include_complete,
        execute=args.execute,
        suite=args.suite,
        scenarios=args.scenario,
        skip_git_repo_check=args.skip_git_repo_check,
        limit=args.limit,
        child_log_dir=args.child_log_dir,
        child_timeout_seconds=args.child_timeout_seconds,
        inline_skill_path=args.inline_skill,
        compact_events=args.compact_events,
    )


if __name__ == "__main__":
    main()
