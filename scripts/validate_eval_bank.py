#!/usr/bin/env python3
"""Validate the Reality Slap eval bank structure and portability."""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from expand_eval_bank import parse_bank


EXPECTED_PROFILES = {
    "pilot": {"FI": 10, "PR": 8, "EB": 7},
    "full": {"FI": 40, "PR": 30, "EB": 30},
}
DEFAULT_PROFILE = "pilot"
EXPECTED_COUNTS = EXPECTED_PROFILES[DEFAULT_PROFILE]
EXPECTED_TOTAL = sum(EXPECTED_COUNTS.values())
FORBIDDEN_TERMS = [
    "/Users/",
    "/private/",
    "Rexiano",
    "Hermes",
    "Stock-AI-Committee",
    "tw-sector-alpha-radar",
    "EndeavorYen",
]


def expected_total(expected_counts):
    return sum(expected_counts.values())


def validate_counts(scenarios, errors, expected_counts):
    total = expected_total(expected_counts)
    if len(scenarios) != total:
        errors.append(f"expected {total} scenarios, found {len(scenarios)}")

    counts = Counter(scenario.scenario_id.split("-", 1)[0] for scenario in scenarios)
    for prefix, expected in expected_counts.items():
        actual = counts.get(prefix, 0)
        if actual != expected:
            errors.append(f"expected {expected} {prefix} scenarios, found {actual}")


def validate_ids(scenarios, errors, expected_counts):
    ids = [scenario.scenario_id for scenario in scenarios]
    for scenario_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate scenario id {scenario_id}")

    grouped = {prefix: [] for prefix in expected_counts}
    for scenario_id in ids:
        match = re.fullmatch(r"(FI|PR|EB)-(\d{2})", scenario_id)
        if not match:
            errors.append(f"invalid scenario id format {scenario_id}")
            continue
        if match.group(1) not in grouped:
            errors.append(f"unexpected scenario prefix {match.group(1)}")
            continue
        grouped[match.group(1)].append(int(match.group(2)))

    for prefix, expected_count in expected_counts.items():
        expected = list(range(1, expected_count + 1))
        actual = sorted(grouped[prefix])
        if actual and actual != expected:
            errors.append(f"{prefix} ids should be sequential 01..{expected_count:02d}")


def validate_fields(scenarios, errors):
    for scenario in scenarios:
        fields = {
            "domain": scenario.domain,
            "facts": scenario.facts,
            "positive": scenario.positive,
            "negative": scenario.negative,
            "expected": scenario.expected,
        }
        for name, value in fields.items():
            if not value:
                errors.append(f"{scenario.scenario_id}.{name}: field is empty")


def validate_portability(path, errors):
    text = Path(path).read_text(encoding="utf-8")
    for term in FORBIDDEN_TERMS:
        if term in text:
            errors.append(f"forbidden project-specific term {term!r}")


def validate_eval_bank(path, profile=DEFAULT_PROFILE):
    errors = []
    expected_counts = EXPECTED_PROFILES[profile]
    scenarios = parse_bank(path)
    validate_counts(scenarios, errors, expected_counts)
    validate_ids(scenarios, errors, expected_counts)
    validate_fields(scenarios, errors)
    validate_portability(path, errors)
    return scenarios, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="evals/reality-slap-eval-bank.md")
    parser.add_argument(
        "--profile",
        choices=sorted(EXPECTED_PROFILES),
        default=DEFAULT_PROFILE,
        help="Expected bank size profile. Use pilot now and full for the 100-scenario target.",
    )
    args = parser.parse_args()

    scenarios, errors = validate_eval_bank(args.input, args.profile)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)

    print(f"Eval bank is valid: {len(scenarios)} scenarios (profile {args.profile})")


if __name__ == "__main__":
    main()
