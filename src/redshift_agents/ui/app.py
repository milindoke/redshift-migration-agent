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
ASSESSMENT_AGENT_ID = os.getenv("ASSESSMENT_AGENT_ID", "")
ARCHITECTURE_AGENT_ID = os.getenv("ARCHITECTURE_AGENT_ID", "")
EXECUTION_AGENT_ID = os.getenv("EXECUTION_AGENT_ID", "")
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

if "active_cluster_id" not in st.session_state:
    st.session_state.active_cluster_id = ""

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
    st.session_state.active_cluster_id = ""
    st.session_state.authenticated = False
    st.session_state.boto3_session = None
    st.session_state.messages = []
    st.session_state.session_id = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Bedrock AgentCore client
# ---------------------------------------------------------------------------


def forget_cluster_memory(cluster_id: str) -> str:
    """Delete SESSION_SUMMARY memory for a cluster across all 4 agents."""
    session = st.session_state.boto3_session or boto3
    client = session.client("bedrock-agent-runtime", region_name=AWS_REGION)

    agent_ids = [
        aid for aid in [
            ORCHESTRATOR_AGENT_ID,
            ASSESSMENT_AGENT_ID,
            ARCHITECTURE_AGENT_ID,
            EXECUTION_AGENT_ID,
        ] if aid
    ]

    errors = []
    for agent_id in agent_ids:
        try:
            client.delete_agent_memory(
                agentId=agent_id,
                agentAliasId="TSTALIASID",  # memory is alias-independent but API requires it
                memoryId=cluster_id,
            )
        except Exception as e:
            errors.append(f"{agent_id}: {e}")

    if errors:
        return "⚠️ Some agents could not be cleared:\n" + "\n".join(errors)
    return f"✅ Memory cleared for cluster `{cluster_id}` across all agents."


def _extract_trace_steps(trace_event: dict) -> list[dict]:
    """Pull reasoning steps out of a Bedrock Agent trace event.

    Returns a list of dicts with keys: type, text, (optional) tool, input, output.
    """
    steps = []
    trace = trace_event.get("trace", {})

    # Orchestration trace — reasoning + tool calls
    orch = trace.get("orchestrationTrace", {})

    rationale = orch.get("rationale", {}).get("text", "")
    if rationale:
        steps.append({"type": "reasoning", "text": rationale})

    inv = orch.get("invocationInput", {})
    action_inv = inv.get("actionGroupInvocationInput", {})
    agent_inv = inv.get("agentCollaboratorInvocationInput", {})
    kb_inv = inv.get("knowledgeBaseLookupInput", {})

    if action_inv:
        steps.append({
            "type": "tool_call",
            "tool": action_inv.get("actionGroupName", "") + "/" + action_inv.get("apiPath", ""),
            "input": json.dumps(action_inv.get("requestBody", {}).get("content", {}), indent=2),
        })
    if agent_inv:
        steps.append({
            "type": "agent_call",
            "tool": agent_inv.get("agentCollaboratorName", "sub-agent"),
            "input": agent_inv.get("input", {}).get("text", ""),
        })
    if kb_inv:
        steps.append({
            "type": "kb_lookup",
            "text": kb_inv.get("text", ""),
        })

    obs = orch.get("observation", {})
    action_result = obs.get("actionGroupInvocationOutput", {})
    agent_result = obs.get("agentCollaboratorInvocationOutput", {})
    kb_result = obs.get("knowledgeBaseLookupOutput", {})

    if action_result:
        steps.append({
            "type": "tool_result",
            "output": action_result.get("text", ""),
        })
    if agent_result:
        steps.append({
            "type": "agent_result",
            "tool": agent_result.get("agentCollaboratorName", "sub-agent"),
            "output": agent_result.get("output", {}).get("text", ""),
        })
    if kb_result:
        refs = kb_result.get("retrievedReferences", [])
        snippets = [r.get("content", {}).get("text", "") for r in refs if r.get("content", {}).get("text")]
        if snippets:
            steps.append({
                "type": "kb_result",
                "output": "\n\n---\n\n".join(snippets[:3]),  # cap at 3 snippets
            })

    return steps


