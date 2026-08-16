KNOWLEDGE_POINTS = {
    "linked_list_structure": {"name": "链表结构", "prerequisites": [], "difficulty": 1},
    "pointer_reference": {"name": "指针引用", "prerequisites": ["linked_list_structure"], "difficulty": 2},
    "linked_list_boundary": {"name": "链表边界条件", "prerequisites": ["linked_list_structure", "pointer_reference"], "difficulty": 2},
    "linked_list_delete": {"name": "链表删除操作", "prerequisites": ["linked_list_boundary"], "difficulty": 3},
}

TASK_TEMPLATES = {
    "linked-list-review": {"title": "知识回顾 · 链表边界条件", "task_type": "KNOWLEDGE_REVIEW", "difficulty": 1, "minutes": 8},
    "linked-list-guided": {"title": "引导练习 · 安全处理空链表", "task_type": "GUIDED_PRACTICE", "difficulty": 2, "minutes": 15},
    "linked-list-coding": {"title": "编程实践 · 完成删除函数", "task_type": "CODING_PRACTICE", "difficulty": 3, "minutes": 20},
    "linked-list-retest": {"title": "独立复测 · 多边界场景变式题", "task_type": "INDEPENDENT_RETEST", "difficulty": 3, "minutes": 20},
}
