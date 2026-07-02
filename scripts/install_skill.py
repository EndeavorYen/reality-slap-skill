#!/usr/bin/env python3
"""Install, inspect, or uninstall the Reality Slap Codex skill."""

import argparse
import os
import shutil
import sys
from pathlib import Path


SKILL_NAME = "reality-slap"
RUNTIME_PATHS = ("SKILL.md", "agents", "LICENSE")
EVAL_TOOL_PATHS = ("README.md", "evals", "scripts", "tests")


def default_codex_home():
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def skill_destination(codex_home, name):
    return Path(codex_home).expanduser() / "skills" / name


def command_prompt_destination(codex_home, name):
    return Path(codex_home).expanduser() / "prompts" / f"{name}.md"


def require_source(source):
    source = Path(source).expanduser().resolve()
    if not (source / "SKILL.md").exists():
        raise SystemExit(f"source does not look like a skill repo: {source}")
    return source


def describe_destination(destination):
    if not destination.exists() and not destination.is_symlink():
        return "not-installed"
    if destination.is_symlink():
        return f"symlink -> {destination.resolve()}"
    if destination.is_dir():
        return "directory"
    return "file"


def remove_destination(destination, force):
    if not destination.exists() and not destination.is_symlink():
        return
    if destination.is_symlink() or destination.is_file():
        destination.unlink()
        return
    if destination.is_dir():
        if not force:
            raise SystemExit(
                f"{destination} already exists as a directory; pass --force to replace it"
            )
        shutil.rmtree(destination)
        return
    raise SystemExit(f"cannot replace unsupported destination: {destination}")


def write_command_prompt(destination, name, force):
    if destination.exists() or destination.is_symlink():
        if not force:
            raise SystemExit(
                f"{destination} already exists; pass --force to replace it"
            )
        remove_destination(destination, force=True)

    destination.parent.mkdir(parents=True, exist_ok=True)
    prompt_text = f"""---
description: Force Reality Slap for decision pressure-testing
argument-hint: [decision-or-context]
---

Use ${name} to pressure-test this decision or recommendation. Hold the best-supported stance, name the trade-offs, and say what evidence would change the recommendation.

$ARGUMENTS
"""
    destination.write_text(prompt_text)


def copy_path(source, destination):
    if source.is_dir():
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(
                ".git",
                ".pytest_cache",
                "__pycache__",
                ".DS_Store",
                "*.pyc",
            ),
        )
    elif source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def install_link(source, destination, force):
    remove_destination(destination, force)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source, target_is_directory=True)
    return f"installed {SKILL_NAME}: {destination} -> {source}"


def install_copy(source, destination, force, include_eval_tools):
    remove_destination(destination, force)
    destination.mkdir(parents=True, exist_ok=True)
    paths = list(RUNTIME_PATHS)
    if include_eval_tools:
        paths.extend(EVAL_TOOL_PATHS)
    for relative in paths:
        copy_path(source / relative, destination / relative)
    return f"installed {SKILL_NAME}: {destination} ({describe_destination(destination)})"


def install(args):
    source = require_source(args.source)
    destination = skill_destination(args.codex_home, args.name)
    if args.method == "link":
        message = install_link(source, destination, args.force)
    else:
        message = install_copy(source, destination, args.force, args.include_eval_tools)
    print(message)


def install_command(args):
    destination = command_prompt_destination(args.codex_home, args.name)
    write_command_prompt(destination, args.name, args.force)
    print(f"installed {args.name} command: {destination}")


def status(args):
    destination = skill_destination(args.codex_home, args.name)
    print(f"{args.name}: {describe_destination(destination)}")
    if destination.exists() or destination.is_symlink():
        skill_file = destination / "SKILL.md"
        print(f"skill_file: {skill_file}")
    command_prompt = command_prompt_destination(args.codex_home, args.name)
    print(f"command_prompt: {describe_destination(command_prompt)}")
    if command_prompt.exists() or command_prompt.is_symlink():
        print(f"command_prompt_file: {command_prompt}")


def uninstall(args):
    destination = skill_destination(args.codex_home, args.name)
    remove_destination(destination, args.force)
    print(f"uninstalled {args.name}: {destination}")


def uninstall_command(args):
    destination = command_prompt_destination(args.codex_home, args.name)
    remove_destination(destination, args.force)
    print(f"uninstalled {args.name} command: {destination}")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.set_defaults(func=None)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--codex-home", type=Path, default=default_codex_home())
    common.add_argument("--name", default=SKILL_NAME)

    subparsers = parser.add_subparsers(dest="command")

    install_parser = subparsers.add_parser("install", parents=[common])
    install_parser.add_argument("--source", type=Path, default=Path.cwd())
    install_parser.add_argument("--method", choices=("link", "copy"), default="copy")
    install_parser.add_argument("--force", action="store_true")
    install_parser.add_argument(
        "--include-eval-tools",
        action="store_true",
        help="Copy README, eval bank, scripts, and tests into the installed skill.",
    )
    install_parser.set_defaults(func=install)

    install_command_parser = subparsers.add_parser("install-command", parents=[common])
    install_command_parser.add_argument("--force", action="store_true")
    install_command_parser.set_defaults(func=install_command)

    status_parser = subparsers.add_parser("status", parents=[common])
    status_parser.set_defaults(func=status)

    uninstall_parser = subparsers.add_parser("uninstall", parents=[common])
    uninstall_parser.add_argument("--force", action="store_true")
    uninstall_parser.set_defaults(func=uninstall)

    uninstall_command_parser = subparsers.add_parser(
        "uninstall-command", parents=[common]
    )
    uninstall_command_parser.add_argument("--force", action="store_true")
    uninstall_command_parser.set_defaults(func=uninstall_command)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.func is None:
        parser.print_help()
        return 2
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
