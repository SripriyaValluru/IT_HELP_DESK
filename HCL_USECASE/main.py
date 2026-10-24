#main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from backend.ingest import load_vector_store
from backend.model import ChatRequest, ResolutionOutput


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting")
    load_vector_store()
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

@app.post("/chat", response_model=ResolutionOutput)
async def chat(request: ChatRequest):
    return {
        "resolution_summary":"Status Ok"
    }