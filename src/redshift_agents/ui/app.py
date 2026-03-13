"""
Redshift Modernization Chat UI — Streamlit app.

Connects to the orchestrator agent via Bedrock AgentCore InvokeAgent API
and provides a conversational interface for the 3-phase modernization workflow.

Authenticates users via Amazon Cognito before granting access to the chat.

Run with:
    cd src/redshift_agents
    streamlit run ui/app.py
"""
from __future__ import annotations

import json
import os
import uuid

from dotenv import load_dotenv

# Load .env BEFORE any other imports that read env vars
load_dotenv()

import boto3
import streamlit as st

from auth import (
    cognito_sign_in,
    create_authenticated_session,
    extract_user_id,
    refresh_tokens,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ORCHESTRATOR_AGENT_ID = os.getenv(
    "ORCHESTRATOR_AGENT_ID", "redshift-orchestrator"
)
ORCHESTRATOR_AGENT_ALIAS_ID = os.getenv(
    "ORCHESTRATOR_AGENT_ALIAS_ID", "TSTALIASID"
)
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Redshift Modernization",
    page_icon="🚀",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        max-width: 900px;
        margin: 0 auto;
    }
    .status-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .phase-active { background: #dbeafe; color: #1e40af; }
    .phase-done { background: #dcfce7; color: #166534; }
    .phase-pending { background: #f3f4f6; color: #6b7280; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_id" not in st.session_state:
    st.session_state.user_id = ""

if "configured" not in st.session_state:
    st.session_state.configured = False

# Auth tokens
if "id_token" not in st.session_state:
    st.session_state.id_token = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "boto3_session" not in st.session_state:
    st.session_state.boto3_session = None
if "password_challenge" not in st.session_state:
    st.session_state.password_challenge = None
if "challenge_username" not in st.session_state:
    st.session_state.challenge_username = None
if "challenge_password" not in st.session_state:
    st.session_state.challenge_password = None


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _do_sign_in(username: str, password: str, new_password: str | None = None) -> bool:
    """Attempt Cognito sign-in. Returns True on success."""
    try:
        tokens = cognito_sign_in(username, password, new_password=new_password)

        # Handle NEW_PASSWORD_REQUIRED challenge
        if tokens.get("challenge") == "NEW_PASSWORD_REQUIRED":
            st.session_state.password_challenge = tokens["session"]
            st.session_state.challenge_username = username
            st.session_state.challenge_password = password
            return False

        st.session_state.password_challenge = None
        st.session_state.id_token = tokens["id_token"]
        st.session_state.access_token = tokens["access_token"]
        st.session_state.refresh_token = tokens["refresh_token"]
        st.session_state.user_id = extract_user_id(tokens["id_token"])
        st.session_state.authenticated = True

        # Exchange JWT for temporary AWS credentials
        session = create_authenticated_session(tokens["id_token"])
        st.session_state.boto3_session = session
        return True
    except Exception as e:
        st.error(f"Sign-in failed: {e}")
        return False


def _do_token_refresh() -> bool:
    """Attempt to refresh tokens. Returns True on success, False on failure."""
    if not st.session_state.refresh_token:
        return False
    try:
        new_tokens = refresh_tokens(st.session_state.refresh_token)
        st.session_state.id_token = new_tokens["id_token"]
        st.session_state.access_token = new_tokens["access_token"]
        st.session_state.user_id = extract_user_id(new_tokens["id_token"])

        # Refresh Identity Pool credentials too
        session = create_authenticated_session(new_tokens["id_token"])
        st.session_state.boto3_session = session
        return True
    except Exception:
        # Refresh failed — force re-login
        _sign_out()
        return False


def _sign_out():
    """Clear all auth state."""
    st.session_state.id_token = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_id = ""
    st.session_state.authenticated = False
    st.session_state.boto3_session = None
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Bedrock AgentCore client
# ---------------------------------------------------------------------------


def invoke_orchestrator(message: str, user_id: str) -> str:
    """Send a message to the orchestrator and return the response."""
    # Use Identity Pool credentials if available, else default
    session = st.session_state.boto3_session or boto3
    client = session.client("bedrock-agent-runtime", region_name=AWS_REGION)

    # Build the input with identity propagation — user_id from Cognito JWT
    input_text = json.dumps({
        "message": message,
        "user_id": user_id,
    })

    try:
        response = client.invoke_agent(
            agentId=ORCHESTRATOR_AGENT_ID,
            agentAliasId=ORCHESTRATOR_AGENT_ALIAS_ID,
            sessionId=st.session_state.session_id,
            inputText=input_text,
        )

        # Stream the response
        result_text = ""
        if "completion" in response:
            for event in response["completion"]:
                if "chunk" in event:
                    chunk_bytes = event["chunk"].get("bytes", b"")
                    result_text += chunk_bytes.decode("utf-8", errors="replace")

        return result_text if result_text else "No response from orchestrator."

    except client.exceptions.ResourceNotFoundException:
        return (
            "⚠️ Orchestrator agent not found. Make sure you've deployed the agents "
            "with `cdk deploy` and set the `ORCHESTRATOR_AGENT_ID` "
            "environment variable."
        )
    except Exception as e:
        error_msg = str(e)
        # If token expired, attempt refresh
        if "expired" in error_msg.lower() or "token" in error_msg.lower():
            if _do_token_refresh():
                return invoke_orchestrator(message, user_id)
        return f"⚠️ Error communicating with orchestrator: {error_msg}"


# ---------------------------------------------------------------------------
# Sign-in form (shown when not authenticated)
# ---------------------------------------------------------------------------

if not st.session_state.authenticated:
    st.title("🚀 Redshift Modernization")

    # Show "set new password" form if challenge is active
    if st.session_state.password_challenge:
        st.caption("Please set a new password")
        with st.form("new_password_form"):
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Set Password", use_container_width=True)

            if submitted:
                if not new_password or not confirm_password:
                    st.warning("Please fill in both fields.")
                elif new_password != confirm_password:
                    st.warning("Passwords don't match.")
                else:
                    _do_sign_in(
                        st.session_state.challenge_username,
                        st.session_state.challenge_password,
                        new_password=new_password,
                    )
                    if st.session_state.authenticated:
                        st.rerun()
    else:
        st.caption("Sign in to get started")
        with st.form("sign_in_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if username and password:
                    _do_sign_in(username, password)
                    if st.session_state.authenticated:
                        st.rerun()
                    elif st.session_state.password_challenge:
                        st.rerun()
                else:
                    st.warning("Please enter both username and password.")

    st.stop()


# ---------------------------------------------------------------------------
# Sidebar — configuration (authenticated)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Configuration")

    st.markdown(f"**Signed in as:** `{st.session_state.user_id}`")

    st.divider()

    st.caption(f"Agent: `{ORCHESTRATOR_AGENT_ID}`")
    st.caption(f"Region: `{AWS_REGION}`")
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.button("🚪 Sign Out", use_container_width=True):
            _sign_out()
            st.rerun()

    st.divider()

    st.markdown("### Workflow Phases")
    st.markdown(
        """
        1. 🔍 **Assessment** — Cluster analysis & WLM contention
        2. 🏗️ **Architecture** — Workgroup design & RPU sizing
        3. 🚀 **Execution** — Create resources & migrate

        Approval gates between each phase.
        """
    )


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

st.title("🚀 Redshift Modernization")
st.caption("Migrate your Redshift Provisioned cluster to Serverless")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Describe your modernization request..."):
    # user_id is always from Cognito JWT — cannot be overridden
    user_id = st.session_state.user_id

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get orchestrator response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = invoke_orchestrator(prompt, user_id)
        st.markdown(response)

    # Add assistant message
    st.session_state.messages.append({"role": "assistant", "content": response})


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

if not st.session_state.messages:
    st.markdown("---")
    st.markdown("### Getting Started")
    st.markdown(
        f"""
        You're signed in as **{st.session_state.user_id}**. Try one of these:

        - *"Modernize my Redshift cluster `prod-cluster-01` in `us-east-2`"*
        - *"List all Redshift clusters in my account"*
        - *"I want to migrate cluster `analytics-dw` to Serverless"*

        The orchestrator will guide you through assessment, architecture design,
        and execution — with approval gates at each step.
        """
    )
