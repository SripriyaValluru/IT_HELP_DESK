#main.py

from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from backend.ingest import load_vector_store, _load_docs
from backend.model import ChatRequest, ResolutionOutput,QueryRequest, HILRequest, AgentResponse
from backend.agent import build_agent, ResolutionOutput

docs = None
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global docs, agent
    print("Application starting")
    load_vector_store()
    docs = _load_docs()
    agent = build_agent()
    yield
    print("Application shutting down")
    
    
app = FastAPI(
    title="IT Help Desk",
    description="IT Helpdesk Multiagent System with Open Telemetry",
    version="1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins= ["*"],
    allow_methods= ["*"],
    allow_headers=["*"]
)

@app.get("/health")
def health():
    return {"status":"ok", "message":"Application is healty"}

@app.post("/chat", response_model=AgentResponse)
async def chat(request: QueryRequest):
    from langchain_core.messages import HumanMessage

    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        state = agent.invoke(
            {
                "messages":   [HumanMessage(content=request.message.query)],
                "docs":       docs,
                "approved":   None,
                "resolution": None,    # ← initialize resolution as None
            },
            config=config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    current_state = agent.get_state(config)
    next_nodes    = list(current_state.next)

    return AgentResponse(
        thread_id  = request.thread_id,
        resolution = state.get("resolution"),   # ← None if paused, filled if done
        paused     = "hil" in next_nodes,
        next_nodes = next_nodes,
    )
    
@app.post("/approve", response_model=AgentResponse)
async def approve(req: HILRequest):
    config        = {"configurable": {"thread_id": req.thread_id}}
    current_state = agent.get_state(config)

    # Guard: only call this if actually paused
    if "hil" not in current_state.next:
        raise HTTPException(
            status_code=400,
            detail="No HIL checkpoint pending for this thread."
        )

    try:
        state = agent.invoke(
            {"approved": req.approved},   # ← resume with decision
            config=config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    current_state = agent.get_state(config)
    next_nodes    = list(current_state.next)

    return AgentResponse(
        thread_id  = req.thread_id,
        resolution = state.get("resolution"),   # ← populated after parser_node runs
        paused     = "hil" in next_nodes,
        next_nodes = next_nodes,
    )