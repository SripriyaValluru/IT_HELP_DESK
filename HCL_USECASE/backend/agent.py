from langchain_openai import ChatOpenAI
from backend.tools import search_knowledge_base, get_ticket_and_sla_status, plan_next_steps, execute_ticket_action
from typing import Annotated
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Optional
from .llm import get_llm
from langgraph.types import interrupt
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
from .model import ResolutionOutput
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
import sqlite3

class AgentState(TypedDict):
    messages:  Annotated[list, add_messages]
    ticket_id: str | None
    docs:      list           # pre-loaded from ingest
    approved:  bool | None 
    resolution: Optional[ResolutionOutput]
        
TOOLS = [
    search_knowledge_base,
    get_ticket_and_sla_status,
    plan_next_steps,
    execute_ticket_action,
]

llm = get_llm().bind_tools(TOOLS)
parser_llm  = get_llm().with_structured_output(ResolutionOutput)

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
    return "tools" if state.get("approved") else "supervisor"  


def parser_node(state: AgentState):
    """Runs at the end — converts conversation into ResolutionOutput."""
    history = "\n".join(
        m.content for m in state["messages"]
        if hasattr(m, "content") and m.content
    )
    result = parser_llm.invoke(
        f"Based on this IT support conversation, extract the resolution:\n\n{history}"
    )
    return {"resolution": result}

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

def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("tools",      tool_node)
    graph.add_node("hil",        hil_node)
    graph.add_node("parser",     parser_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges("supervisor", route_after_supervisor, {
        "tools": "tools",
        "hil":   "hil",
        "end":   "parser",        # no more tool calls → parse resolution
    })

    graph.add_edge("tools",   "supervisor")
    graph.add_edge("parser",  END)

    graph.add_conditional_edges("hil", route_after_hil, {
        "tools":      "tools",
        "supervisor": "supervisor",
    })
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["hil"]
    )