from __future__ import annotations

"""Policy checks for access approval and routing decisions."""


def requires_approval(action: str) -> bool:
    """Only access-related actions require approval in this initial workflow."""
    return action.lower() in {"grant_access", "reset_password", "approve_admin_access"}
