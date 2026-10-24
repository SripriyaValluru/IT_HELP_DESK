"""Streamlit UI for IT Helpdesk AI - connects to HCL_USECASE FastAPI backend."""

import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="IT Helpdesk AI",
    page_icon="🎫",
    layout="centered",
)

st.title("🎫 IT Helpdesk AI")
st.caption("Ollama + LangGraph + FastAPI")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.subheader("Settings")
    api_url = st.text_input("FastAPI URL", value=API_BASE_URL)
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.markdown("### Status")
    try:
        resp = requests.get(f"{api_url}/health", timeout=5)
        if resp.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API error")
    except Exception as e:
        st.error(f"❌ Cannot connect: {e}")

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

    # Get response from API
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{api_url}/chat",
                    json={"query": prompt},
                    timeout=120,
                )
                if resp.status_code == 200:
                    answer = resp.json().get("resolution_summary", "No answer")
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
                error_msg = "Request timed out."
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