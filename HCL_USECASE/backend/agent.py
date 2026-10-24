from langchain_openai import ChatOpenAI
from tools import search_knowledge_base, get_ticket_and_sla_status, plan_next_steps, execute_ticket_action
from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from llm import get_llm
from langgraph.types import interrupt
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage

class AgentState(TypedDict):
    messages:  Annotated[list, add_messages]
    ticket_id: str | None
    docs:      list           # pre-loaded from ingest
    approved:  bool | None    # HIL decision
    
TOOLS = [
    search_knowledge_base,
    get_ticket_and_sla_status,
    plan_next_steps,
    execute_ticket_action,
]

llm = get_llm()

def supervisor_node(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def hil_node(state: AgentState):
    last = state["messages"][-1].content

    # Pause graph and wait for human input
    decision = interrupt({
        "question": "Approve this action?",
        "context":  last,
    })

    return {"approved": decision.get("approved", False)}


def route_after_hil(state: AgentState):
    return "execute" if state.get("approved") else "supervisor"

tool_node = ToolNode(TOOLS)

INTERRUPT_TOOLS = {"execute_ticket_action", "plan_next_steps"}

def route_after_supervisor(state: AgentState):
    last = state["messages"][-1]

    # No tool call → done
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return "end"

    # Needs human approval for these tools
    if any(tc["name"] in INTERRUPT_TOOLS for tc in last.tool_calls):
        return "hil"

    return "tools"