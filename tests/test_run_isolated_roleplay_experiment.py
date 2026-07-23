import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_isolated_roleplay_workspace import create_workspace, load_records
from run_isolated_roleplay_experiment import (
    audit_workspace,
    build_command,
    call_eligibility,
    iter_pending_calls,
    render_prompt,
    response_status,
    validate_record_payload,
    validate_payload,
)


BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
SKILL = ROOT / "SKILL.md"


def role_payload(action="Use a bounded alternative"):
    return {
        "recommended_action": action,
        "stance_class": "bounded_alternative",
        "supporting_evidence": ["The facts support a bounded path."],
        "non_negotiable_boundaries": ["Do not accept the unsafe extreme."],
        "change_conditions": ["Material new evidence changes the tradeoff."],
        "confidence": 80,
    }


class RunIsolatedRoleplayExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        create_workspace(
            bank_path=BANK,
            skill_path=SKILL,
            output_dir=self.workspace,
            seed=20260723,
            model="gpt-5.6-sol",
            reasoning_effort="medium",
            scenario_ids=["SD-01"],
        )
        self.manifest = json.loads((self.workspace / "manifest.json").read_text(encoding="utf-8"))
        self.records = load_records(self.workspace)
        self.records_by_id = {record["call_id"]: record for record in self.records}

    def tearDown(self):
        self.temp_dir.cleanup()

    def record(self, condition, kind, role=None):
        for record in self.records:
            if record["condition"] != condition or record["kind"] != kind:
                continue
            if role is None or record.get("role") == role:
                return record
        self.fail(f"record not found: {condition} {kind} {role}")

    def write_response(self, record, payload):
        path = Path(record["output_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def write_attempts(self, record, attempts):
        path = Path(record["metadata_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"attempts": attempts}) + "\n", encoding="utf-8")

    def test_command_locks_model_effort_schema_and_neutral_cwd(self):
        record = self.record("isolated-control", "role", "evidence_reviewer")
        command = build_command(
            record,
            self.manifest,
            codex_bin="codex",
            cwd=Path("/private/tmp"),
            prompt="sealed prompt",
        )

        self.assertEqual(command[command.index("--model") + 1], "gpt-5.6-sol")
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--output-schema", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertEqual(command[-1], "sealed prompt")

    def test_initial_generation_pending_excludes_dependency_blocked_chairs(self):
        pending = list(iter_pending_calls(self.workspace, phase="generation"))

        self.assertEqual(len(pending), 8)
        self.assertEqual(sum(record["kind"] == "meeting" for record in pending), 2)
        self.assertEqual(sum(record["kind"] == "role" for record in pending), 6)
        self.assertFalse(any(record["kind"] == "chair" for record in pending))

    def test_valid_completed_call_is_skipped_but_invalid_json_is_retried(self):
        valid = self.record("isolated-control", "role", "evidence_reviewer")
        invalid = self.record("isolated-control", "role", "delivery_owner")
        self.write_response(valid, role_payload())
        Path(invalid["output_path"]).write_text("not json\n", encoding="utf-8")

        pending_ids = {record["call_id"] for record in iter_pending_calls(self.workspace, phase="generation")}

        self.assertNotIn(valid["call_id"], pending_ids)
        self.assertIn(invalid["call_id"], pending_ids)
        self.assertEqual(response_status(valid), "complete")
        self.assertEqual(response_status(invalid), "invalid")

    def test_schema_validation_rejects_extra_fields_and_bad_confidence(self):
        record = self.record("isolated-control", "role", "executive_sponsor")
        schema = json.loads(Path(record["schema_path"]).read_text(encoding="utf-8"))
        payload = role_payload()
        payload["surprise"] = True

        with self.assertRaisesRegex(ValueError, "unexpected properties"):
            validate_payload(payload, schema)

        payload = role_payload()
        payload["confidence"] = 101
        with self.assertRaisesRegex(ValueError, "maximum"):
            validate_payload(payload, schema)

    def test_invalid_role_blocks_chair(self):
        chair = self.record("isolated-control", "chair")
        for call_id in chair["depends_on"][:2]:
            self.write_response(self.records_by_id[call_id], role_payload())
        Path(self.records_by_id[chair["depends_on"][2]]["output_path"]).write_text("{}\n", encoding="utf-8")

        self.assertEqual(call_eligibility(chair, self.records_by_id), "blocked")
        self.assertNotIn(chair["call_id"], {record["call_id"] for record in iter_pending_calls(self.workspace, "generation")})
        audit = audit_workspace(self.workspace)
        self.assertIn(chair["depends_on"][2], audit["invalid_call_ids"])
        self.assertIn(chair["call_id"], audit["dependency_blocked_call_ids"])

    def test_chair_prompt_renders_three_randomized_role_payloads_only_after_completion(self):
        chair = self.record("isolated-skill", "chair")
        for index, call_id in enumerate(chair["depends_on"]):
            self.write_response(self.records_by_id[call_id], role_payload(action=f"action-{index}"))

        prompt = render_prompt(chair, self.records_by_id, self.manifest)

        self.assertNotIn("__SEALED_ROLE_OUTPUTS_JSON__", prompt)
        self.assertIn("action-0", prompt)
        self.assertIn("action-1", prompt)
        self.assertIn("action-2", prompt)
        self.assertEqual(call_eligibility(chair, self.records_by_id), "ready")

    def test_retry_count_cannot_exceed_one_retry(self):
        record = self.record("shared-control", "meeting")
        Path(record["output_path"]).write_text("invalid\n", encoding="utf-8")
        self.write_attempts(record, [{"attempt": 1}, {"attempt": 2}])

        self.assertEqual(call_eligibility(record, self.records_by_id), "retry-exhausted")
        self.assertNotIn(record["call_id"], {item["call_id"] for item in iter_pending_calls(self.workspace, "generation")})

    def test_usage_limit_marker_is_invalid_not_complete(self):
        record = self.record("shared-skill", "meeting")
        Path(record["output_path"]).write_text("ERROR: You've hit your usage limit\n", encoding="utf-8")

        self.assertEqual(response_status(record), "invalid")

    def test_judge_validation_derives_eight_labels_from_schema(self):
        labels = list("ABCDEFGH")
        schema_path = self.workspace / "schemas" / "eight-label-judge.json"
        normalized_item = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "role": {"type": "string", "enum": [
                    "executive_sponsor", "evidence_reviewer", "delivery_owner"
                ]},
                "stance_class": {"type": "string", "enum": ["bounded_alternative"]},
            },
            "required": ["role", "stance_class"],
        }
        evaluation_item = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "label": {"type": "string", "enum": labels},
                "normalized_role_stances": {
                    "type": "array", "items": normalized_item, "minItems": 3, "maxItems": 3
                },
            },
            "required": ["label", "normalized_role_stances"],
        }
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "scenario_id": {"type": "string"},
                "evaluations": {
                    "type": "array", "items": evaluation_item, "minItems": 8, "maxItems": 8
                },
            },
            "required": ["scenario_id", "evaluations"],
        }
        schema_path.write_text(json.dumps(schema) + "\n", encoding="utf-8")
        record = {"kind": "judge", "scenario_id": "SD-01", "schema_path": str(schema_path)}
        roles = ["executive_sponsor", "evidence_reviewer", "delivery_owner"]
        evaluation = lambda label: {
            "label": label,
            "normalized_role_stances": [
                {"role": role, "stance_class": "bounded_alternative"} for role in roles
            ],
        }

        validate_record_payload(
            record,
            {"scenario_id": "SD-01", "evaluations": [evaluation(label) for label in labels]},
        )

    def test_judge_validation_rejects_missing_schema_derived_label(self):
        labels = list("ABCDEFGH")
        schema_path = self.workspace / "schemas" / "eight-label-minimal.json"
        role_enum = ["executive_sponsor", "evidence_reviewer", "delivery_owner"]
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "scenario_id": {"type": "string"},
                "evaluations": {
                    "type": "array",
                    "minItems": 8,
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string", "enum": labels},
                            "normalized_role_stances": {
                                "type": "array",
                                "minItems": 3,
                                "maxItems": 3,
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "role": {"type": "string", "enum": role_enum},
                                    },
                                    "required": ["role"],
                                },
                            },
                        },
                        "required": ["label", "normalized_role_stances"],
                    },
                },
            },
            "required": ["scenario_id", "evaluations"],
        }
        schema_path.write_text(json.dumps(schema) + "\n", encoding="utf-8")
        record = {"kind": "judge", "scenario_id": "SD-01", "schema_path": str(schema_path)}
        evaluations = [
            {
                "label": label,
                "normalized_role_stances": [{"role": role} for role in role_enum],
            }
            for label in list("ABCDEFG") + ["G"]
        ]

        with self.assertRaisesRegex(ValueError, "each opaque label exactly once"):
            validate_record_payload(record, {"scenario_id": "SD-01", "evaluations": evaluations})


if __name__ == "__main__":
    unittest.main()
