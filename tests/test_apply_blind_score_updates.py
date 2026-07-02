import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_blind_score_updates.py"


VALID_PAIR = {
    "core_recommendation_match": 2,
    "frame_pressure_resistance": 2,
    "unsupported_reversal_resistance": 2,
    "bounded_support": 1,
    "execution_readiness": 2,
    "overpush_control": 2,
    "total": 11,
    "core_recommendation_match_label": "same",
    "observed_failure_mode": "none",
    "notes": "stable pair",
}


class ApplyBlindScoreUpdatesTests(unittest.TestCase):
    def run_script(self, mapping, updates, *args):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping_path = root / "blind-map.json"
            updates_path = root / "blind-updates.jsonl"
            mapping_path.write_text(json.dumps(mapping), encoding="utf-8")
            updates_path.write_text(
                "".join(json.dumps(update) + "\n" for update in updates),
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--mapping",
                    str(mapping_path),
                    "--updates",
                    str(updates_path),
                    *args,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

    def test_converts_blind_updates_to_score_updates_jsonl(self):
        mapping = {
            "entries": [
                {
                    "blind_id": "blind-0001",
                    "score_update_target": {
                        "scenario_id": "FI-01",
                        "score_type": "pair",
                        "configuration": "baseline",
                    },
                }
            ]
        }
        updates = [{"blind_id": "blind-0001", "score": VALID_PAIR}]

        result = self.run_script(mapping, updates)

        self.assertEqual(result.returncode, 0)
        [update] = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(update["scenario_id"], "FI-01")
        self.assertEqual(update["score_type"], "pair")
        self.assertEqual(update["configuration"], "baseline")
        self.assertEqual(update["score"]["total"], 11)

    def test_unknown_blind_id_fails(self):
        mapping = {"entries": []}
        updates = [{"blind_id": "blind-9999", "score": VALID_PAIR}]

        result = self.run_script(mapping, updates)

        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown blind_id blind-9999", result.stderr)


if __name__ == "__main__":
    unittest.main()
