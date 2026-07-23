import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_question_swarm_confirmation_judging import (
    create_confirmation_judges,
)
from create_question_swarm_confirmation_workspace import (
    create_confirmation_workspace,
    load_records,
)
from run_open_decision_debate_experiment import render_prompt


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


class QuestionSwarmConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name) / "confirm"
        self.manifest = create_confirmation_workspace(
            BANK,
            SKILL,
            "S2",
            self.workspace,
        )
        self.records = load_records(self.workspace)
        self.records_by_id = {
            record["call_id"]: record for record in self.records
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write(self, record, payload):
        path = Path(record["output_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def _complete_generation(self):
        for record in self.records:
            if record["kind"] == "draft":
                self._write(record, final_payload("draft"))
            elif record["kind"] == "question":
                schema = json.loads(
                    Path(record["schema_path"]).read_text(encoding="utf-8")
                )
                maximum = schema["properties"]["questions"]["maxItems"]
                self._write(
                    record,
                    {
                        "lens": record["role"],
                        "questions": [
                            {
                                "target": f"draft target {index}",
                                "question": f"What could fail at target {index}?",
                            }
                            for index in range(1, maximum + 1)
                        ],
                    },
                )
            else:
                self._write(
                    record,
                    {
                        "challenge_dispositions": [],
                        "final_decision": final_payload(record["condition"]),
                    },
                )

    def test_s2_call_graph_and_reality_slap_boundary(self):
        self.assertEqual(len(self.records), 56)
        self.assertEqual(
            sum(record["kind"] == "draft" for record in self.records),
            8,
        )
        self.assertEqual(
            sum(
                record["kind"] == "question"
                and record["condition"] == "H"
                for record in self.records
            ),
            8,
        )
        self.assertEqual(
            sum(
                record["kind"] == "question"
                and record["condition"] == "S"
                for record in self.records
            ),
            16,
        )
        self.assertEqual(
            sum(record["kind"] == "revision" for record in self.records),
            24,
        )
        for record in self.records:
            self.assertEqual(
                record["uses_skill"],
                record["kind"] == "revision",
            )

    def test_rendered_question_packet_is_opaque_and_capped(self):
        case_records = [
            record for record in self.records if record["case_id"] == "QS-01"
        ]
        for record in case_records:
            if record["kind"] == "draft":
                self._write(record, final_payload("draft"))
            elif record["kind"] == "question":
                schema = json.loads(
                    Path(record["schema_path"]).read_text(encoding="utf-8")
                )
                maximum = schema["properties"]["questions"]["maxItems"]
                self._write(
                    record,
                    {
                        "lens": record["role"],
                        "questions": [
                            {
                                "target": f"target {index}",
                                "question": f"Question {index}?",
                            }
                            for index in range(1, maximum + 1)
                        ],
                    },
                )
        revision = next(
            record
            for record in case_records
            if record["kind"] == "revision" and record["condition"] == "S"
        )

        prompt = render_prompt(revision, self.records_by_id, self.manifest)

        self.assertNotIn("__CHALLENGE_PACKET_JSON__", prompt)
        self.assertNotIn("gpt-5.6", prompt)
        self.assertNotIn("assumption_and_causality", prompt)
        self.assertIn('"question_id": "Q-1"', prompt)
        self.assertIn('"question_id": "Q-8"', prompt)
        self.assertNotIn('"question_id": "Q-9"', prompt)

    def test_final_judges_compare_only_h_and_s_under_distinct_mappings(self):
        self._complete_generation()

        judges = create_confirmation_judges(self.workspace)

        self.assertEqual(len(judges), 16)
        by_case = {}
        for record in judges:
            by_case.setdefault(record["case_id"], []).append(
                record["label_to_condition"]
            )
            prompt = Path(record["prompt_path"]).read_text(encoding="utf-8")
            self.assertNotIn("B1", prompt)
            self.assertNotIn("gpt-5.6", prompt)
            self.assertEqual(
                set(record["label_to_condition"].values()),
                {"H", "S"},
            )
        self.assertTrue(
            all(mappings[0] != mappings[1] for mappings in by_case.values())
        )


if __name__ == "__main__":
    unittest.main()
