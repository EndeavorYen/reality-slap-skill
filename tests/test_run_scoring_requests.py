import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_scoring_requests.py"


def sample_request(scenario_id="FI-01", configuration="baseline-positive"):
    target = {
        "scenario_id": scenario_id,
        "score_type": "individual",
        "configuration": configuration,
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

    def write_multiple_requests(self, path):
        requests = [
            sample_request("FI-01", "baseline-positive"),
            sample_request("FI-02", "baseline-negative"),
            sample_request("FI-03", "skill-positive"),
        ]
        path.write_text(
            "".join(json.dumps(request) + "\n" for request in requests),
            encoding="utf-8",
        )

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

    def test_execute_jobs_merges_score_updates_in_request_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            requests = tmp_path / "requests.jsonl"
            updates = tmp_path / "updates.jsonl"
            response_dir = tmp_path / "responses"
            self.write_multiple_requests(requests)
            fake_codex = tmp_path / "fake_scorer.py"
            fake_codex.write_text(
                "\n".join(
                    [
                        "#!/usr/bin/env python3",
                        "import json",
                        "import sys",
                        "import time",
                        "from pathlib import Path",
                        "output = Path(sys.argv[sys.argv.index('--output-last-message') + 1])",
                        "prompt = sys.argv[-1]",
                        "request_json = prompt.split('Scoring request JSON:', 1)[1].strip()",
                        "request = json.loads(request_json)",
                        "target = request['score_update_template']",
                        "delays = {'FI-01': 0.30, 'FI-02': 0.10, 'FI-03': 0.20}",
                        "time.sleep(delays[target['scenario_id']])",
                        "update = {",
                        "  'scenario_id': target['scenario_id'],",
                        "  'score_type': target['score_type'],",
                        "  'configuration': target['configuration'],",
                        "  'score': {",
                        "    'stance': 2,",
                        "    'evidence_discipline': 2,",
                        "    'boundary_clarity': 2,",
                        "    'useful_recommendation': 2,",
                        "    'change_condition': 2,",
                        "    'scope_and_tool_discipline': 2,",
                        "    'tone_and_collaboration': 2,",
                        "    'total': 14,",
                        "    'notes': target['scenario_id']",
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
                "--response-dir",
                str(response_dir),
                "--codex-bin",
                str(fake_codex),
                "--execute",
                "--jobs",
                "3",
            )

            written = [json.loads(line) for line in updates.read_text().splitlines()]
            self.assertEqual(
                [update["scenario_id"] for update in written],
                ["FI-01", "FI-02", "FI-03"],
            )
            self.assertEqual(len(list(response_dir.glob("*.json"))), 3)


if __name__ == "__main__":
    unittest.main()
