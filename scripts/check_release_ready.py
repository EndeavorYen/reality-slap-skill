#!/usr/bin/env python3
"""Run the release-readiness gate for the Reality Slap skill."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUICK_VALIDATE = (
    Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"
)
RUNTIME_TOP_LEVEL = {"SKILL.md", "agents", "LICENSE"}
RUNTIME_REQUIRED_FILES = ("SKILL.md", "agents/openai.yaml", "LICENSE")
COMMAND_PROMPT_REQUIRED_SNIPPETS = (
    "description:",
    "argument-hint:",
    "Use $reality-slap",
    "$ARGUMENTS",
)


def command_record(name, command):
    return {"name": name, "command": [str(part) for part in command]}


def release_commands(
    root,
    codex_home,
    quick_validate,
    skip_tests=False,
    eval_workspace=None,
):
    python = sys.executable
    commands = [
        command_record(
            "official-skill-validator",
            [python, quick_validate, root],
        ),
        command_record(
            "stance-drift-eval-bank",
            [
                python,
                root / "scripts" / "validate_eval_bank.py",
                "--input",
                root / "evals" / "reality-slap-eval-bank.md",
                "--profile",
                "stance-drift",
            ],
        ),
        command_record(
            "stance-drift-eval-design",
            [
                python,
                root / "scripts" / "audit_eval_design.py",
                "--bank",
                root / "evals" / "reality-slap-eval-bank.md",
                "--profile",
                "stance-drift",
            ],
        ),
        command_record(
            "copy-install",
            [
                python,
                root / "scripts" / "install_skill.py",
                "install",
                "--method",
                "copy",
                "--codex-home",
                codex_home,
                "--force",
            ],
        ),
        command_record(
            "installed-status",
            [
                python,
                root / "scripts" / "install_skill.py",
                "status",
                "--codex-home",
                codex_home,
            ],
        ),
        command_record(
            "installed-skill-validator",
            [
                python,
                quick_validate,
                Path(codex_home) / "skills" / "reality-slap",
            ],
        ),
        command_record(
            "command-install",
            [
                python,
                root / "scripts" / "install_skill.py",
                "install-command",
                "--codex-home",
                codex_home,
                "--force",
            ],
        ),
        command_record(
            "command-uninstall",
            [
                python,
                root / "scripts" / "install_skill.py",
                "uninstall-command",
                "--codex-home",
                codex_home,
                "--force",
            ],
        ),
        command_record(
            "copy-uninstall",
            [
                python,
                root / "scripts" / "install_skill.py",
                "uninstall",
                "--codex-home",
                codex_home,
                "--force",
            ],
        ),
    ]
    if eval_workspace:
        commands.append(
            command_record(
                "eval-goal-completion",
                [
                    python,
                    root / "scripts" / "audit_goal_completion.py",
                    "--workspace",
                    eval_workspace,
                    "--skill",
                    root / "SKILL.md",
                    "--profile",
                    "stance-drift",
                ],
            )
        )
        commands.append(
            command_record(
                "hard-evidence-gate",
                [
                    python,
                    root / "scripts" / "check_hard_evidence_gate.py",
                    "--scorecard",
                    Path(eval_workspace) / "scorecard.json",
                    "--metadata",
                    root / "evals" / "evals.json",
                ],
            )
        )
    if not skip_tests:
        commands.insert(
            1,
            command_record(
                "unit-tests",
                [python, "-m", "unittest", "discover", "-s", "tests"],
            ),
        )
    return commands


def run_command(record, cwd):
    result = subprocess.run(
        record["command"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "name": record["name"],
        "command": record["command"],
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "ok": result.returncode == 0,
    }


def inspect_runtime_layout(codex_home):
    destination = Path(codex_home) / "skills" / "reality-slap"
    missing = [
        relative
        for relative in RUNTIME_REQUIRED_FILES
        if not (destination / relative).exists()
    ]
    unexpected_top_level = []
    if destination.exists():
        unexpected_top_level = sorted(
            child.name
            for child in destination.iterdir()
            if child.name not in RUNTIME_TOP_LEVEL
        )
    else:
        missing = list(RUNTIME_REQUIRED_FILES)

    return {
        "name": "installed-runtime-layout",
        "command": ["inspect", str(destination)],
        "returncode": 0 if not missing and not unexpected_top_level else 1,
        "stdout": json.dumps(
            {
                "required_files": list(RUNTIME_REQUIRED_FILES),
                "missing": missing,
                "unexpected_top_level": unexpected_top_level,
            },
            sort_keys=True,
        )
        + "\n",
        "stderr": "",
        "ok": not missing and not unexpected_top_level,
    }


def inspect_command_prompt(codex_home):
    prompt_file = Path(codex_home) / "prompts" / "reality-slap.md"
    if prompt_file.exists():
        prompt_text = prompt_file.read_text()
        missing = [
            snippet
            for snippet in COMMAND_PROMPT_REQUIRED_SNIPPETS
            if snippet not in prompt_text
        ]
    else:
        missing = ["prompts/reality-slap.md"]

    return {
        "name": "installed-command-prompt",
        "command": ["inspect", str(prompt_file)],
        "returncode": 0 if not missing else 1,
        "stdout": json.dumps(
            {
                "required_snippets": list(COMMAND_PROMPT_REQUIRED_SNIPPETS),
                "missing": missing,
            },
            sort_keys=True,
        )
        + "\n",
        "stderr": "",
        "ok": not missing,
    }


def run_release_gate(args):
    root = Path(args.root).expanduser().resolve()
    quick_validate = Path(args.quick_validate).expanduser().resolve()
    if not quick_validate.exists():
        raise SystemExit(f"quick_validate.py not found: {quick_validate}")

    if args.codex_home:
        codex_home = Path(args.codex_home).expanduser().resolve()
        temp_context = None
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="reality-slap-release-")
        codex_home = Path(temp_context.name) / "codex-home"

    try:
        commands = release_commands(
            root=root,
            codex_home=codex_home,
            quick_validate=quick_validate,
            skip_tests=args.skip_tests,
            eval_workspace=args.eval_workspace,
        )
        if args.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "mode": "score-release" if args.eval_workspace else "install-release",
                "eval_workspace": str(args.eval_workspace) if args.eval_workspace else "",
                "commands": commands,
            }

        results = []
        for record in commands:
            results.append(run_command(record, root))
            if record["name"] == "installed-status":
                results.append(inspect_runtime_layout(codex_home))
            if record["name"] == "command-install":
                results.append(inspect_command_prompt(codex_home))
        failed = [result for result in results if not result["ok"]]
        return {
            "ok": not failed,
            "dry_run": False,
            "mode": "score-release" if args.eval_workspace else "install-release",
            "eval_workspace": str(args.eval_workspace) if args.eval_workspace else "",
            "codex_home": str(codex_home),
            "results": results,
        }
    finally:
        if temp_context is not None:
            temp_context.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--quick-validate", type=Path, default=DEFAULT_QUICK_VALIDATE)
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument(
        "--eval-workspace",
        "--full-eval-workspace",
        dest="eval_workspace",
        type=Path,
        help=(
            "Also require a completed scored eval workspace to pass "
            "audit_goal_completion.py. Omit this for install-only releases."
        ),
    )
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_release_gate(args)
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
