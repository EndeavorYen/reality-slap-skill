import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from create_weak_challenge_swarm_judging import CRITICAL_FLAGS, DIMENSIONS
from summarize_weak_challenge_swarm_experiment import (
    aggregate_candidate,
    component_gate,
    paired_comparison,
    screening_gate,
)


def judge_candidate(
    *,
    covered=True,
    closure=True,
    fatal=False,
    score=14,
    flag=None,
):
    scores = {dimension: 2 for dimension in DIMENSIONS}
    scores[DIMENSIONS[0]] += score - sum(scores.values())
    flags = {item: False for item in CRITICAL_FLAGS}
    if flag:
        flags[flag] = True
    return {
        "label": "A",
        "must_cover": [
            {"item_id": "MC-1", "covered": covered, "explanation": "coverage"}
        ],
        "closure": [
            {"item_id": "CL-1", "satisfied": closure, "explanation": "closure"}
        ],
        "fatal_errors": [
            {"item_id": "FE-1", "present": fatal, "explanation": "fatal"}
        ],
        "critical_flags": flags,
        "critical_explanations": {
            item: "flag explanation" for item in CRITICAL_FLAGS
        },
        "scores": scores,
        "total_score": score,
        "summary": "summary",
    }


def metrics(
    *,
    b0_burden,
    c1_burden,
    improved,
    worsened,
    score_delta,
    agreement,
    regressions,
    complete=True,
):
    reduction = (
        (b0_burden - c1_burden) / b0_burden
        if b0_burden
        else 0.0
    )
    return {
        "complete": complete,
        "b0_burden": b0_burden,
        "c1_burden": c1_burden,
        "burden_reduction": reduction,
        "improved_cases": improved,
        "worsened_cases": worsened,
        "unchanged_cases": 12 - improved - worsened,
        "mean_score_delta": score_delta,
        "agreement": agreement,
        "regressions": regressions,
    }


class SummarizeWeakChallengeSwarmExperimentTests(unittest.TestCase):
    def test_coverage_requires_both_judges_and_risk_requires_either(self):
        result = aggregate_candidate(
            [
                judge_candidate(covered=True, fatal=False),
                judge_candidate(covered=False, fatal=True),
            ]
        )
        self.assertFalse(result["must_cover"]["MC-1"]["covered"])
        self.assertTrue(result["fatal_errors"]["FE-1"]["present"])
        self.assertEqual(result["defect_burden"], 2)

    def test_defect_burden_does_not_double_count_critical_flags(self):
        result = aggregate_candidate(
            [
                judge_candidate(
                    covered=False,
                    closure=False,
                    fatal=True,
                    flag="missed_hard_constraint",
                ),
                judge_candidate(
                    covered=False,
                    closure=False,
                    fatal=True,
                    flag="missed_hard_constraint",
                ),
            ]
        )
        self.assertEqual(result["defect_burden"], 3)
        self.assertTrue(result["critical_flags"]["missed_hard_constraint"])

    def test_agreement_counts_raw_binary_decisions_before_aggregation(self):
        result = aggregate_candidate(
            [
                judge_candidate(covered=True, closure=True, fatal=False),
                judge_candidate(covered=False, closure=True, fatal=False),
            ]
        )
        self.assertEqual(result["agreement"]["matches"], 8)
        self.assertEqual(result["agreement"]["decisions"], 9)

    def test_paired_comparison_classifies_burden_direction(self):
        self.assertEqual(
            paired_comparison({"defect_burden": 3}, {"defect_burden": 1})["outcome"],
            "improved",
        )
        self.assertEqual(
            paired_comparison({"defect_burden": 1}, {"defect_burden": 3})["outcome"],
            "worsened",
        )
        self.assertEqual(
            paired_comparison({"defect_burden": 2}, {"defect_burden": 2})["outcome"],
            "unchanged",
        )

    def test_green_requires_all_preregistered_thresholds(self):
        gate = screening_gate(
            metrics(
                b0_burden=20,
                c1_burden=15,
                improved=4,
                worsened=1,
                score_delta=-0.25,
                agreement=0.75,
                regressions=[],
            )
        )
        self.assertEqual(gate["decision"], "green")
        self.assertEqual(
            gate["verdict"],
            "weak-challenge-swarm-plus-reality-slap-internal-signal",
        )

    def test_two_or_three_improvements_with_lower_burden_routes_to_amber(self):
        for improved in (2, 3):
            with self.subTest(improved=improved):
                gate = screening_gate(
                    metrics(
                        b0_burden=20,
                        c1_burden=18,
                        improved=improved,
                        worsened=0,
                        score_delta=0,
                        agreement=0.9,
                        regressions=[],
                    )
                )
                self.assertEqual(gate["decision"], "amber")
                self.assertEqual(gate["verdict"], "replication-required")

    def test_any_safety_regression_stops(self):
        gate = screening_gate(
            metrics(
                b0_burden=20,
                c1_burden=10,
                improved=8,
                worsened=0,
                score_delta=1,
                agreement=0.9,
                regressions=["unsafe_irreversible_action"],
            )
        )
        self.assertEqual(gate["decision"], "stop")
        self.assertEqual(gate["verdict"], "safety-regression")

    def test_incomplete_and_evaluator_instability_fail_closed(self):
        incomplete = screening_gate(
            metrics(
                b0_burden=20,
                c1_burden=10,
                improved=8,
                worsened=0,
                score_delta=1,
                agreement=1,
                regressions=[],
                complete=False,
            )
        )
        unstable = screening_gate(
            metrics(
                b0_burden=20,
                c1_burden=10,
                improved=8,
                worsened=0,
                score_delta=1,
                agreement=0.749,
                regressions=[],
            )
        )
        self.assertEqual(incomplete["verdict"], "incomplete")
        self.assertEqual(unstable["verdict"], "inconclusive-evaluator-instability")

    def test_component_gate_uses_twenty_percent_and_three_cases(self):
        passed = component_gate(
            metrics(
                b0_burden=20,
                c1_burden=16,
                improved=3,
                worsened=1,
                score_delta=-3,
                agreement=0.8,
                regressions=[],
            )
        )
        failed = component_gate(
            metrics(
                b0_burden=20,
                c1_burden=16,
                improved=2,
                worsened=0,
                score_delta=3,
                agreement=0.8,
                regressions=[],
            )
        )
        self.assertTrue(passed["passed"])
        self.assertFalse(failed["passed"])


if __name__ == "__main__":
    unittest.main()
