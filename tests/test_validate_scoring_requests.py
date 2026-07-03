import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKSPACE = ROOT / "scripts" / "create_ab_workspace.py"
CREATE_REQUESTS = ROOT / "scripts" / "create_scoring_requests.py"
VALIDATE_REQUESTS = ROOT / "scripts" / "validate_scoring_requests.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class ValidateScoringRequestsTests(unittest.TestCase):
    def create_workspace(self, workspace):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_WORKSPACE),
                "--input",
                str(BANK),
                "--output-dir",
                str(workspace),
                "--scenario",
                "SD-01",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def create_requests(self, workspace):
        result = subprocess.run(
            [sys.executable, str(CREATE_REQUESTS), "--workspace", str(workspace)],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        return [json.loads(line) for line in result.stdout.splitlines()]

    def create_blind_requests(self, workspace, mapping_path):
        result = subprocess.run(
            [
                sys.executable,
                str(CREATE_REQUESTS),
                "--workspace",
                str(workspace),
                "--kind",
                "pair",
                "--blind",
                "--mapping-output",
                str(mapping_path),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        return [json.loads(line) for line in result.stdout.splitlines()]

    def run_validator(self, workspace, requests, *args):
        with tempfile.TemporaryDirectory() as tmp:
            requests_path = Path(tmp) / "scoring-requests.jsonl"
            requests_path.write_text(
                "".join(json.dumps(request) + "\n" for request in requests),
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_REQUESTS),
                    "--workspace",
                    str(workspace),
                    "--requests",
                    str(requests_path),
                    *args,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

    def run_blind_validator(self, workspace, requests, mapping_path, *args):
        with tempfile.TemporaryDirectory() as tmp:
            requests_path = Path(tmp) / "blind-scoring-requests.jsonl"
            requests_path.write_text(
                "".join(json.dumps(request) + "\n" for request in requests),
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    sys.executable,
                    str(VALIDATE_REQUESTS),
                    "--workspace",
                    str(workspace),
                    "--requests",
                    str(requests_path),
                    "--blind",
                    "--mapping",
                    str(mapping_path),
                    *args,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

    def test_complete_scoring_requests_cover_completed_outputs_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            requests = self.create_requests(workspace)

            result = self.run_validator(workspace, requests)

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["expected_requests"], 6)
        self.assertEqual(report["provided_requests"], 6)
        self.assertEqual(report["missing_request_count"], 0)
        self.assertEqual(report["duplicate_request_count"], 0)
        self.assertEqual(report["unknown_request_count"], 0)

    def test_missing_duplicate_and_unknown_request_targets_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            requests = self.create_requests(workspace)
            requests.pop(0)
            requests.append(requests[-1])
            unknown = dict(requests[-1])
            unknown["score_update_template"] = dict(
                unknown["score_update_template"],
                configuration="missing",
            )
            unknown["packet"] = dict(
                unknown["packet"],
                score_update_target={
                    "scenario_id": "SD-01",
                    "score_type": "pair",
                    "configuration": "missing",
                },
            )
            requests.append(unknown)

            result = self.run_validator(workspace, requests)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["missing_request_count"], 1)
        self.assertEqual(report["duplicate_request_count"], 1)
        self.assertEqual(report["unknown_request_count"], 1)
        self.assertIn("missing scoring request SD-01 individual baseline-positive", result.stderr)
        self.assertIn("duplicate scoring request SD-01 pair skill", result.stderr)
        self.assertIn("unknown scoring request SD-01 pair missing", result.stderr)

    def test_template_and_packet_target_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            requests = self.create_requests(workspace)
            requests[0]["score_update_template"]["configuration"] = "skill-positive"

            result = self.run_validator(workspace, requests)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("template target does not match packet target", result.stderr)

    def test_missing_rubric_context_and_wrong_workspace_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            other_workspace = Path(tmp) / "other-workspace"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            requests = self.create_requests(workspace)
            requests[0].pop("rubric_context")
            requests[1]["provenance"] = dict(
                requests[1]["provenance"],
                workspace=str(other_workspace),
            )

            result = self.run_validator(workspace, requests)

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("rubric_context must be an object", result.stderr)
        self.assertIn("provenance.workspace does not match", result.stderr)

    def test_complete_blind_scoring_requests_match_mapping_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            mapping_path = Path(tmp) / "blind-map.json"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            requests = self.create_blind_requests(workspace, mapping_path)

            result = self.run_blind_validator(
                workspace,
                requests,
                mapping_path,
                "--kind",
                "pair",
            )

        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["expected_requests"], 2)
        self.assertEqual(report["provided_requests"], 2)
        self.assertEqual(report["covered_requests"], 2)

    def test_blind_scoring_requests_missing_mapping_entry_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            mapping_path = Path(tmp) / "blind-map.json"
            self.create_workspace(workspace)
            self.complete_all_outputs(workspace)
            requests = self.create_blind_requests(workspace, mapping_path)
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            mapping["entries"].pop(0)
            mapping_path.write_text(json.dumps(mapping), encoding="utf-8")

            result = self.run_blind_validator(
                workspace,
                requests,
                mapping_path,
                "--kind",
                "pair",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("unknown blind scoring request blind-0001", result.stderr)

    @staticmethod
    def complete_all_outputs(workspace):
        for output in workspace.glob("*/**/output.txt"):
            output.write_text("done", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
