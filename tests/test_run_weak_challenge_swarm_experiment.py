import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_weak_challenge_swarm_workspace import (
    CHALLENGE_PACKET_MARKER,
    DRAFT_MARKER,
    ROLES,
    create_workspace,
    load_records,
)
from run_open_decision_debate_experiment import (
    call_eligibility,
    expected_challenge_ids,
    iter_pending_calls,
    render_prompt,
    rendered_challenge_packet,
    response_status,
    shared_input_hashes,
)


BANK = ROOT / "evals" / "open-decision-case-bank.json"
SKILL = ROOT / "SKILL.md"


def final_payload(label="bounded pilot"):
    return {
        "recommendation": label,
        "accepted_claims": ["The reversible path fits supplied facts."],
        "rejected_claims": ["An irreversible rollout is unsupported."],
        "residual_dissent": ["The effect size remains uncertain."],
        "decision_owner": "Named owner",
        "next_action": "Run the bounded step.",
        "stop_conditions": ["Stop on threshold failure."],
        "rollback_or_revision_path": "Return to the prior state.",
        "change_evidence": ["Measured threshold evidence."],
        "known_facts": ["The case states a hard constraint."],
        "inferences": ["A bounded step limits downside."],
        "uncertainties": ["Outcome magnitude."],
    }


def challenge_payload(role, count=2):
    return {
        "role": role,
        "challenges": [
            {
                "question_or_challenge": f"Challenge {index + 1}",
                "why_material": "It could change the safe decision.",
                "case_fact_refs": ["facts[0]"],
                "failure_if_ignored": "The decision may violate a constraint.",
                "disconfirming_evidence": "Direct evidence that the constraint is met.",
                "severity": "high",
            }
            for index in range(count)
        ],
        "coverage_limitations": ["No external evidence was available."],
    }


class RunWeakChallengeSwarmExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "workspace"
        create_workspace(BANK, SKILL, self.workspace, seed=20260725)
        self.manifest = json.loads(
            (self.workspace / "manifest.json").read_text(encoding="utf-8")
        )
        self.records = load_records(self.workspace)
        self.records_by_id = {record["call_id"]: record for record in self.records}

    def tearDown(self):
        self.temp_dir.cleanup()

    def record(self, *, case_id="OD-13", condition=None, kind=None, role=None):
        return next(
            record
            for record in self.records
            if record["case_id"] == case_id
            and (condition is None or record["condition"] == condition)
            and (kind is None or record["kind"] == kind)
            and (role is None or record.get("role") == role)
        )

    def write(self, record, payload):
        path = Path(record["output_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def complete_case_dependencies(self):
        draft = self.record(condition="A")
        self.write(draft, final_payload())
        for role in ROLES:
            self.write(
                self.record(kind="challenge", role=role),
                challenge_payload(role),
            )

    def revision_payload(self, record, *, omit_last=False, duplicate=False):
        challenge_ids = expected_challenge_ids(record, self.records_by_id, self.manifest)
        if omit_last:
            challenge_ids = challenge_ids[:-1]
        if duplicate and challenge_ids:
            challenge_ids[-1] = challenge_ids[0]
        return {
            "challenge_dispositions": [
                {
                    "challenge_id": challenge_id,
                    "disposition": "accepted",
                    "case_grounded_reason": "The referenced constraint is material.",
                    "resulting_change": "The final adds a bounded safeguard.",
                }
                for challenge_id in challenge_ids
            ],
            "final_decision": final_payload("bounded revision"),
        }

    def test_initial_ready_wave_has_drafts_and_boundary_scouts_only(self):
        ready = list(iter_pending_calls(self.workspace, "generation"))
        self.assertEqual(len(ready), 24)
        self.assertEqual(sum(record["kind"] == "draft" for record in ready), 12)
        self.assertEqual(
            {
                record["role"]
                for record in ready
                if record["kind"] == "challenge"
            },
            {"boundary_scout"},
        )

    def test_draft_rendering_enables_auditors_without_metadata_leakage(self):
        draft = self.record(condition="A")
        auditor = self.record(kind="challenge", role="adversarial_auditor")
        self.assertEqual(call_eligibility(auditor, self.records_by_id), "blocked")
        self.write(draft, final_payload())

        prompt = render_prompt(auditor, self.records_by_id, self.manifest)

        self.assertEqual(call_eligibility(auditor, self.records_by_id), "ready")
        self.assertNotIn(DRAFT_MARKER, prompt)
        self.assertIn('"recommendation": "bounded pilot"', prompt)
        self.assertNotIn("gpt-5.6", prompt)
        self.assertNotIn("reasoning_effort", prompt)

    def test_c0_and_c1_receive_identical_ordered_challenge_packet(self):
        self.complete_case_dependencies()
        c0 = self.record(condition="C0")
        c1 = self.record(condition="C1")

        c0_packet = rendered_challenge_packet(c0, self.records_by_id, self.manifest)
        c1_packet = rendered_challenge_packet(c1, self.records_by_id, self.manifest)

        self.assertEqual(c0_packet, c1_packet)
        self.assertEqual(
            shared_input_hashes(c0, self.records_by_id, self.manifest),
            shared_input_hashes(c1, self.records_by_id, self.manifest),
        )
        text = json.dumps(c0_packet)
        self.assertNotIn("gpt-5.6", text)
        self.assertNotIn("call_id", text)
        self.assertNotIn("output_path", text)
        self.assertEqual(
            [entry["source_role"] for entry in c0_packet],
            [
                role
                for role in self.manifest["challenge_order_by_case"]["OD-13"]
                for _ in range(2)
            ],
        )
        self.assertEqual(
            [entry["challenge_id"] for entry in c0_packet],
            expected_challenge_ids(c0, self.records_by_id, self.manifest),
        )

    def test_rendered_c_prompt_replaces_both_markers(self):
        self.complete_case_dependencies()
        c0 = self.record(condition="C0")
        prompt = render_prompt(c0, self.records_by_id, self.manifest)
        self.assertNotIn(DRAFT_MARKER, prompt)
        self.assertNotIn(CHALLENGE_PACKET_MARKER, prompt)
        self.assertIn('"source_role": "boundary_scout"', prompt)

    def test_revision_dispositions_must_cover_every_challenge_once(self):
        self.complete_case_dependencies()
        c0 = self.record(condition="C0")

        self.write(c0, self.revision_payload(c0, omit_last=True))
        self.assertEqual(
            response_status(c0, self.records_by_id, self.manifest),
            "invalid",
        )
        self.write(c0, self.revision_payload(c0, duplicate=True))
        self.assertEqual(
            response_status(c0, self.records_by_id, self.manifest),
            "invalid",
        )
        self.write(c0, self.revision_payload(c0))
        self.assertEqual(
            response_status(c0, self.records_by_id, self.manifest),
            "complete",
        )

    def test_no_challenge_revision_requires_empty_dispositions(self):
        draft = self.record(condition="A")
        b0 = self.record(condition="B0")
        self.write(draft, final_payload())
        payload = self.revision_payload(b0)
        self.write(b0, payload)
        self.assertEqual(
            response_status(b0, self.records_by_id, self.manifest),
            "complete",
        )
        payload["challenge_dispositions"] = [
            {
                "challenge_id": "invented-1",
                "disposition": "accepted",
                "case_grounded_reason": "Invented",
                "resulting_change": "Invented",
            }
        ]
        self.write(b0, payload)
        self.assertEqual(
            response_status(b0, self.records_by_id, self.manifest),
            "invalid",
        )

    def test_challenge_role_must_match_record(self):
        challenge = self.record(kind="challenge", role="boundary_scout")
        self.write(challenge, challenge_payload("adversarial_auditor"))
        self.assertEqual(
            response_status(challenge, self.records_by_id, self.manifest),
            "invalid",
        )


if __name__ == "__main__":
    unittest.main()
