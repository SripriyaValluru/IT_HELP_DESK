#pydantic models

from pydantic import BaseModel, field_validator , Field
from typing import Optional, Enum

class ChatRequest(BaseModel):
    query : str
    
    @field_validator('query')
    @classmethod
    def validate(cls, value):
        if not value or not value.strip():
            raise ValueError("messasge is empty!")
        
        if len(value) > 1000:
            raise ValueError("Keep the message under 1000 characters")
        
        return value.strip()
    
class ResolutionOutput(BaseModel):
    # The primary mandatory output summarizing the resolution
    resolution_summary: str = Field(
        description="A concise summary of how the customer's query was resolved."
    )
    
    # The optional field, which defaults to None if not generated
    agent_first_reply: Optional[str] = Field(
        default=None,
        description="The initial response sent by the agent to the customer, if applicable."
    )
    

class TicketSLAStatus(BaseModel):
    ticket_id:          str
    customer_id:        str
    priority:           str
    status:             str
    sla_plan:           str
    sla_resolution_due: str
    sla_breached:       bool
    time_open_hours:    float
    customer_sentiment: str
    recommended_action: str
    escalate:           bool
    
class NextStepPlan(BaseModel):
    reasoning:       str        
    next_steps:      list[str]  
    policy_applied:  list[str] 
    assigned_to:     str       
    requires_approval: bool
    
class TicketAction(str, Enum):
    CREATE   = "create"
    UPDATE   = "update"
    ESCALATE = "escalate"
    RESOLVE  = "resolve"


# --- Schemas ---

class ActionRequest(BaseModel):
    action:       TicketAction
    ticket_id:    str | None = None  
    customer_id:  str
    issue_type:   str
    priority:     str
    product_area: str
    notes:        str                


class ActionResult(BaseModel):
    action_taken:      str
    ticket_id:         str
    status:            str
    assigned_to:       str
    resolution_notes:  str
    timestamp:         str
    success:           bool
    
class QueryRequest(BaseModel):
    thread_id: str
    message:   str
    ticket_id: str | None = None


class HILRequest(BaseModel):
    thread_id: str
    approved:  bool


class AgentResponse(BaseModel):
    thread_id:   str
    response:    str
    paused:      bool          # True if waiting for HIL
    next_nodes:  list[str]
