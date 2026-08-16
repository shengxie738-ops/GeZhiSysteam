from __future__ import annotations

from collections import defaultdict
from typing import Any

from .constants import SANDBOX_STATUSES
from .mastery_evaluator import MasteryEvaluator


class RuleEngine:
    def assess(
        self,
        evidence_records,
        knowledge_point_ids: list[str],
        include_git_evidence: bool = False,
    ) -> dict[str, dict[str, Any]]:
        buckets: dict[str, list[Any]] = defaultdict(list)
        for record in evidence_records:
            for knowledge_point_id in record.knowledge_point_ids:
                if knowledge_point_id in knowledge_point_ids:
                    buckets[knowledge_point_id].append(record)

        evaluator = MasteryEvaluator()
        results: dict[str, dict[str, Any]] = {}
        for knowledge_point_id in knowledge_point_ids:
            records = buckets.get(knowledge_point_id, [])
            valid: list[Any] = []
            failed_cases: set[str] = set()
            scores: list[float] = []
            weighted_scores: list[tuple[float, float]] = []
            practice_scores: list[tuple[float, float]] = []
            reason_codes: list[str] = []
            independent_passed = False
            independent_coverage: set[str] = set()
            highest_hint_level = 0
            for record in records:
                status = str(record.result.get("status", ""))
                if record.source_type == "SANDBOX" and status == "SANDBOX_ERROR":
                    continue
                valid.append(record)
                hint_level = int(record.result.get("hint_level", 0) or 0)
                highest_hint_level = max(highest_hint_level, hint_level)
                weight = evaluator.independence_weight(hint_level)
                if record.source_type == "INDEPENDENT_RETEST" or record.result.get("task_type") == "INDEPENDENT_RETEST":
                    summary_for_retest = record.result.get("test_summary") or record.result.get("testSummary") or {}
                    independent_passed = independent_passed or bool(record.result.get("independent_retest_passed")) or (str(record.result.get("status", "")).upper() == "PASSED" and (not summary_for_retest or summary_for_retest.get("passed") == summary_for_retest.get("total")))
                    independent_coverage.update(str(item).upper() for item in (record.result.get("coverage") or record.result.get("independent_retest_coverage") or []))
                if isinstance(record.result.get("score"), (int, float)):
                    value = float(record.result["score"])
                    scores.append(value)
                    weighted_scores.append((value, weight))
                summary = record.result.get("test_summary") or record.result.get("testSummary") or {}
                total = summary.get("total") or 0
                passed = summary.get("passed") or 0
                if total:
                    value = float(passed) / float(total) * 100
                    scores.append(value)
                    weighted_scores.append((value, weight))
                if record.source_type == "GIT" and include_git_evidence:
                    value = record.result.get("practice_score")
                    if isinstance(value, (int, float)):
                        reliability = float(getattr(record.provenance, "reliability", 1.0) or 1.0)
                        practice_scores.append((float(value), max(0.0, reliability)))
                for case in record.result.get("failed_cases", []):
                    failed_cases.add(str(case))

            if "EMPTY_LIST" in failed_cases:
                reason_codes.append("EMPTY_LIST_FAILED")
            if "SINGLE_NODE" in failed_cases:
                reason_codes.append("SINGLE_NODE_FAILED")
            if not valid:
                results[knowledge_point_id] = {
                    "mastery_score": None,
                    "practice_score": None,
                    "state": "insufficient_data",
                    "confidence": 0.0,
                    "reason_codes": ["INSUFFICIENT_EVIDENCE"],
                    "evidence_count": 0,
                    "failed_cases": sorted(failed_cases),
                }
                continue
            denominator = sum(weight for _, weight in weighted_scores)
            mastery = round(sum(value * weight for value, weight in weighted_scores) / denominator, 2) if denominator else None
            evaluated = evaluator.evaluate({"independent_retest_passed": independent_passed, "coverage": independent_coverage, "highest_hint_level": highest_hint_level}, mastery or 0) if mastery is not None else {"state": "insufficient_data", "independent_retest_passed": False, "independent_retest_coverage": [], "highest_hint_level": highest_hint_level}
            state = "unstable" if failed_cases and evaluated.get("state") == "needs_review" else evaluated.get("state", "learning")
            practice_denominator = sum(weight for _, weight in practice_scores)
            practice_score = (
                round(sum(value * weight for value, weight in practice_scores) / practice_denominator, 2)
                if practice_scores and practice_denominator and include_git_evidence
                else None
            )
            if mastery is None and practice_score is not None:
                state = "learning"
                reason_codes.append("MASTERY_EVIDENCE_INSUFFICIENT")
            results[knowledge_point_id] = {
                "mastery_score": mastery,
                "practice_score": practice_score,
                "state": state,
                "confidence": min(1.0, round(0.55 + len(valid) * 0.1 + (0.1 if independent_passed else 0), 2)),
                "reason_codes": reason_codes,
                "evidence_count": len(valid),
                "failed_cases": sorted(failed_cases),
                "evidence_refs": [record.evidence_id for record in valid],
                "independent_retest_passed": bool(evaluated.get("independent_retest_passed", independent_passed)),
                "independent_retest_coverage": list(evaluated.get("independent_retest_coverage", sorted(independent_coverage))),
                "highest_hint_level": int(evaluated.get("highest_hint_level", highest_hint_level)),
            }
        return results
