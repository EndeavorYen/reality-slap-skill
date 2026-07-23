import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_question_swarm_confirmation_workspace import (
    create_confirmation_workspace,
    load_records,
)
from create_question_swarm_ledger_replay_judging import (
    create_ledger_replay_judges,
)
from create_question_swarm_ledger_pair_fallback import append_pair_fallback
from create_question_swarm_ledger_replay_workspace import (
    create_ledger_replay_workspace,
)
from run_open_decision_debate_experiment import validate_record_payload


BANK = ROOT / "evals" / "question-swarm-holdout-bank.json"
SKILL = ROOT / "SKILL.md"


def final_payload(label):
    return {
        "recommendation": f"Run the bounded {label} path.",
        "accepted_claims": ["A reversible test is supported."],
        "rejected_claims": ["An irreversible rollout is unsupported."],
        "residual_dissent": ["The effect size is uncertain."],
        "decision_owner": "Named owner",
        "next_action": "Start the bounded test.",
        "stop_conditions": ["Stop if the threshold fails."],
        "rollback_or_revision_path": "Return to the previous state.",
        "change_evidence": ["Measured threshold evidence."],
        "known_facts": ["A supplied case fact."],
        "inferences": ["A bounded step limits downside."],
        "uncertainties": ["Outcome magnitude."],
    }


class LedgerReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.source = root / "source"
        create_confirmation_workspace(BANK, SKILL, "S2", self.source)
        self._complete_source()
        self.workspace = root / "replay"
        self.manifest = create_ledger_replay_workspace(
            self.source,
            SKILL,
            self.workspace,
        )
        self.records = load_records(self.workspace)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, record, payload):
        path = Path(record["output_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        metadata = Path(record["metadata_path"])
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(
            json.dumps(
                {
                    "attempts": [
                        {
                            "usage": {
                                "input_tokens": 100,
                                "cached_input_tokens": 0,
                                "output_tokens": 50,
                                "reasoning_output_tokens": 20,
                            }
                        }
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def _complete_source(self):
        for record in load_records(self.source):
            if record["kind"] == "draft":
                payload = final_payload("draft")
            elif record["kind"] == "question":
                schema = json.loads(
                    Path(record["schema_path"]).read_text(encoding="utf-8")
                )
                count = schema["properties"]["questions"]["maxItems"]
                payload = {
                    "lens": record["role"],
                    "questions": [
                        {
                            "target": f"target {index}",
                            "question": f"What could fail at target {index}?",
                        }
                        for index in range(1, count + 1)
                    ],
                }
            else:
                payload = {
                    "challenge_dispositions": [],
                    "final_decision": final_payload(record["condition"]),
                }
            self._write(record, payload)

    def _complete_new(self):
        for record in self.records:
            if record["kind"] == "direct":
                self._write(record, final_payload(record["condition"]))
            elif record["kind"] == "revision" and record["condition"] == "L":
                ids = record["ledger_constraint_ids"]
                self._write(
                    record,
                    {
                        "challenge_dispositions": [],
                        "constraint_ledger": [
                            {
                                "constraint_id": item_id,
                                "status": "closed",
                                "final_decision_field": "recommendation",
                                "closure_note": f"Closed {item_id}.",
                            }
                            for item_id in ids
                        ],
                        "interaction_checks": [
                            {
                                "left_constraint_id": ids[0],
                                "right_constraint_id": ids[1],
                                "risk": "A material interaction.",
                                "disposition": "addressed",
                            },
                            {
                                "left_constraint_id": ids[1],
                                "right_constraint_id": ids[2],
                                "risk": "Another material interaction.",
                                "disposition": "addressed",
                            },
                        ],
                        "final_decision": final_payload("L"),
                    },
                )

    def test_call_graph_efforts_and_shared_questions(self):
        self.assertEqual(self.manifest["planned_new_generation_calls"], 24)
        self.assertEqual(
            sum(
                record["kind"] == "revision"
                and record["condition"] == "L"
                for record in self.records
            ),
            8,
        )
        efforts = {
            record["condition"]: record["reasoning_effort"]
            for record in self.records
            if record["kind"] == "direct"
        }
        self.assertEqual(efforts, {"DH": "high", "DX": "xhigh"})
        case = [
            record for record in self.records if record["case_id"] == "QS-01"
        ]
        s_questions = {
            record["call_id"]
            for record in case
            if record["kind"] == "question" and record["condition"] == "S"
        }
        ledger = next(
            record
            for record in case
            if record["kind"] == "revision" and record["condition"] == "L"
        )
        self.assertTrue(s_questions.issubset(set(ledger["depends_on"])))
        self.assertTrue(
            any(
                record["kind"] == "revision"
                and record["condition"] == "B1"
                for record in self.records
            )
        )

    def test_prompts_keep_process_boundaries(self):
        ledger = next(
            record
            for record in self.records
            if record["kind"] == "revision" and record["condition"] == "L"
        )
        direct = next(
            record for record in self.records if record["kind"] == "direct"
        )
        ledger_prompt = Path(ledger["prompt_path"]).read_text(encoding="utf-8")
        direct_prompt = Path(direct["prompt_path"]).read_text(encoding="utf-8")
        self.assertIn("Numbered source constraints", ledger_prompt)
        self.assertIn("FROZEN_REALITY_SLAP", ledger_prompt)
        self.assertIn("__CHALLENGE_PACKET_JSON__", ledger_prompt)
        self.assertNotIn("__CHALLENGE_PACKET_JSON__", direct_prompt)
        self.assertNotIn("Frozen shared draft", direct_prompt)
        self.assertIn("Work alone", direct_prompt)

    def test_ledger_validation_rejects_duplicate_ids(self):
        self._complete_new()
        record = next(
            record
            for record in self.records
            if record["kind"] == "revision" and record["condition"] == "L"
        )
        payload = json.loads(
            Path(record["output_path"]).read_text(encoding="utf-8")
        )
        payload["constraint_ledger"][1]["constraint_id"] = (
            payload["constraint_ledger"][0]["constraint_id"]
        )
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_record_payload(record, payload)

    def test_five_way_judges_are_blind_and_distinct(self):
        self._complete_new()
        judges = create_ledger_replay_judges(self.workspace)
        self.assertEqual(len(judges), 16)
        by_case = {}
        for record in judges:
            by_case.setdefault(record["case_id"], []).append(
                record["label_to_condition"]
            )
            self.assertEqual(
                set(record["label_to_condition"].values()),
                {"H", "S", "L", "DH", "DX"},
            )
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            for hidden in (
                "gpt-5.6",
                '"H"',
                '"S"',
                '"L"',
                '"DH"',
                '"DX"',
                "reasoning_effort",
            ):
                self.assertNotIn(hidden, prompt)
        self.assertTrue(
            all(mappings[0] != mappings[1] for mappings in by_case.values())
        )

    def test_pair_fallback_scores_each_condition_once(self):
        self._complete_new()
        create_ledger_replay_judges(self.workspace)

        records = append_pair_fallback(self.workspace, "QS-02")

        self.assertEqual(len(records), 3)
        scored = [
            condition
            for record in records
            for condition in record["score_conditions"]
        ]
        self.assertEqual(sorted(scored), ["DH", "DX", "H", "L", "S"])
        for record in records:
            self.assertEqual(record["candidate_labels"], ["A", "B"])
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertNotIn("gpt-5.6", prompt)
            self.assertNotIn("reasoning_effort", prompt)


if __name__ == "__main__":
    unittest.main()
