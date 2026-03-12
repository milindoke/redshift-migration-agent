"""
Redshift Modernization Chat UI — Streamlit app.

Connects to the orchestrator agent via Bedrock AgentCore InvokeAgent API
and provides a conversational interface for the 3-phase modernization workflow.

Run with:
    cd src/redshift_agents
    streamlit run ui/app.py
"""
from __future__ import annotations

import json
import os
import uuid

import boto3
import streamlit as st

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


# ---------------------------------------------------------------------------
# Bedrock AgentCore client
# ---------------------------------------------------------------------------


def invoke_orchestrator(message: str, user_id: str) -> str:
    """Send a message to the orchestrator and return the response."""
    client = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)

    # Build the input with identity propagation
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
            "with `./deploy-agentcore.sh` and set the `ORCHESTRATOR_AGENT_ID` "
            "environment variable."
        )
    except Exception as e:
        return f"⚠️ Error communicating with orchestrator: {str(e)}"


# ---------------------------------------------------------------------------
# Sidebar — configuration
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Configuration")

    user_id = st.text_input(
        "Your User ID",
        value=st.session_state.user_id,
        placeholder="e.g. jane.doe",
        help="Required for identity propagation and audit traceability.",
    )

    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id

    st.divider()

    st.caption(f"Agent: `{ORCHESTRATOR_AGENT_ID}`")
    st.caption(f"Region: `{AWS_REGION}`")
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

    st.divider()

    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
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
    if not st.session_state.user_id:
        st.error("Please enter your User ID in the sidebar before starting.")
        st.stop()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get orchestrator response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = invoke_orchestrator(prompt, st.session_state.user_id)
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
        """
        Enter your **User ID** in the sidebar, then try one of these:

        - *"Modernize my Redshift cluster `prod-cluster-01` in `us-east-2`"*
        - *"List all Redshift clusters in my account"*
        - *"I want to migrate cluster `analytics-dw` to Serverless"*

        The orchestrator will guide you through assessment, architecture design,
        and execution — with approval gates at each step.
        """
    )
