"""FastAPI service that connects to Qwen via Ollama and returns answers."""

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from langchain_ollama import ChatOllama
from pydantic import BaseModel

MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

app = FastAPI(title="IT Helpdesk Qwen API")


class QuestionRequest(BaseModel):
    question: str
    system_prompt: Optional[str] = None


class AnswerResponse(BaseModel):
    answer: str
    model: str


def get_llm() -> ChatOllama:
    """Create a ChatOllama instance connected to the local Qwen model."""
    return ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )


@app.get("/")
async def root():
    return {"message": "IT Helpdesk Qwen API", "model": MODEL_NAME}


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Send a question to Qwen and return the answer."""
    try:
        llm = get_llm()
        system_prompt = request.system_prompt or (
            "You are a helpful IT support assistant. Provide clear, concise answers."
        )
        messages = [
            ("system", system_prompt),
            ("human", request.question),
        ]
        response = llm.invoke(messages)
        return AnswerResponse(answer=response.content, model=MODEL_NAME)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM request failed: {exc}")


@app.get("/health")
async def health():
    """Check if Ollama is reachable."""
    try:
        llm = get_llm()
        # Simple test invoke to verify connection
        llm.invoke("ping")
        return {"status": "ok", "model": MODEL_NAME, "base_url": OLLAMA_BASE_URL}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)