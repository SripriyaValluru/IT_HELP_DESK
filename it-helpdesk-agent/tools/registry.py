from __future__ import annotations

from typing import Any

from agents.knowledge_search import find_relevant_tickets


def knowledge_search_tool(question: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the top matching support tickets for a user question."""
    return find_relevant_tickets(question, limit=limit)
