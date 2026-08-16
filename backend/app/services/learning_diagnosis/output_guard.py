from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass
class GuardResult:
    allowed: bool
    reason_codes: list[str] = field(default_factory=list)


class AnswerLeakageGuard:
    _complete_code = re.compile(r"class\s+\w+\s*\{|def\s+\w+\s*\(|public\s+static\s+void\s+main", re.I)
    _secret = re.compile(r"api[_ -]?key|token|password|system prompt|hidden test", re.I)

    def inspect(self, text: str, hint_level: int) -> GuardResult:
        reasons: list[str] = []
        if hint_level < 5 and self._complete_code.search(text):
            reasons.append("COMPLETE_CODE")
        if self._secret.search(text):
            reasons.append("SENSITIVE_OR_INTERNAL_CONTENT")
        return GuardResult(allowed=not reasons, reason_codes=reasons)
