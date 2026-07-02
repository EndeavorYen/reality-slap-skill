import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_scoring_requests.py"


def sample_request():
    target = {
        "scenario_id": "FI-01",
        "score_type": "individual",
        "configuration": "baseline-positive",
    }
    return {
        "request_type": "score-update-request",
        "score_update_template": {
            **target,
            "score": {
                "stance": None,
                "evidence_discipline": None,
                "boundary_clarity": None,
                "useful_recommendation": None,
                "change_condition": None,
                "scope_and_tool_discipline": None,
                "tone_and_collaboration": None,
                "total": None,
                "notes": "",
            },
        },
        "packet": {
            "score_update_target": target,
        },
    }


class RunScoringRequestsTests(unittest.TestCase):
    def write_requests(self, path):
        path.write_text(json.dumps(sample_request()) + "\n", encoding="utf-8")

    def run_runner(self, *args, check=True):
        return subprocess.run(
            [sys.executable, str(RUNNER), *args],
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def test_dry_run_lists_missing_score_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            requests = Path(tmp) / "requests.jsonl"
            updates = Path(tmp) / "updates.jsonl"
            self.write_requests(requests)

            result = self.run_runner(
                "--requests",
                str(requests),
                "--updates",
                str(updates),
                "--compact-events",
            )

            [event] = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(event["mode"], "dry-run")
            self.assertEqual(event["target"]["scenario_id"], "FI-01")
            self.assertTrue(event["command"][-1].startswith("<prompt omitted:"))

    def test_execute_appends_update_and_resume_skips_existing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            requests = tmp_path / "requests.jsonl"
            updates = tmp_path / "updates.jsonl"
            self.write_requests(requests)
            fake_codex = tmp_path / "fake_codex.py"
            fake_codex.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import json",
                        "import sys",
                        "from pathlib import Path",
                        "output = Path(sys.argv[sys.argv.index('--output-last-message') + 1])",
                        "update = {",
                        "  'scenario_id': 'FI-01',",
                        "  'score_type': 'individual',",
                        "  'configuration': 'baseline-positive',",
                        "  'score': {",
                        "    'stance': 2,",
                        "    'evidence_discipline': 2,",
                        "    'boundary_clarity': 1,",
                        "    'useful_recommendation': 2,",
                        "    'change_condition': 1,",
                        "    'scope_and_tool_discipline': 2,",
                        "    'tone_and_collaboration': 2,",
                        "    'total': 12,",
                        "    'notes': 'test score'",
                        "  }",
                        "}",
                        "output.write_text(json.dumps(update), encoding='utf-8')",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o755)

            self.run_runner(
                "--requests",
                str(requests),
                "--updates",
                str(updates),
                "--codex-bin",
                str(fake_codex),
                "--execute",
            )

            written = [json.loads(line) for line in updates.read_text().splitlines()]
            self.assertEqual(len(written), 1)
            self.assertEqual(written[0]["score"]["total"], 12)

            resume = self.run_runner(
                "--requests",
                str(requests),
                "--updates",
                str(updates),
            )

            self.assertEqual(resume.stdout, "")


if __name__ == "__main__":
    unittest.main()
