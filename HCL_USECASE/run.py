"""Run script for HCL_USECASE FastAPI + Streamlit."""

import subprocess
import sys
import time
import os


def main():
    print("=" * 60)
    print("IT Helpdesk AI - HCL_USECASE")
    print("=" * 60)

    # Set working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Start FastAPI
    print("\n[1/2] Starting FastAPI backend on http://localhost:8000...")
    api_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
        ],
    )

    # Wait for API
    print("Waiting for API to start...")
    time.sleep(3)

    # Verify
    try:
        import requests
        resp = requests.get("http://localhost:8000/health", timeout=10)
        if resp.status_code == 200:
            print("✅ FastAPI backend is running")
        else:
            print("⚠️  API started but health check failed")
    except Exception as e:
        print(f"⚠️  Could not verify API: {e}")

    # Start Streamlit
    print("\n[2/2] Starting Streamlit UI on http://localhost:8501...")
    print("\n" + "=" * 60)
    print("Services running! Press Ctrl+C to stop")
    print("  - FastAPI: http://localhost:8000")
    print("  - Streamlit UI: http://localhost:8501")
    print("  - API Docs: http://localhost:8000/docs")
    print("=" * 60 + "\n")

    streamlit_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "ui.py",
            "--server.port",
            "8501",
        ],
    )

    try:
        api_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        api_process.terminate()
        streamlit_process.terminate()
        api_process.wait()
        streamlit_process.wait()
        print("Services stopped.")


if __name__ == "__main__":
    main()