def invoke_orchestrator(message: str, user_id: str) -> tuple[str, list[dict]]:
    """Send a message to the orchestrator and return (response_text, trace_steps)."""
    session = st.session_state.boto3_session or boto3
    from botocore.config import Config
    client = session.client(
        "bedrock-agent-runtime",
        region_name=AWS_REGION,
        config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2}),
    )

    input_text = json.dumps({"message": message, "user_id": user_id})
    memory_id = st.session_state.get("active_cluster_id") or "general"

    try:
        response = client.invoke_agent(
            agentId=ORCHESTRATOR_AGENT_ID,
            agentAliasId=ORCHESTRATOR_AGENT_ALIAS_ID,
            sessionId=st.session_state.session_id,
            inputText=input_text,
            memoryId=memory_id,
            enableTrace=True,
        )

        result_text = ""
        trace_steps = []

        if "completion" in response:
            for event in response["completion"]:
                if "chunk" in event:
                    chunk_bytes = event["chunk"].get("bytes", b"")
                    result_text += chunk_bytes.decode("utf-8", errors="replace")
                if "trace" in event:
                    trace_steps.extend(_extract_trace_steps(event))

        return result_text or "No response from orchestrator.", trace_steps

    except client.exceptions.ResourceNotFoundException:
        return (
            "⚠️ Orchestrator agent not found. Make sure you've deployed the agents "
            "with `cdk deploy` and set the `ORCHESTRATOR_AGENT_ID` environment variable.",
            [],
        )
    except Exception as e:
        error_msg = str(e)
        if "expired" in error_msg.lower() or "token" in error_msg.lower():
            if _do_token_refresh():
                return invoke_orchestrator(message, user_id)
        return f"⚠️ Error communicating with orchestrator: {error_msg}", []


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
    if st.session_state.active_cluster_id:
        st.caption(f"Cluster: `{st.session_state.active_cluster_id}`")
        if st.button("🗑️ Forget Cluster Memory", use_container_width=True):
            result = forget_cluster_memory(st.session_state.active_cluster_id)
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.toast(result)

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
# Helpers
# ---------------------------------------------------------------------------

_TRACE_ICONS = {
    "reasoning": "🧠",
    "tool_call": "🔧",
    "tool_result": "📤",
    "agent_call": "🤝",
    "agent_result": "💬",
    "kb_lookup": "📚",
    "kb_result": "📖",
}


def _render_trace(steps: list[dict]) -> None:
    """Render agent trace steps inside a collapsible expander."""
    if not steps:
        return
    with st.expander(f"🔍 Agent reasoning ({len(steps)} steps)", expanded=False):
        for i, step in enumerate(steps, 1):
            stype = step.get("type", "")
            icon = _TRACE_ICONS.get(stype, "•")

            if stype == "reasoning":
                st.markdown(f"**{icon} Step {i} — Reasoning**")
                st.markdown(step["text"])

            elif stype == "tool_call":
                st.markdown(f"**{icon} Step {i} — Tool call:** `{step['tool']}`")
                if step.get("input"):
                    st.code(step["input"], language="json")

            elif stype == "tool_result":
                st.markdown(f"**{icon} Step {i} — Tool result**")
                output = step.get("output", "")
                # Try to pretty-print JSON, fall back to plain text
                try:
                    st.code(json.dumps(json.loads(output), indent=2), language="json")
                except Exception:
                    st.text(output[:2000])  # cap very long outputs

            elif stype == "agent_call":
                st.markdown(f"**{icon} Step {i} — Delegating to:** `{step['tool']}`")
                if step.get("input"):
                    st.markdown(f"> {step['input']}")

            elif stype == "agent_result":
                st.markdown(f"**{icon} Step {i} — Response from:** `{step['tool']}`")
                output = step.get("output", "")
                if output:
                    st.markdown(output[:3000])

            elif stype == "kb_lookup":
                st.markdown(f"**{icon} Step {i} — Knowledge base lookup**")
                st.markdown(f"> {step.get('text', '')}")

            elif stype == "kb_result":
                st.markdown(f"**{icon} Step {i} — Knowledge base results**")
                st.markdown(step.get("output", ""))

            if i < len(steps):
                st.divider()


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

st.title("🚀 Redshift Modernization")
st.caption("Migrate your Redshift Provisioned cluster to Serverless")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("trace"):
            _render_trace(msg["trace"])
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Describe your modernization request..."):
    # user_id is always from Cognito JWT — cannot be overridden
    user_id = st.session_state.user_id

    # Extract cluster_id from the message if mentioned
    # Looks for patterns like "cluster my-cluster-01" or known cluster names
    import re
    cluster_match = re.search(r'cluster[- _]?(?:id)?[:\s]+([a-zA-Z0-9][a-zA-Z0-9._-]+)', prompt, re.IGNORECASE)
    if not cluster_match:
        # Also match "modernize <cluster-name>" or "<cluster-name> in <region>"
        cluster_match = re.search(r'(?:modernize|migrate|assess|analyze)\s+([a-zA-Z][a-zA-Z0-9._-]+)', prompt, re.IGNORECASE)
    if cluster_match:
        new_cluster = cluster_match.group(1)
        if new_cluster != st.session_state.active_cluster_id:
            # Cluster switched — start fresh session so context doesn't bleed
            st.session_state.active_cluster_id = new_cluster
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get orchestrator response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response, trace_steps = invoke_orchestrator(prompt, user_id)
        _render_trace(trace_steps)
        st.markdown(response)

    # Add assistant message (store trace for history replay)
    st.session_state.messages.append({"role": "assistant", "content": response, "trace": trace_steps})


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
