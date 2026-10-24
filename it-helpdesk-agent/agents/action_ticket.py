from __future__ import annotations

"""Action/ticket agent stub that simulates IT ticket creation."""


def create_ticket(summary: str, priority: str = "medium") -> dict[str, str]:
    return {
        "ticket_id": "MOCK-IT-001",
        "summary": summary,
        "priority": priority,
        "status": "created_mock",
        "notes": "This operation is intentionally mocked for the initial workflow build.",
    }
