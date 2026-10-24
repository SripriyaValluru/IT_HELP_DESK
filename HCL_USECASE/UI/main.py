"""Streamlit UI for IT Helpdesk AI - connects to FastAPI backend with session management."""

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "helpdesk.db"

st.set_page_config(
    page_title="IT Helpdesk AI",
    page_icon="🎫",
    layout="wide",
)

st.title("🎫 IT Helpdesk AI")
st.caption("Local Qwen + Ollama + FastAPI | Session-aware + SQLite tickets")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "user_id" not in st.session_state:
    st.session_state.user_id = "demo-user"


# Database helpers
def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            user_id TEXT,
            subject TEXT,
            description TEXT,
            status TEXT,
            priority TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def create_ticket(subject: str, description: str, priority: str = "medium") -> str:
    init_db()
    ticket_id = f"HD-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tickets (ticket_id, user_id, subject, description, status, priority, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (ticket_id, st.session_state.user_id, subject, description, "open", priority, now, now),
    )
    conn.commit()
    conn.close()
    return ticket_id


def get_ticket(ticket_id: str) -> dict | None:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


# Sidebar
with st.sidebar:
    st.subheader("Session")
    st.text_input("User ID", value=st.session_state.user_id, disabled=True)
    st.text_input("Conversation Thread ID", value=st.session_state.thread_id, disabled=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("New Conversation"):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    st.markdown("---")
    st.subheader("Settings")
    api_url = st.text_input("FastAPI URL", value=API_BASE_URL)

    st.markdown("---")
    st.markdown("### Backend Status")
    try:
        resp = requests.get(f"{api_url}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok":
                st.success(f"✅ Connected: {data.get('model', 'unknown')}")
            else:
                st.error(f"❌ Error: {data.get('detail', 'unknown')}")
        else:
            st.error("❌ API not reachable")
    except Exception as e:
        st.error(f"❌ Cannot connect: {e}")

    st.markdown("---")
    st.caption("Tip: Use same Thread ID for multi-turn context. LangGraph checkpointer uses this.")

# Tabs
tab_chat, tab_tickets = st.tabs(["💬 Chat", "🎫 Tickets (SQLite)"])

# Chat tab
with tab_chat:
    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Describe your IT issue..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get response from API with session context
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "question": prompt,
                        "user_id": st.session_state.user_id,
                        "thread_id": st.session_state.thread_id,
                    }
                    resp = requests.post(
                        f"{api_url}/ask",
                        json=payload,
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("answer") or data.get("response") or "No answer"
                        st.markdown(answer)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer}
                        )
                    else:
                        error_msg = f"Error {resp.status_code}: {resp.text}"
                        st.error(error_msg)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": error_msg}
                        )
                except requests.exceptions.Timeout:
                    error_msg = "Request timed out. The model may be slow on first run."
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )
                except Exception as e:
                    error_msg = f"Connection error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": error_msg}
                    )

# Tickets tab
with tab_tickets:
    st.subheader("Mock Ticket Management (SQLite)")
    st.caption(f"DB: {DB_PATH}")

    col_create, col_lookup = st.columns(2)

    with col_create:
        st.markdown("### Create Ticket")
        with st.form("create_ticket_form", clear_on_submit=True):
            subject = st.text_input("Subject", placeholder="e.g. Cannot access VPN")
            description = st.text_area("Description", placeholder="Describe the issue in detail...")
            priority = st.selectbox("Priority", ["low", "medium", "high", "critical"], index=1)
            submitted = st.form_submit_button("Create Ticket")
            if submitted:
                if not subject.strip():
                    st.error("Subject is required")
                else:
                    tid = create_ticket(subject.strip(), description.strip(), priority)
                    st.success(f"Created ticket: {tid}")
                    st.code(tid)

    with col_lookup:
        st.markdown("### Lookup Ticket Status")
        with st.form("lookup_ticket_form"):
            lookup_id = st.text_input("Ticket ID", placeholder="HD-XXXXXXXX")
            lookup_submitted = st.form_submit_button("Lookup")
            if lookup_submitted and lookup_id.strip():
                ticket = get_ticket(lookup_id.strip().upper())
                if ticket is None:
                    st.error("Ticket not found")
                else:
                    st.json(ticket)
