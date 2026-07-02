#!/usr/bin/env python3
"""Convert blinded score updates into normal Reality Slap score updates."""

import argparse
import json
import sys
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_updates(path):
    updates = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            update = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"line {line_number}: invalid JSON: {error}") from error
        update["_line_number"] = line_number
        updates.append(update)
    return updates


def mapping_by_blind_id(mapping):
    return {
        entry.get("blind_id"): entry.get("score_update_target")
        for entry in mapping.get("entries", [])
        if entry.get("blind_id")
    }


def convert_update(update, targets):
    line = update.get("_line_number", "?")
    blind_id = update.get("blind_id")
    if not blind_id:
        raise ValueError(f"line {line}: blind_id is required")
    if blind_id not in targets:
        raise ValueError(f"line {line}: unknown blind_id {blind_id}")
    if not isinstance(update.get("score"), dict):
        raise ValueError(f"line {line}: score must be an object")

    converted = dict(targets[blind_id])
    converted["score"] = update["score"]
    return converted


def convert_updates(mapping, updates):
    targets = mapping_by_blind_id(mapping)
    return [convert_update(update, targets) for update in updates]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--updates", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        converted = convert_updates(load_json(args.mapping), load_updates(args.updates))
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)

    output = "".join(json.dumps(update, sort_keys=True) + "\n" for update in converted)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
