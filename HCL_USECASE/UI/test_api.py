"""Test script to verify the FastAPI Qwen endpoint works."""

import sys
import requests

BASE_URL = "http://localhost:8000"


def test_root():
    """Test the root endpoint."""
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"GET / -> {resp.status_code}")
        print(resp.json())
        return resp.status_code == 200
    except Exception as e:
        print(f"GET / failed: {e}")
        return False


def test_health():
    """Test the health endpoint."""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=30)
        print(f"GET /health -> {resp.status_code}")
        print(resp.json())
        return resp.status_code == 200
    except Exception as e:
        print(f"GET /health failed: {e}")
        return False


def test_ask():
    """Test the ask endpoint."""
    payload = {
        "question": "Reply with exactly: Qwen connection successful",
    }
    try:
        resp = requests.post(f"{BASE_URL}/ask", json=payload, timeout=60)
        print(f"POST /ask -> {resp.status_code}")
        if resp.status_code == 200:
            print(resp.json())
            return True
        else:
            print(resp.text)
            return False
    except Exception as e:
        print(f"POST /ask failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing FastAPI Qwen endpoints...\n")
    ok1 = test_root()
    print()
    ok2 = test_health()
    print()
    ok3 = test_ask()
    print()
    if ok1 and ok2 and ok3:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1)