from langchain_core.tools import tool
from backend.ingest import retrieve_relevant_chunks
from backend.model import TicketSLAStatus, NextStepPlan, ActionResult, ActionRequest
from datetime import datetime, timedelta, timezone
from backend.ingest import _load_docs
from backend.llm import get_llm
from backend.config import system_prompt, POLICY_RULES
from langchain_core.messages import SystemMessage, HumanMessage
from backend.action_service import ACTION_MAP, _timestamp

SLA_MATRIX = {
    "premium":  {"critical": 4,  "high": 8,  "medium": 16, "low": 48},
    "standard": {"critical": 8,  "high": 24, "medium": 48, "low": 96},
}

@tool()
def search_knowledge_base(query: str):
    """
    Parses, searches, and resolves IT help desk queries using the knowledge base.

    This tool acts as an automated service desk assistant. It ingests natural 
    language technical problems or account inquiries from users, retrieves relevant 
    troubleshooting documentation, and extracts a structured resolution plan.

    It is designed to handle common enterprise IT support scenarios including, 
    but not limited to:
    - Identity & Access Management (e.g., "I am not able to login", "Account locked")
    - Multi-Factor Authentication (e.g., "My 2FA token is not working/synced")
    - Financial & Billing Queries (e.g., "My service amount on the invoice is incorrect")
    - Hardware/Software Troubleshooting (e.g., VPN drops, printer issues, software installation)

    Args:
        user_query (str): The raw, natural language issue description or question 
            submitted by the end-user (e.g., "Help, my account is locked after 3 attempts").

    Returns:
        ResolutionOutput: A structured Pydantic object containing:
            - resolution_summary (str): The step-by-step technical fix or system action 
              required to resolve the user's issue.
            - agent_first_reply (str, optional): A personalized, empathetic macro or 
              first response draft for the agent to send immediately to the user.

    Raises:
        KnowledgeBaseLookupError: If the search index is unreachable or fails to query.
        ValidationError: If the generated solution fails to conform to the output schema.
    """
    
    if not query:
        raise ValueError("Query can not be empty!")
    
    results = retrieve_relevant_chunks(query)
    
    if not results:
        raise ValueError("No relevant chunks found!")
    
    content = "\n----\n".join(results)
    
    return content

@tool()
def get_ticket_and_sla_status(ticket_id: str) -> TicketSLAStatus:
    """
    Returns SLA status and recommended action for a given ticket ID.
    Looks up ticket metadata from already-loaded documents.

    Args:
        ticket_id (str): The ticket ID to look up (e.g., "TKT-1001").

    Returns:
        TicketSLAStatus: Ticket context, SLA breach status, and recommended action.
    """
    # Find matching ticket from loaded docs
    docs = _load_docs()
    ticket = next(
        (doc.metadata for doc in docs if doc.metadata.get("ticket_id") == ticket_id),
        None
    )

    if not ticket:
        raise ValueError(f"Ticket {ticket_id} not found in loaded documents")

    # Compute SLA
    created_at = datetime.fromisoformat(ticket["created_at"]).replace(tzinfo=timezone.utc)
    resolution_hrs = SLA_MATRIX.get(ticket["sla_plan"], {}).get(ticket["priority"], 48)
    resolution_due = created_at + timedelta(hours=resolution_hrs)
    now = datetime.now(timezone.utc)
    time_open = (now - created_at).total_seconds() / 3600

    sla_breached = (
        ticket["status"] != "resolved"
        and now > resolution_due
    )

    escalate = sla_breached or ticket.get("reopened") or ticket.get("customer_sentiment") == "very_negative"

    action = (
        "Escalate to L2 — SLA breached or ticket reopened."  if escalate else
        "Follow standard resolution flow per knowledge base."
    )

    return TicketSLAStatus(
        ticket_id          = ticket["ticket_id"],
        customer_id        = ticket["customer_id"],
        priority           = ticket["priority"],
        status             = ticket["status"],
        sla_plan           = ticket["sla_plan"],
        sla_resolution_due = resolution_due.isoformat(),
        sla_breached       = sla_breached,
        time_open_hours    = round(time_open, 2),
        customer_sentiment = ticket.get("customer_sentiment", "unknown"),
        recommended_action = action,
        escalate           = escalate,
    )
@tool()
def plan_next_steps(ticket_context: str) -> NextStepPlan:
    """
    Reasoning agent that plans next steps for a support ticket
    after the access-check agent has run.

    Takes the full ticket context (SLA status, account state, sentiment,
    issue type) and reasons over company policy to produce an ordered
    action plan.

    Args:
        ticket_context (str): Serialized output from get_ticket_and_sla_status
                              — paste the full context as a string.

    Returns:
        NextStepPlan: Reasoning trace, ordered next steps, policies triggered,
                      assignment, and approval flag.
    """
    llm = get_llm()

    system_prompt = system_prompt

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Ticket context:\n{ticket_context}")
    ])

    import json
    raw = response.content.strip().removeprefix("```json").removesuffix("```").strip()
    parsed = json.loads(raw)

    return NextStepPlan(**parsed)    

@tool()
def execute_ticket_action(request: ActionRequest) -> ActionResult:
    """
    Action agent that executes ticket operations against the JSON data store.

    Supports four actions:
    - create:   Opens a new ticket and appends it to the JSON file
    - update:   Updates priority, status, and agent notes on existing ticket
    - escalate: Escalates ticket assignment from L1 → L2 → L3
    - resolve:  Marks ticket resolved, writes resolution summary and computes resolution time

    Args:
        request (ActionRequest): Action to perform with ticket context and notes.

    Returns:
        ActionResult: Outcome — ticket ID, status, assignment, notes, and success flag.
    """
    handler = ACTION_MAP.get(request.action)

    if not handler:
        return ActionResult(
            action_taken     = "unknown_action",
            ticket_id        = request.ticket_id or "N/A",
            status           = "failed",
            assigned_to      = "unknown",
            resolution_notes = f"No handler for action: {request.action}",
            timestamp        = _timestamp(),
            success          = False,
        )

    return handler(request)

tools = [
    search_knowledge_base,
    get_ticket_and_sla_status,
    plan_next_steps,
    execute_ticket_action
]