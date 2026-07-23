#!/usr/bin/env python3
"""Load and validate the frozen open-decision experiment case bank."""

import hashlib
import json
from collections import Counter
from pathlib import Path


SEED = 20260724
DOMAINS = (
    "platform-architecture",
    "product-launch",
    "operations-incidents",
    "data-privacy-security",
    "vendor-business-strategy",
    "organization-process",
)
SUBSETS = ("primary", "reserve")
REQUIRED_PUBLIC = (
    "decision_owner",
    "objective",
    "facts",
    "decision_request",
    "plausible_paths",
    "material_constraints",
    "harmful_failure_paths",
    "incomplete_information",
    "reversible_action",
)
REQUIRED_CARD = (
    "must_cover_constraints",
    "acceptable_decision_families",
    "fatal_errors",
    "known_valid_insights",
    "decision_closure_requirements",
    "reasoning_notes",
)
MIN_LIST_ITEMS = {
    "facts": 4,
    "plausible_paths": 3,
    "material_constraints": 4,
    "harmful_failure_paths": 2,
    "incomplete_information": 1,
    "must_cover_constraints": 4,
    "acceptable_decision_families": 2,
    "fatal_errors": 2,
    "known_valid_insights": 1,
    "decision_closure_requirements": 5,
}


def load_case_bank(path):
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid case bank: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError("case bank must be an object")
    return payload


def require_keys(value, required, path):
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object")
    missing = [key for key in required if key not in value]
    if missing:
        raise ValueError(f"{path} missing required field: {missing[0]}")


def require_text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be non-empty text")


def require_text_list(value, path, minimum):
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{path} requires at least {minimum} items")
    for index, item in enumerate(value):
        require_text(item, f"{path}[{index}]")


def canonical_sha256(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_case(case):
    require_keys(case, ("case_id", "title", "domain", "subset", "public", "adjudication"), "case")
    require_text(case["case_id"], "case_id")
    require_text(case["title"], f"{case['case_id']}.title")
    if case["domain"] not in DOMAINS:
        raise ValueError(f"{case['case_id']}.domain is invalid")
    if case["subset"] not in SUBSETS:
        raise ValueError(f"{case['case_id']}.subset is invalid")

    public = case["public"]
    card = case["adjudication"]
    require_keys(public, REQUIRED_PUBLIC, f"{case['case_id']}.public")
    require_keys(card, REQUIRED_CARD, f"{case['case_id']}.adjudication")

    for field in ("decision_owner", "objective", "decision_request", "reversible_action"):
        require_text(public[field], f"{case['case_id']}.public.{field}")
    require_text(card["reasoning_notes"], f"{case['case_id']}.adjudication.reasoning_notes")
    for field, minimum in MIN_LIST_ITEMS.items():
        container = public if field in public else card
        require_text_list(container[field], f"{case['case_id']}.{field}", minimum)

    public_text = json.dumps(public, ensure_ascii=False).casefold()
    for hidden in card["fatal_errors"]:
        if hidden.casefold() in public_text:
            raise ValueError(f"{case['case_id']} public prompt leaks adjudication")


def validate_case_bank(payload, seed=SEED):
    if payload.get("experiment_id") != "open-decision-debate-20260724":
        raise ValueError("unexpected experiment_id")
    if payload.get("seed") != seed:
        raise ValueError(f"case bank seed must be {seed}")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 24:
        raise ValueError("case bank must contain 24 cases")
    for case in cases:
        validate_case(case)

    ids = [case["case_id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate case_id")
    expected_ids = [f"OD-{number:02d}" for number in range(1, 25)]
    if sorted(ids) != expected_ids:
        raise ValueError("case IDs must be OD-01 through OD-24")

    primary_ids = sorted(case["case_id"] for case in cases if case["subset"] == "primary")
    reserve_ids = sorted(case["case_id"] for case in cases if case["subset"] == "reserve")
    if primary_ids != expected_ids[:12]:
        raise ValueError("primary IDs must be OD-01 through OD-12")
    if reserve_ids != expected_ids[12:]:
        raise ValueError("reserve IDs must be OD-13 through OD-24")

    counts = Counter((case["domain"], case["subset"]) for case in cases)
    domain_split_counts = {}
    for domain in DOMAINS:
        observed = tuple((subset, counts[(domain, subset)]) for subset in SUBSETS)
        if observed != (("primary", 2), ("reserve", 2)):
            raise ValueError(f"domain split must contain two primary and two reserve: {domain}")
        domain_split_counts[domain] = observed

    return {
        "experiment_id": payload["experiment_id"],
        "seed": seed,
        "case_count": len(cases),
        "primary_ids": primary_ids,
        "reserve_ids": reserve_ids,
        "domain_split_counts": domain_split_counts,
        "bank_sha256": canonical_sha256(payload),
    }


def select_cases(payload, subset):
    if subset not in SUBSETS:
        raise ValueError(f"unknown subset: {subset}")
    validate_case_bank(payload)
    return sorted(
        (case for case in payload["cases"] if case["subset"] == subset),
        key=lambda case: case["case_id"],
    )
