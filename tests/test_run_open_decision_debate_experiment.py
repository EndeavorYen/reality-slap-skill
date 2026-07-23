import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_open_decision_debate_workspace import (
    ROLES,
    create_workspace,
    load_records,
)
from run_open_decision_debate_experiment import (
    audit_workspace,
    build_command,
    call_eligibility,
    iter_pending_calls,
    parse_usage_events,
    render_prompt,
    response_status,
    validate_payload,
)


BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"


def first_payload(role):
    return {
        "role": role,
        "recommendation": "Run a bounded pilot.",
        "claims": [
            {"claim": "A pilot produces evidence.", "evidence_refs": ["fact-1"], "confidence": 80},
            {"claim": "Rollback limits downside.", "evidence_refs": ["fact-2"], "confidence": 75},
        ],
        "constraints": ["Protect the hard boundary."],
        "failure_modes": ["The pilot could be too broad."],
        "uncertainties": ["The effect size is unknown."],
        "falsifiers": ["The pilot misses the threshold."],
        "reversible_test": "Start with one cohort.",
    }


def cross_payload(role):
    return {
        "role": role,
        "strongest_peer_point_accepted": "A peer identified a real constraint.",
        "strongest_unresolved_objection": "The scale remains uncertain.",
        "unsupported_peer_claims": ["One claim lacks evidence."],
        "update_type": "revised",
        "updated_recommendation": "Run a smaller bounded pilot.",
        "update_reason": "The peer constraint changes the safe scope.",
        "remaining_uncertainty": ["Outcome magnitude remains unknown."],
    }


class RunOpenDecisionDebateExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        create_workspace(BANK, SKILL, self.workspace, "primary", 20260724)
        self.manifest = json.loads((self.workspace / "manifest.json").read_text(encoding="utf-8"))
        self.records = load_records(self.workspace)
        self.records_by_id = {record["call_id"]: record for record in self.records}

    def tearDown(self):
        self.temp_dir.cleanup()

    def case_record(self, condition, kind, phase=None, role=None):
        return next(
            record
            for record in self.records
            if record["case_id"] == "OD-01"
            and record["condition"] == condition
            and record["kind"] == kind
            and (phase is None or record["phase"] == phase)
            and (role is None or record.get("role") == role)
        )

    def write_response(self, record, payload):
        path = Path(record["output_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def write_attempts(self, record, attempts):
        path = Path(record["metadata_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"call_id": record["call_id"], "attempts": attempts}) + "\n")

    def test_command_uses_record_level_model_and_effort(self):
        record = self.case_record(
            "heterogeneous-debate-rs-chair",
            "role",
            role=self.manifest["terra_role_by_case"]["OD-01"],
        )

        command = build_command(record, "codex", Path("/private/tmp"), "sealed prompt")

        self.assertEqual(command[command.index("--model") + 1], "gpt-5.6-terra")
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--json", command)
        self.assertEqual(command[-1], "sealed prompt")

    def test_parse_usage_events_requires_one_complete_usage_record(self):
        events = "\n".join(
            [
                '{"type":"thread.started","thread_id":"thread-1"}',
                '{"type":"turn.completed","usage":{"input_tokens":10,'
                '"cached_input_tokens":2,"output_tokens":3,'
                '"reasoning_output_tokens":1}}',
            ]
        )

        self.assertEqual(
            parse_usage_events(events),
            {
                "input_tokens": 10,
                "cached_input_tokens": 2,
                "output_tokens": 3,
                "reasoning_output_tokens": 1,
            },
        )

        with self.assertRaisesRegex(ValueError, "exactly one"):
            parse_usage_events('{"type":"thread.started"}')
        with self.assertRaisesRegex(ValueError, "exactly one"):
            parse_usage_events(events + "\n" + events.splitlines()[-1])
        with self.assertRaisesRegex(ValueError, "missing usage field"):
            parse_usage_events(
                '{"type":"turn.completed","usage":{"input_tokens":10}}'
            )

    def test_initial_ready_wave_has_exactly_sixty_calls(self):
        pending = list(iter_pending_calls(self.workspace, "generation"))

        self.assertEqual(len(pending), 60)
        self.assertEqual(sum(record["kind"] == "direct" for record in pending), 12)
        self.assertEqual(
            sum(record["kind"] == "serial" and record["phase"] == "draft" for record in pending),
            12,
        )
        self.assertEqual(sum(record["kind"] == "role" for record in pending), 36)

    def test_cross_exam_waits_for_all_first_round_records(self):
        cross = self.case_record(
            "heterogeneous-debate-rs-chair",
            "cross_exam",
            role="proposal_advocate",
        )
        self.assertEqual(call_eligibility(cross, self.records_by_id), "blocked")

        for role in ROLES:
            record = self.case_record("heterogeneous-debate-rs-chair", "role", role=role)
            self.write_response(record, first_payload(role))

        self.assertEqual(call_eligibility(cross, self.records_by_id), "ready")

    def test_cross_exam_rendering_labels_self_and_anonymous_peers_without_models(self):
        cross = self.case_record(
            "heterogeneous-debate-rs-chair",
            "cross_exam",
            role="proposal_advocate",
        )
        for role in ROLES:
            record = self.case_record("heterogeneous-debate-rs-chair", "role", role=role)
            self.write_response(record, first_payload(role))

        prompt = render_prompt(cross, self.records_by_id, self.manifest)

        self.assertNotIn("__DEPENDENCY_PACKET_JSON__", prompt)
        self.assertIn('"label": "SELF"', prompt)
        self.assertIn('"label": "PEER-A"', prompt)
        self.assertIn('"label": "PEER-B"', prompt)
        self.assertNotIn("gpt-5.6", prompt)
        self.assertNotIn("reasoning_effort", prompt)

    def test_role_schema_rejects_extra_fields_and_wrong_role(self):
        record = self.case_record(
            "heterogeneous-debate-rs-chair",
            "role",
            role="failure_mode_red_team",
        )
        schema = json.loads(Path(record["schema_path"]).read_text(encoding="utf-8"))
        payload = first_payload("failure_mode_red_team")
        payload["surprise"] = True
        with self.assertRaisesRegex(ValueError, "unexpected properties"):
            validate_payload(payload, schema)

        payload = first_payload("proposal_advocate")
        self.write_response(record, payload)
        self.assertEqual(response_status(record), "invalid")

    def test_retry_exhaustion_blocks_downstream_calls(self):
        role = self.case_record(
            "heterogeneous-debate-rs-chair",
            "role",
            role="option_architect",
        )
        self.write_attempts(role, [{"attempt": 1}, {"attempt": 2}])
        cross = self.case_record(
            "heterogeneous-debate-rs-chair",
            "cross_exam",
            role="proposal_advocate",
        )

        self.assertEqual(call_eligibility(role, self.records_by_id), "retry-exhausted")
        self.assertEqual(call_eligibility(cross, self.records_by_id), "blocked")
        audit = audit_workspace(self.workspace)
        self.assertIn(role["call_id"], audit["retry_exhausted_call_ids"])
        self.assertIn(cross["call_id"], audit["dependency_blocked_call_ids"])

    def test_explicit_third_attempt_can_recover_an_exhausted_call(self):
        role = self.case_record(
            "heterogeneous-debate-rs-chair",
            "role",
            role="option_architect",
        )
        self.write_attempts(
            role,
            [
                {"attempt": 1, "invalid_reason": "invalid-output"},
                {"attempt": 2, "invalid_reason": "invalid-output"},
            ],
        )

        self.assertEqual(
            call_eligibility(role, self.records_by_id),
            "retry-exhausted",
        )
        self.assertEqual(
            call_eligibility(role, self.records_by_id, max_attempts=3),
            "ready",
        )

    def test_valid_completed_call_is_skipped_and_invalid_json_is_retried(self):
        valid = self.case_record(
            "heterogeneous-debate-rs-chair",
            "role",
            role="proposal_advocate",
        )
        invalid = self.case_record(
            "heterogeneous-debate-rs-chair",
            "role",
            role="failure_mode_red_team",
        )
        self.write_response(valid, first_payload("proposal_advocate"))
        Path(invalid["output_path"]).write_text("not json\n", encoding="utf-8")

        pending = {record["call_id"] for record in iter_pending_calls(self.workspace, "generation")}

        self.assertNotIn(valid["call_id"], pending)
        self.assertIn(invalid["call_id"], pending)
        self.assertEqual(response_status(valid), "complete")
        self.assertEqual(response_status(invalid), "invalid")


if __name__ == "__main__":
    unittest.main()
