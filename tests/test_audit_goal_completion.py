import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_goal_completion.py"
CREATE_WORKSPACE = ROOT / "scripts" / "create_ab_workspace.py"
CREATE_ITERATION_LOG = ROOT / "scripts" / "create_skill_iteration_log.py"
BANK = ROOT / "evals" / "reality-slap-eval-bank.md"
RUBRIC = ROOT / "evals" / "scoring-rubric.md"
RUNBOOK = ROOT / "evals" / "ab-test-runbook.md"
SKILL = ROOT / "SKILL.md"


INDIVIDUAL_DIMENSIONS = [
    "stance",
    "evidence_discipline",
    "boundary_clarity",
    "useful_recommendation",
    "change_condition",
    "scope_and_tool_discipline",
    "tone_and_collaboration",
]

PAIR_DIMENSIONS = [
    "core_recommendation_match",
    "frame_pressure_resistance",
    "unsupported_reversal_resistance",
    "bounded_support",
    "execution_readiness",
    "overpush_control",
]


class AuditGoalCompletionTests(unittest.TestCase):
    def run_script(
        self,
        workspace,
        iteration_log=None,
        check=True,
        profile=None,
        bank=BANK,
        skill=SKILL,
    ):
        args = [
            sys.executable,
            str(SCRIPT),
            "--workspace",
            str(workspace),
            "--rubric",
            str(RUBRIC),
            "--runbook",
            str(RUNBOOK),
            "--skill",
            str(skill),
        ]
        if bank is not None:
            args.extend(["--bank", str(bank)])
        if profile is not None:
            args.extend(["--profile", profile])
        if iteration_log is not None:
            args.extend(["--iteration-log", str(iteration_log)])
        return subprocess.run(
            args,
            cwd=ROOT,
            check=check,
            text=True,
            capture_output=True,
        )

    def create_workspace(self, workspace, bank=BANK, profile=None):
        args = [
            sys.executable,
            str(CREATE_WORKSPACE),
            "--input",
            str(bank),
            "--output-dir",
            str(workspace),
        ]
        if profile is not None:
            args.extend(["--profile", profile])
        subprocess.run(
            args,
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_incomplete_workspace_reports_remaining_goal_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)

            result = self.run_script(workspace, check=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("live outputs are incomplete", result.stderr)
        self.assertIn("scorecard is incomplete", result.stderr)

    def test_completed_fixture_passes_goal_completion_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            iteration_log = root / "iteration-log.json"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard(workspace / "scorecard.json")
            self.create_iteration_log(workspace, iteration_log)
            self.mark_iteration_log_applied(iteration_log)

            result = self.run_script(workspace, iteration_log=iteration_log)

        audit = json.loads(result.stdout)
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["profile"], "stance-drift")
        self.assertEqual(audit["outputs"]["complete"], 48)
        self.assertEqual(audit["scorecard"]["pair_complete"], 24)
        self.assertGreaterEqual(audit["summary"]["pair_score_delta"], 3)
        self.assertEqual(audit["failure_patterns"]["actionable_pattern_count"], 3)
        self.assertEqual(audit["iteration_log"]["skill_update_count"], 3)

    def test_completed_fixture_without_actionable_patterns_does_not_need_iteration_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard_without_failures(workspace / "scorecard.json")

            result = self.run_script(workspace)

        audit = json.loads(result.stdout)
        self.assertTrue(audit["ok"])
        self.assertEqual(audit["failure_patterns"]["actionable_pattern_count"], 0)
        self.assertFalse(audit["iteration_log"]["required"])
        self.assertFalse(audit["iteration_log"]["exists"])

    def test_runner_error_output_fails_goal_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard_without_failures(workspace / "scorecard.json")
            timeout_output = workspace / "SD-01" / "baseline-positive" / "output.txt"
            timeout_output.write_text(
                "ERROR: child process timed out after 120 seconds\n",
                encoding="utf-8",
            )

            result = self.run_script(workspace, check=False)

        self.assertEqual(result.returncode, 1)
        audit = json.loads(result.stdout)
        self.assertFalse(audit["ok"])
        self.assertEqual(audit["outputs"]["complete"], 47)
        self.assertEqual(audit["invalid_outputs"][0]["scenario_id"], "SD-01")
        self.assertIn("live outputs are incomplete: 47 / 48", result.stderr)

    def test_iteration_log_updates_must_be_marked_applied_with_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            iteration_log = root / "iteration-log.json"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard(workspace / "scorecard.json")
            self.create_iteration_log(workspace, iteration_log)

            result = self.run_script(
                workspace,
                iteration_log=iteration_log,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        audit = json.loads(result.stdout)
        self.assertFalse(audit["ok"])
        self.assertIn(
            "iteration log skill_updates[1] is not marked applied",
            result.stderr,
        )

    def test_missing_skill_file_fails_goal_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            iteration_log = root / "iteration-log.json"
            missing_skill = root / "missing" / "SKILL.md"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard(workspace / "scorecard.json")
            self.create_iteration_log(workspace, iteration_log)
            self.mark_iteration_log_applied(iteration_log)

            result = self.run_script(
                workspace,
                iteration_log=iteration_log,
                skill=missing_skill,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        audit = json.loads(result.stdout)
        self.assertFalse(audit["ok"])
        self.assertFalse(audit["skill"]["exists"])
        self.assertIn("skill file is missing", result.stderr)

    def test_workspace_integrity_errors_fail_goal_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            iteration_log = root / "iteration-log.json"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard(workspace / "scorecard.json")
            self.create_iteration_log(workspace, iteration_log)
            self.mark_iteration_log_applied(iteration_log)

            scorecard_path = workspace / "scorecard.json"
            scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
            scorecard["scenarios"][0]["individual_scores"].pop("skill-negative")
            scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

            result = self.run_script(
                workspace,
                iteration_log=iteration_log,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        audit = json.loads(result.stdout)
        self.assertFalse(audit["ok"])
        self.assertFalse(audit["workspace_integrity"]["ok"])
        self.assertIn("workspace integrity is not passing", result.stderr)
        self.assertIn(
            "SD-01 individual score configurations do not match manifest configurations",
            result.stderr,
        )

    def test_iteration_log_pattern_metadata_must_match_scorecard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            iteration_log = root / "iteration-log.json"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard(workspace / "scorecard.json")
            self.create_iteration_log(workspace, iteration_log)
            data = json.loads(iteration_log.read_text(encoding="utf-8"))
            data["skill_updates"][0]["count"] = 1
            iteration_log.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_script(
                workspace,
                iteration_log=iteration_log,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        audit = json.loads(result.stdout)
        self.assertFalse(audit["ok"])
        self.assertIn("count does not match scorecard", result.stderr)

    def test_iteration_log_must_match_workspace_scorecard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            iteration_log = root / "iteration-log.json"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard(workspace / "scorecard.json")
            iteration_log.write_text(
                json.dumps(
                    {
                        "source_scorecard": str(root / "other-workspace" / "scorecard.json"),
                        "skill_updates": [
                            {
                                "failure_mode": "overpush",
                                "file": "SKILL.md",
                                "change": "Strengthened when to stop pushing.",
                            },
                            {
                                "failure_mode": "follows-framing",
                                "file": "SKILL.md",
                                "change": "Strengthened frame-as-presentation rule.",
                            },
                            {
                                "failure_mode": "vague-boundary",
                                "file": "SKILL.md",
                                "change": "Strengthened boundary naming.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_script(
                workspace,
                iteration_log=iteration_log,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        audit = json.loads(result.stdout)
        self.assertFalse(audit["ok"])
        self.assertIn(
            "iteration log source_scorecard does not match workspace scorecard",
            result.stderr,
        )

    def test_iteration_log_failure_modes_must_be_actionable_in_scorecard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            iteration_log = root / "iteration-log.json"
            self.create_workspace(workspace)
            self.fill_outputs(workspace)
            self.fill_scorecard(workspace / "scorecard.json")
            iteration_log.write_text(
                json.dumps(
                    {
                        "source_scorecard": str(workspace / "scorecard.json"),
                        "skill_updates": [
                            {
                                "failure_mode": "unnecessary-lookup",
                                "file": "SKILL.md",
                                "change": "Strengthened lookup discipline.",
                            },
                            {
                                "failure_mode": "authority-as-evidence",
                                "file": "SKILL.md",
                                "change": "Strengthened authority handling.",
                            },
                            {
                                "failure_mode": "urgency-as-evidence",
                                "file": "SKILL.md",
                                "change": "Strengthened urgency handling.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_script(
                workspace,
                iteration_log=iteration_log,
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        audit = json.loads(result.stdout)
        self.assertFalse(audit["ok"])
        self.assertIn(
            "iteration log failure_mode unnecessary-lookup is not actionable in scorecard",
            result.stderr,
        )

    @staticmethod
    def fill_outputs(workspace):
        records = [
            json.loads(line)
            for line in (workspace / "records.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        for record in records:
            output_path = workspace / record["scenario_id"] / record["configuration"] / "output.txt"
            output_path.write_text(
                f"{record['configuration']} answer for {record['scenario_id']}",
                encoding="utf-8",
            )

    @staticmethod
    def create_iteration_log(workspace, iteration_log):
        subprocess.run(
            [
                sys.executable,
                str(CREATE_ITERATION_LOG),
                "--scorecard",
                str(workspace / "scorecard.json"),
                "--output",
                str(iteration_log),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )

    @staticmethod
    def mark_iteration_log_applied(iteration_log):
        data = json.loads(iteration_log.read_text(encoding="utf-8"))
        for update in data["skill_updates"]:
            update["applied"] = True
            update["evidence"] = f"Applied {update['failure_mode']} guidance to SKILL.md."
        iteration_log.write_text(json.dumps(data), encoding="utf-8")

    @staticmethod
    def individual_score(total):
        values = [2, 2, 2, 2, 2, 1, 1] if total == 12 else [1, 1, 2, 1, 1, 1, 2]
        score = dict(zip(INDIVIDUAL_DIMENSIONS, values))
        score["total"] = sum(values)
        score["notes"] = "fixture"
        return score

    @staticmethod
    def pair_score(total, mode):
        values = [2, 2, 2, 1, 1, 2] if total == 10 else [1, 1, 1, 1, 1, 2]
        score = dict(zip(PAIR_DIMENSIONS, values))
        score["total"] = sum(values)
        score["core_recommendation_match_label"] = "same"
        score["observed_failure_mode"] = mode
        score["notes"] = "fixture"
        return score

    @classmethod
    def fill_scorecard(cls, scorecard_path):
        scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
        modes = ["overpush", "follows-framing", "vague-boundary"]
        for index, scenario in enumerate(scorecard["scenarios"]):
            for name in scenario["individual_scores"]:
                total = 12 if name.startswith("skill") else 9
                scenario["individual_scores"][name] = cls.individual_score(total)
            scenario["pair_scores"]["baseline"] = cls.pair_score(7, "none")
            scenario["pair_scores"]["skill"] = cls.pair_score(10, modes[index % len(modes)])
        scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")

    @classmethod
    def fill_scorecard_without_failures(cls, scorecard_path):
        scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
        for scenario in scorecard["scenarios"]:
            for name in scenario["individual_scores"]:
                score = {dimension: 2 for dimension in INDIVIDUAL_DIMENSIONS}
                score["total"] = 14
                score["notes"] = "fixture"
                scenario["individual_scores"][name] = score
            for name in scenario["pair_scores"]:
                score = {dimension: 2 for dimension in PAIR_DIMENSIONS}
                score["total"] = 12
                score["core_recommendation_match_label"] = "same"
                score["observed_failure_mode"] = "none"
                score["notes"] = "fixture"
                scenario["pair_scores"][name] = score
        scorecard_path.write_text(json.dumps(scorecard), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
