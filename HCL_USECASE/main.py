"""FastAPI main application - IT Helpdesk with LangGraph agents."""

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from backend.ingest import load_vector_store
from backend.model import ChatRequest, ResolutionOutput, AgentResponse, QueryRequest, HILRequest
from backend.llm import get_llm
from backend.tools import search_knowledge_base
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage, HumanMessage
import uuid


class AgentState(TypedDict):
    messages: list
    ticket_id: str | None
    docs: list
    approved: bool | None


def build_graph():
    """Build a simple LangGraph for the helpdesk agent."""
    llm = get_llm()

    def supervisor_node(state: AgentState):
        """Process the user query and decide next step."""
        messages = state.get("messages", [])
        if not messages:
            return {"messages": [AIMessage(content="Please provide a query.")]}

        response = llm.invoke(messages)
        return {"messages": [response]}

    def knowledge_node(state: AgentState):
        """Search the knowledge base for relevant info."""
        last_msg = state["messages"][-1]
        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        try:
            results = search_knowledge_base(query)
            return {
                "messages": [
                    AIMessage(content=f"Found relevant info:\n{results}")
                ]
            }
        except Exception as e:
            return {
                "messages": [
                    AIMessage(content=f"Knowledge search failed: {e}")
                ]
            }

    # Build the graph
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("knowledge", knowledge_node)

    # Simple routing: supervisor -> knowledge -> end
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", "knowledge")
    workflow.add_edge("knowledge", END)

    return workflow.compile()


# Global graph instance
_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("Application starting")
    global _graph
    load_vector_store()
    _graph = build_graph()
    print("✅ Graph compiled and ready")
    yield
    print("Application shutting down")


app = FastAPI(
    title="IT Help Desk",
    description="IT Helpdesk Multiagent System with Ollama + LangGraph",
    version="1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "message": "Application is healthy"}


@app.post("/chat", response_model=ResolutionOutput)
async def chat(request: ChatRequest):
    """Process a chat request through the agent graph."""
    if _graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialized")

    try:
        initial_state = {
            "messages": [HumanMessage(content=request.query)],
            "ticket_id": None,
            "docs": [],
            "approved": None,
        }

        result = _graph.invoke(initial_state)

        # Get the last message content
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        else:
            answer = "No response generated."

        return ResolutionOutput(
            resolution_summary=answer,
            agent_first_reply=answer[:200] if len(answer) > 200 else answer,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")


@app.post("/ask", response_model=ResolutionOutput)
async def ask(request: ChatRequest):
    """Simple ask endpoint - alias for /chat."""
    return await chat(request)