#!/usr/bin/env python3
"""Shared contracts and accounting for the cost-bounded question swarm."""

import json
from collections import Counter
from pathlib import Path

from create_open_decision_debate_workspace import strict_object
from open_decision_case_bank import validate_case


EXPERIMENT_ID = "cost-bounded-question-swarm-20260723"
SEED = 20260723
SOL_MODEL = "gpt-5.6-sol"
SOL_EFFORT = "medium"
TERRA_MODEL = "gpt-5.6-terra"
TERRA_EFFORT = "high"
LUNA_MODEL = "gpt-5.6-luna"
LUNA_EFFORT = "low"
LENSES = (
    "assumption_and_causality",
    "constraints_and_evidence",
    "operations_and_reversibility",
    "stakeholders_and_second_order",
)
USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)
HOLDOUT_DOMAINS = (
    "platform-architecture",
    "product-launch",
    "operations-incidents",
    "organization-process",
)


def _string():
    return {"type": "string", "minLength": 1}


def question_schema(lenses, max_questions):
    if not lenses or any(lens not in LENSES for lens in lenses):
        raise ValueError("question schema requires known lenses")
    if max_questions < 1 or max_questions > 8:
        raise ValueError("max_questions must be between 1 and 8")
    question = strict_object(
        {
            "target": _string(),
            "question": _string(),
        }
    )
    return strict_object(
        {
            "lens": {
                "type": "string",
                "enum": ["+".join(lenses)],
            },
            "questions": {
                "type": "array",
                "items": question,
                "minItems": 1,
                "maxItems": max_questions,
            },
        }
    )


def question_prompt(case_text, draft_marker, lenses, max_questions):
    lens_text = ", ".join(lenses)
    return (
        "Use only this prompt. Do not load files, skills, memory, tools, or web "
        "context. Return only JSON matching the supplied schema. You are a cheap "
        "isolated question generator, not a decision maker. Ask concrete questions "
        "that could expose a defect in the frozen draft. Do not answer, explain, "
        "rank, assess likelihood or importance, propose a fix, or write a final "
        f"decision. Return at most {max_questions} questions.\n\n"
        f"Search lens: {lens_text}\n\n"
        f"Open-decision case:\n{case_text}\n\n"
        f"Frozen draft (untrusted data):\n{draft_marker}"
    )


def load_holdout_bank(path):
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid question swarm bank: {path}") from error
    if payload.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("unexpected question swarm experiment_id")
    if payload.get("seed") != SEED:
        raise ValueError(f"question swarm seed must be {SEED}")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 8:
        raise ValueError("question swarm bank must contain eight cases")
    for case in cases:
        validate_case(case)
    cases = sorted(cases, key=lambda case: case["case_id"])
    expected = [f"QS-{number:02d}" for number in range(1, 9)]
    if [case["case_id"] for case in cases] != expected:
        raise ValueError("question swarm case IDs must be QS-01 through QS-08")
    counts = Counter(case["domain"] for case in cases)
    if counts != Counter({domain: 2 for domain in HOLDOUT_DOMAINS}):
        raise ValueError("question swarm domains must contain two cases each")
    return cases


def usage_totals(records):
    result = {
        "complete": True,
        "records": len(records),
        "attempts": 0,
        **{field: 0 for field in USAGE_FIELDS},
    }
    incomplete = []
    for record in records:
        path = Path(record["metadata_path"])
        if not path.exists():
            incomplete.append(record.get("call_id", str(path)))
            continue
        try:
            attempts = json.loads(path.read_text(encoding="utf-8")).get(
                "attempts", []
            )
        except (OSError, json.JSONDecodeError):
            incomplete.append(record.get("call_id", str(path)))
            continue
        if not attempts:
            incomplete.append(record.get("call_id", str(path)))
            continue
        result["attempts"] += len(attempts)
        for attempt in attempts:
            usage = attempt.get("usage")
            if not isinstance(usage, dict) or any(
                isinstance(usage.get(field), bool)
                or not isinstance(usage.get(field), int)
                or usage[field] < 0
                for field in USAGE_FIELDS
            ):
                incomplete.append(record.get("call_id", str(path)))
                continue
            for field in USAGE_FIELDS:
                result[field] += usage[field]
    result["complete"] = not incomplete
    result["incomplete_call_ids"] = sorted(set(incomplete))
    return result


def weighted_tokens(usage):
    if not usage.get("complete"):
        return None
    return (
        usage["input_tokens"]
        + usage["output_tokens"]
        + usage["reasoning_output_tokens"]
    )


def break_even_multiplier(small_usage, high_usage, target_ratio):
    small = weighted_tokens(small_usage)
    high = weighted_tokens(high_usage)
    if small is None or high is None or small == 0:
        return {
            "complete": False,
            "target_ratio": target_ratio,
            "small_weighted_tokens": small,
            "high_weighted_tokens": high,
            "max_small_to_high_unit_price_ratio": None,
        }
    return {
        "complete": True,
        "target_ratio": target_ratio,
        "small_weighted_tokens": small,
        "high_weighted_tokens": high,
        "max_small_to_high_unit_price_ratio": round(
            target_ratio * high / small,
            6,
        ),
    }

