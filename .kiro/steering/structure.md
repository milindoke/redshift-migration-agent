# Project Structure

```
.
├── sdk/                          # Legacy ATX BaseAgent SDK wheel files (vendored, unused)
├── src/redshift_agents/          # Main application code
│   ├── orchestrator/
│   │   └── orchestrator.py       # Orchestrator agent (workflow, locking, approval gates)
│   ├── subagents/
│   │   ├── assessment.py         # Assessment agent (cluster discovery, WLM analysis, metrics)
│   │   ├── architecture.py       # Architecture agent (workgroup design, RPU sizing)
│   │   └── execution.py          # Execution agent (create resources, migrate, validate)
│   ├── tools/
│   │   ├── redshift_tools.py     # Shared @tool functions (9 tools, boto3 calls)
│   │   ├── audit_logger.py       # Structured JSON audit logging
│   │   ├── cluster_lock.py       # DynamoDB cluster-level locking
│   │   └── log_sharing.py        # Cross-account log sharing opt-in
│   ├── iam/                      # Per-agent IAM policy documents (JSON)
│   ├── tests/                    # Unit + property-based tests (68 tests, 7 files)
│   │   ├── conftest.py           # Strands/AgentCore stubs for test env
│   │   ├── test_redshift_tools.py
│   │   ├── test_audit_logger.py
│   │   ├── test_cluster_lock.py
│   │   ├── test_assessment.py
│   │   ├── test_architecture.py
│   │   ├── test_execution.py
│   │   ├── test_orchestrator.py
│   │   └── requirements-test.txt
│   ├── models.py                 # Dataclasses (Assessment/Architecture/Execution results, locks, audit)
│   ├── deploy-agentcore.sh       # Deploy all agents via `agentcore launch`
│   ├── requirements.txt
│   └── .env.example
```

## Architecture Patterns

- **Agent pattern**: Each agent is a Python module with a `SYSTEM_PROMPT` constant and a `create_agent(tools=None)` factory returning a Strands `Agent`. Each has a `BedrockAgentCoreApp` entry point for `agentcore launch`.
- **Tool pattern**: Shared tools in `tools/redshift_tools.py` use `@tool` from `strands.tools`. Tools are plain functions that call AWS APIs via boto3 and return dicts. Errors return `{"error": ...}`, never raise.
- **Subagents import tools** from `..tools.redshift_tools` and pass them to `Agent(tools=[...])`.
- **Orchestrator** delegates to subagents via Bedrock AgentCore `InvokeAgent` API (not direct tool imports). It also manages cluster locks and approval gates.

## Conventions
- System prompts are module-level constants named `*_SYSTEM_PROMPT`.
- Factory functions: `create_agent(tools=None) -> Agent`.
- Every tool accepts `region` and `user_id` for cross-region support and identity propagation.
- Every tool emits audit events via `emit_audit_event(initiated_by=user_id)`.
- Environment config via `.env` files (see `.env.example`).
