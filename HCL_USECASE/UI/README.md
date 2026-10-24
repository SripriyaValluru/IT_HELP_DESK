# IT Helpdesk FastAPI Service

A FastAPI service that connects to Qwen via Ollama and returns answers.

## Prerequisites

1. **Ollama installed** - Download from https://ollama.com/download
2. **Qwen model installed** - Run `ollama pull qwen2.5:7b`

## Quick Start

### Option 1: Use the setup script (Recommended)

```bash
cd UI
python setup_and_run.py
```

This will:
- Check if Ollama is running (start it if needed)
- Pull the Qwen model if not installed
- Start the FastAPI server

### Option 2: Manual start

1. **Start Ollama** (if not running):
   ```bash
   ollama serve
   ```

2. **Pull Qwen model** (if not installed):
   ```bash
   ollama pull qwen2.5:7b
   ```

3. **Start the FastAPI server**:
   ```bash
   cd UI
   uvicorn fastapi_app:app --reload --port 8000
   ```

## API Endpoints

### GET /
Root endpoint - returns service info.

### GET /health
Health check - verifies Ollama connection.

### POST /ask
Send a question to Qwen.

**Request body:**
```json
{
  "question": "Your question here",
  "system_prompt": "Optional system prompt"
}
```

**Response:**
```json
{
  "answer": "Qwen's response",
  "model": "qwen2.5:7b"
}
```

## Test the API

```bash
python test_api.py
```

Or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello, how are you?"}'
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

Set environment variables to customize:

```bash
$env:OLLAMA_MODEL = "qwen2.5:7b"  # Model name
$env:OLLAMA_BASE_URL = "http://localhost:11434"  # Ollama URL
```