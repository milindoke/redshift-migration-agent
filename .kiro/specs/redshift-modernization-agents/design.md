# Design: Redshift Modernization Agents

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Customer Account                          │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Orchestrator (port 8080)                      │  │
│  │  - AsyncBaseOrchestrator                                  │  │
│  │  - MCP InvokeAgent for subagent delegation                │  │
│  │  - Coordinates workflow, maintains state                  │  │
│  └──────────┬──────────┬──────────┬──────────┬───────────────┘  │
│             │          │          │          │                   │
│  ┌──────────┴──┐ ┌─────┴──────┐ ┌┴────────┐ ┌┴────────┐       │
│  │ Assessment  │ │ Scoring    │ │ Arch.   │ │ Exec.   │       │
│  │ port 8081   │ │ port 8082  │ │ port    │ │ port    │       │
│  │             │ │            │ │ 8083    │ │ 8084    │       │
│  │ Tools:      │ │ Tools:     │ │ No tools│ │ No tools│       │
│  │ - analyze   │ │ - analyze  │ │(reason- │ │         │       │
│  │ - metrics   │ │ - metrics  │ │ ing)    │ │         │       │
│  │ - list      │ │            │ │         │ │         │       │
│  └──────────┬──┘ └─────┬──────┘ └─────────┘ └─────────┘       │
│             │          │                                        │
│             └────┬─────┘                                        │
│           ┌──────┴───────┐                                      │
│           │   Redshift   │                                      │
│           │   Clusters   │                                      │
│           └──────────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
```

All 5 agents (orchestrator + 4 subagents) run within the customer's AWS account. There is no service account dependency. Customer data and all agent activity remain within the customer account boundary.

## Component Design

### 1. Agent Module Pattern

Every agent follows the same module structure:

```python
# Module docstring
"""Agent description."""

# Imports
from eg_platform_base_agent.subagent_strands.base_subagent import AsyncBaseSubagent
from mcp import MCPClient

# System prompt constant
AGENT_SYSTEM_PROMPT = """..."""

# Factory function
def create_<agent>(mcp_client, storage_dir) -> AsyncBaseSubagent:
    return AsyncBaseSubagent(
        system_prompt=AGENT_SYSTEM_PROMPT,
        mcp_clients=[mcp_client] if mcp_client else None,
        custom_tools=[...],
        region_name=os.getenv("AWS_REGION", "us-east-2"),
    )

# CLI entry point
def main():
    server = AgentRuntimeServer(
        agent_factory=create_<agent>,
        host=args.host,
        port=args.port,
        storage_dir=args.storage_dir,
        binary_location=args.binary_location,
    )
    server.start()
```

The orchestrator differs slightly — it uses `create_default_async_orchestrator_with_subagent()` from the SDK factory.

### 2. Tool Design

Tools are defined in `tools/redshift_tools.py` using the Strands `@tool` decorator:

```python
@tool
def tool_name(param: str, region: str = "us-east-2") -> Dict:
    client = boto3.client('service', region_name=region)
    try:
        # API call
        return { structured_result }
    except Exception as e:
        return { "error": str(e), ... }
```

Conventions:
- All tools return `Dict` or `List[Dict]`
- Error responses always include `"error"` key plus input params
- Default region is `us-east-2`
- Tools are pure functions with no side effects beyond API reads

### 3. Tool-to-Agent Mapping

| Tool | Assessment | Scoring | Architecture | Execution |
|------|-----------|---------|-------------|-----------|
| `analyze_redshift_cluster` | ✓ | ✓ | — | — |
| `get_cluster_metrics` | ✓ | ✓ | — | — |
| `list_redshift_clusters` | ✓ | — | — | — |

Architecture and Execution agents are reasoning-only (no custom tools, `custom_tools=[]`).

### 4. Container Design

Each agent has a dedicated Dockerfile:
- `Dockerfile.orchestrator` → uses `eg_platform_base_agent.orchestrator_cli`
- `Dockerfile.assessment` → uses `eg_platform_base_agent.subagent_cli`
- `Dockerfile.scoring`, `.architecture`, `.execution` → same subagent CLI pattern

Build layers:
1. `python:3.12-slim` + system deps (gcc, python3-dev)
2. SDK wheels from `sdk/*.whl`
3. `requirements.txt` dependencies
4. Application code
5. Health check on `/ping`

### 5. Inter-Agent Communication

```
Orchestrator → MCP InvokeAgent(agentId, inputPayload) → Subagent
                                                          ↓
Orchestrator ← MCP GetAgentInstance(agentInstanceId) ← Result
```

`inputPayload` always includes:
- `message`: Natural language instruction
- `cluster_id`: Target cluster
- `region`: AWS region
- `customer_account_id`: For namespace isolation

### 6. Scoring Algorithm

Total: 100 points = Security (35) + Performance (35) + Cost (30)

Security subcategories: Encryption (10), Network (10), VPC Routing (5), Access Controls (5), Audit Logging (5)
Performance subcategories: Node Type (10), Sizing (10), Disk (5), Query Perf (5), WLM (5)
Cost subcategories: Reserved Instances (10), Right-Sizing (10), Snapshots (5), Pause/Resume (5)

Grade mapping: A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, F < 60

### 7. Deployment Topology

All 5 agent images are pushed to the customer account ECR and deployed to Bedrock AgentCore within the customer account:

- Orchestrator image → Customer account ECR → Bedrock AgentCore
- 4 subagent images → Customer account ECR → Bedrock AgentCore
- Docker Compose for local multi-agent testing (all 5 on bridge network)
- Port mapping: orchestrator=8080, assessment=8081, scoring=8082, architecture=8083, execution=8084
- Single IAM role set covering Redshift read, CloudWatch read/write, Bedrock InvokeAgent, S3 conversation storage

### 8. Fleet Audit Observability

The Redshift Service Team needs visibility into which customer accounts use the modernization agents and how. Two complementary mechanisms provide this:

**Structured Audit Logging (agent-level context)**

`tools/audit_logger.py` provides `emit_audit_event()` which emits single-line JSON to a dedicated `redshift_modernization_audit` Python logger. Every event includes:

```json
{
  "timestamp": "2026-03-10T...",
  "event_type": "tool_invocation",
  "agent_name": "assessment",
  "customer_account_id": "123456789012",
  "cluster_id": "prod-cluster-01",
  "region": "us-east-2",
  "details": {"tool": "analyze_redshift_cluster"}
}
```

Event types: `agent_start`, `tool_invocation`, `workflow_start`, `workflow_complete`, `phase_start`, `phase_complete`, `scoring_result`, `error`

Instrumentation points:
- Every agent factory function emits `agent_start`
- Every `@tool` function emits `tool_invocation` before calling AWS APIs
- Orchestrator system prompt instructs the LLM to call audit events at workflow/phase boundaries

**CloudTrail (API-level context)**

CloudTrail automatically captures every `redshift:DescribeClusters` and `cloudwatch:GetMetricStatistics` call with the caller's account ID, IAM role ARN, and timestamp. The Redshift Service Team already has fleet-level CloudTrail access.

**Example CloudWatch Logs Insights queries for the Service Team:**

```
-- Which accounts used the modernization agent?
fields @timestamp, customer_account_id, agent_name, event_type
| filter event_type = "agent_start"
| stats count() by customer_account_id
| sort count desc

-- What clusters were analyzed?
fields @timestamp, customer_account_id, cluster_id, agent_name
| filter event_type = "tool_invocation"
| stats count() by customer_account_id, cluster_id

-- Scoring results across fleet
fields @timestamp, customer_account_id, cluster_id, details.overall_score
| filter event_type = "scoring_result"
```
