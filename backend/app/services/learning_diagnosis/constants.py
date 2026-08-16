SOURCE_TYPES = {
    "ASSIGNMENT",
    "EXAM_WRONG",
    "RANKED_RESULT",
    "SANDBOX",
    "INDEPENDENT_RETEST",
    "GIT",
}

KNOWLEDGE_STATES = {
    "not_started",
    "learning",
    "unstable",
    "mastered",
    "needs_review",
    "insufficient_data",
}

TASK_TYPES = {
    "KNOWLEDGE_REVIEW",
    "GUIDED_PRACTICE",
    "CODING_PRACTICE",
    "INDEPENDENT_RETEST",
}

SANDBOX_STATUSES = {
    "COMPILE_ERROR",
    "RUNTIME_ERROR",
    "TEST_FAILED",
    "TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED",
    "SECURITY_VIOLATION",
    "PASSED",
    "SANDBOX_ERROR",
}

HINT_INDEPENDENCE_WEIGHTS = {
    0: 1.0,
    1: 0.9,
    2: 0.75,
    3: 0.5,
    4: 0.25,
    5: 0.0,
}
