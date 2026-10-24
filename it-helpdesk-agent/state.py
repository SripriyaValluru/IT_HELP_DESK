from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HelpdeskState:
    """Shared state for the multi-agent IT helpdesk workflow."""

    question: str = ""
    route: str = "knowledge_search"
    relevant_tickets: list[dict[str, Any]] = field(default_factory=list)
    access_decision: str = "pending"
    ticket: dict[str, Any] | None = None
    final_answer: str = ""
