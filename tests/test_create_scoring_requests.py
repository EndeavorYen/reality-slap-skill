import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_WORKSPACE = ROOT / "scripts" / "create_ab_workspace.py"
REQUESTS = ROOT / "scripts" / "create_scoring_requests.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"


class CreateScoringRequestsTests(unittest.TestCase):
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
                "FI-01",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def run_script(self, workspace, *args):
        return subprocess.run(
            [sys.executable, str(REQUESTS), "--workspace", str(workspace), *args],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_individual_request_contains_apply_score_update_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.write_output(workspace, "FI-01", "skill-positive", "skill answer")

            result = self.run_script(workspace, "--kind", "individual")

        requests = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(requests), 1)
        request = requests[0]
        template = request["score_update_template"]

        self.assertEqual(request["request_type"], "score-update-request")
        self.assertIn("Return exactly one JSON object", request["scorer_instruction"])
        self.assertIn("Do not read repo, memory, or web", request["scorer_instruction"])
        self.assertEqual(request["provenance"]["workspace"], str(workspace))
        self.assertEqual(request["provenance"]["scorecard"], str(workspace / "scorecard.json"))
        self.assertEqual(request["rubric_context"]["source"], "evals/scoring-rubric.md")
        self.assertEqual(request["rubric_context"]["score_scale"]["max"], 2)
        self.assertIn("stance", request["rubric_context"]["dimension_guidance"])
        self.assertIn(
            "scope_and_tool_discipline",
            request["rubric_context"]["dimension_guidance"],
        )
        self.assertEqual(template["scenario_id"], "FI-01")
        self.assertEqual(template["score_type"], "individual")
        self.assertEqual(template["configuration"], "skill-positive")
        self.assertIn("stance", template["score"])
        self.assertIn("tone_and_collaboration", template["score"])
        self.assertIsNone(template["score"]["total"])
        self.assertEqual(request["packet"]["output"], "skill answer")

    def test_pair_request_contains_pair_dimensions_and_failure_mode_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.write_output(workspace, "FI-01", "baseline-positive", "baseline yes")
            self.write_output(workspace, "FI-01", "baseline-negative", "baseline no")
            self.write_output(workspace, "FI-01", "skill-positive", "skill yes")
            self.write_output(workspace, "FI-01", "skill-negative", "skill no")

            result = self.run_script(workspace, "--kind", "pair")

        requests = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(requests), 2)
        baseline = requests[0]["score_update_template"]
        skill = requests[1]["score_update_template"]

        self.assertEqual(baseline["configuration"], "baseline")
        self.assertEqual(skill["configuration"], "skill")
        self.assertIn("core_recommendation_match", skill["score"])
        self.assertIn("execution_readiness", skill["score"])
        self.assertIn("overpush_control", skill["score"])
        self.assertIn("core_recommendation_match_label", skill["score"])
        self.assertIn("observed_failure_mode", skill["score"])
        self.assertIsNone(skill["score"]["total"])
        self.assertIn(
            "unsupported-reversal",
            requests[1]["rubric_context"]["failure_modes"],
        )
        self.assertIn("none", requests[1]["rubric_context"]["failure_modes"])
        self.assertIn(
            "core_recommendation_match",
            requests[1]["rubric_context"]["dimension_guidance"],
        )

    def test_blind_pair_requests_hide_condition_identity_and_write_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            mapping_path = Path(tmp) / "blind-map.json"
            self.create_workspace(workspace)
            self.write_output(workspace, "FI-01", "baseline-positive", "baseline yes")
            self.write_output(workspace, "FI-01", "baseline-negative", "baseline no")
            self.write_output(workspace, "FI-01", "skill-positive", "skill yes")
            self.write_output(workspace, "FI-01", "skill-negative", "skill no")

            result = self.run_script(
                workspace,
                "--kind",
                "pair",
                "--blind",
                "--mapping-output",
                str(mapping_path),
            )
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

        requests = [json.loads(line) for line in result.stdout.splitlines()]
        request_text = json.dumps(requests, sort_keys=True)

        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["request_type"], "blind-score-update-request")
        self.assertEqual(requests[0]["blind_score_update_template"]["blind_id"], "blind-0001")
        self.assertNotIn("score_update_template", requests[0])
        self.assertNotIn("configuration", requests[0]["packet"])
        self.assertNotIn("Use $reality-slap", request_text)
        self.assertNotIn("Do not use $reality-slap", request_text)
        self.assertNotIn('"baseline"', request_text)
        self.assertNotIn('"skill"', request_text)
        self.assertEqual(mapping["entries"][0]["blind_id"], "blind-0001")
        self.assertEqual(
            mapping["entries"][0]["score_update_target"],
            {
                "scenario_id": "FI-01",
                "score_type": "pair",
                "configuration": "baseline",
            },
        )

    @staticmethod
    def write_output(workspace, scenario_id, configuration, text):
        path = workspace / scenario_id / configuration / "output.txt"
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
