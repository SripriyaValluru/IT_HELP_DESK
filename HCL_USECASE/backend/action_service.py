from datetime import datetime, timezone
import uuid
from model import ActionRequest, ActionResult, TicketAction
from ingest import _load_store, _save_store


def _generate_ticket_id() -> str:
    return f"TKT-{str(uuid.uuid4())[:6].upper()}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assign_to(priority: str, issue_type: str) -> str:
    if priority == "critical":
        return "L2"
    if issue_type in ("account_locked", "mfa_issue"):
        return "L1-IAM"
    if issue_type == "billing":
        return "finance"
    return "L1"


# --- Actions ---

def _create_ticket(req: ActionRequest) -> ActionResult:
    store     = _load_store()
    ticket_id = _generate_ticket_id()
    assigned  = _assign_to(req.priority, req.issue_type)

    store[ticket_id] = {
        "ticket_id":        ticket_id,
        "created_at":       _timestamp(),
        "customer_id":      req.customer_id,
        "customer_segment": None,
        "channel":          None,
        "product_area":     req.product_area,
        "issue_type":       req.issue_type,
        "priority":         req.priority,
        "status":           "open",
        "sla_plan":         None,
        "initial_message":  req.notes,
        "agent_first_reply":     None,
        "resolution_summary":    None,
        "resolution_time_hours": None,
        "reopened":              False,
        "customer_sentiment":    None,
        "csat_score":            None,
        "has_attachment":        False,
        "platform":              None,
        "region":                None,
        "eval_split":            None,
        "scenario_key":          None,
        "assigned_to":           assigned,
    }
    _save_store(store)

    return ActionResult(
        action_taken     = "ticket_created",
        ticket_id        = ticket_id,
        status           = "open",
        assigned_to      = assigned,
        resolution_notes = req.notes,
        timestamp        = _timestamp(),
        success          = True,
    )


def _update_ticket(req: ActionRequest) -> ActionResult:
    store  = _load_store()
    ticket = store.get(req.ticket_id)

    if not ticket:
        return ActionResult(
            action_taken     = "update_failed",
            ticket_id        = req.ticket_id,
            status           = "not_found",
            assigned_to      = "unknown",
            resolution_notes = f"Ticket {req.ticket_id} not found.",
            timestamp        = _timestamp(),
            success          = False,
        )

    ticket["status"]   = "in_progress"
    ticket["priority"] = req.priority
    ticket["agent_first_reply"] = req.notes
    _save_store(store)

    return ActionResult(
        action_taken     = "ticket_updated",
        ticket_id        = req.ticket_id,
        status           = "in_progress",
        assigned_to      = ticket.get("assigned_to", "L1"),
        resolution_notes = req.notes,
        timestamp        = _timestamp(),
        success          = True,
    )


def _escalate_ticket(req: ActionRequest) -> ActionResult:
    store     = _load_store()
    ticket    = store.get(req.ticket_id)
    new_level = "L3" if ticket and ticket.get("assigned_to") == "L2" else "L2"

    if ticket:
        ticket["assigned_to"] = new_level
        ticket["status"]      = "escalated"
        _save_store(store)

    return ActionResult(
        action_taken     = "ticket_escalated",
        ticket_id        = req.ticket_id or _generate_ticket_id(),
        status           = "escalated",
        assigned_to      = new_level,
        resolution_notes = f"Escalated — reason: {req.notes}",
        timestamp        = _timestamp(),
        success          = True,
    )


def _resolve_ticket(req: ActionRequest) -> ActionResult:
    store  = _load_store()
    ticket = store.get(req.ticket_id)

    if not ticket:
        return ActionResult(
            action_taken     = "resolve_failed",
            ticket_id        = req.ticket_id,
            status           = "not_found",
            assigned_to      = "unknown",
            resolution_notes = f"Ticket {req.ticket_id} not found.",
            timestamp        = _timestamp(),
            success          = False,
        )

    ticket["status"]             = "resolved"
    ticket["resolution_summary"] = req.notes
    ticket["resolution_time_hours"] = round(
        (datetime.now(timezone.utc) - datetime.fromisoformat(
            ticket["created_at"]
        ).replace(tzinfo=timezone.utc)).total_seconds() / 3600, 2
    )
    _save_store(store)

    return ActionResult(
        action_taken     = "ticket_resolved",
        ticket_id        = req.ticket_id,
        status           = "resolved",
        assigned_to      = ticket.get("assigned_to", "L1"),
        resolution_notes = req.notes,
        timestamp        = _timestamp(),
        success          = True,
    )


# --- Dispatch ---

ACTION_MAP = {
    TicketAction.CREATE:   _create_ticket,
    TicketAction.UPDATE:   _update_ticket,
    TicketAction.ESCALATE: _escalate_ticket,
    TicketAction.RESOLVE:  _resolve_ticket,
}