"""Setup and run script for the FastAPI Qwen service."""

import os
import subprocess
import sys
import time


def check_ollama():
    """Check if Ollama is installed and running."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        return resp.status_code == 200
    except:
        return False


def start_ollama():
    """Try to start Ollama in the background."""
    print("Starting Ollama...")
    try:
        # Start ollama serve in background
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for it to start
        for i in range(10):
            time.sleep(1)
            if check_ollama():
                print("Ollama started successfully.")
                return True
        print("Ollama failed to start within 10 seconds.")
        return False
    except FileNotFoundError:
        print("Ollama executable not found. Please install Ollama first:")
        print("  winget install Ollama.Ollama")
        print("  or download from https://ollama.com/download")
        return False


def install_qwen():
    """Install the Qwen model if not present."""
    print("Checking for Qwen model...")
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        qwen_models = [m for m in models if "qwen" in m.get("name", "").lower()]
        if qwen_models:
            print(f"Found Qwen models: {[m['name'] for m in qwen_models]}")
            return qwen_models[0]["name"]
    except:
        pass
    
    print("No Qwen model found. Pulling qwen2.5:7b (this may take a while)...")
    try:
        subprocess.run(["ollama", "pull", "qwen2.5:7b"], check=True)
        return "qwen2.5:7b"
    except Exception as e:
        print(f"Failed to pull Qwen model: {e}")
        return None


def main():
    import requests
    
    print("=" * 50)
    print("IT Helpdesk FastAPI Setup")
    print("=" * 50)
    
    # Step 1: Check/start Ollama
    if not check_ollama():
        print("\n[1/3] Ollama not running. Attempting to start...")
        if not start_ollama():
            print("\nPlease start Ollama manually:")
            print("  ollama serve")
            sys.exit(1)
    else:
        print("\n[1/3] Ollama is running.")
    
    # Step 2: Install Qwen model
    print("\n[2/3] Checking Qwen model...")
    model = install_qwen()
    if not model:
        print("Failed to install Qwen model.")
        sys.exit(1)
    print(f"Using model: {model}")
    
    # Step 3: Start FastAPI
    print("\n[3/3] Starting FastAPI server...")
    print("Server will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop.\n")
    
    # Set environment variable
    os.environ["OLLAMA_MODEL"] = model
    
    # Start the FastAPI server
    import uvicorn
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()