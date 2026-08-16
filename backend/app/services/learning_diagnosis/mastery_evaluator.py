from __future__ import annotations

from typing import Any

from .constants import HINT_INDEPENDENCE_WEIGHTS


class MasteryEvaluator:
    def independence_weight(self, highest_hint_level: int) -> float:
        return HINT_INDEPENDENCE_WEIGHTS.get(max(0, min(int(highest_hint_level), 5)), 0.0)

    def evaluate(self, evidence: dict[str, Any], base_score: float) -> dict[str, Any]:
        independent_passed = bool(evidence.get("independent_retest_passed"))
        coverage = set(evidence.get("coverage") or set())
        highest_hint_level = int(evidence.get("highest_hint_level", 0))
        enough_coverage = {"NORMAL", "BOUNDARY", "EXCEPTION"}.issubset(coverage)
        if independent_passed and enough_coverage and highest_hint_level <= 1 and base_score >= 85:
            state = "mastered"
        elif base_score < 45:
            state = "learning"
        elif independent_passed or highest_hint_level <= 2:
            state = "unstable"
        else:
            state = "learning"
        return {
            "mastery_score": round(max(0.0, min(float(base_score), 100.0)), 2),
            "state": state,
            "independent_retest_passed": independent_passed,
            "independent_retest_coverage": sorted(coverage),
            "highest_hint_level": highest_hint_level,
        }
