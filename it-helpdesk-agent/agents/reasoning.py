from __future__ import annotations

"""Reasoning agent stub for diagnosing the issue and deciding the next action."""


def reason_about_issue(question: str, relevant_tickets: list[dict]) -> dict[str, object]:
    return {
        "question": question,
        "candidate_tickets": relevant_tickets[:3],
        "recommended_action": "triage",
        "summary": "This is a placeholder reasoning step.",
    }
