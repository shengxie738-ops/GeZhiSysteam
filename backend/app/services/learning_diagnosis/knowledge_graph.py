from __future__ import annotations

from .catalog import KNOWLEDGE_POINTS


class KnowledgeGraph:
    def __init__(self, points=None):
        self.points = points or KNOWLEDGE_POINTS

    def resolve_prerequisites(self, knowledge_point_ids: list[str]) -> list[str]:
        result: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str):
            if node in visiting:
                raise ValueError("KNOWLEDGE_GRAPH_CYCLE")
            if node in visited:
                return
            visiting.add(node)
            for prerequisite in self.points.get(node, {}).get("prerequisites", []):
                visit(prerequisite)
            visiting.remove(node)
            visited.add(node)
            result.append(node)

        for node in knowledge_point_ids:
            visit(node)
        return result
