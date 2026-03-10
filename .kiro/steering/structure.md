# Project Structure

```
.
├── sdk/                          # ATX BaseAgent SDK wheel files (vendored)
├── src/redshift_agents/          # Main application code
│   ├── orchestrator/
│   │   └── orchestrator.py       # Central orchestrator (customer account, coordinates workflow)
│   ├── subagents/                # Customer-account agents
│   │   ├── assessment.py         # Cluster config & performance analysis
│   │   ├── scoring.py            # Best practices scoring (security/perf/cost)
│   │   ├── architecture.py       # Multi-warehouse topology design
│   │   └── execution.py          # Phased migration planning
│   ├── tools/
│   │   ├── redshift_tools.py     # Shared Strands @tool functions (boto3 calls)
│   │   └── audit_logger.py       # Structured JSON audit logging for fleet observability
│   ├── tests/
│   │   └── test_redshift_tools.py
│   ├── docker/                   # Dockerfiles (one per agent) + docker-compose
│   ├── docs/                     # Deployment checklist, testing guide
│   ├── requirements.txt
│   └── *.sh                      # Build/deploy shell scripts
```

## Architecture Patterns

- **Agent pattern**: Each agent is a Python module that defines a system prompt and a factory function (`create_*`) returning an `AsyncBaseSubagent` or `AsyncBaseOrchestrator`. Each also has a `main()` CLI entry point that starts an `AgentRuntimeServer`.
- **Tool pattern**: Shared tools live in `tools/redshift_tools.py` using the `@tool` decorator from Strands. Tools are plain functions that call AWS APIs via boto3 and return dicts.
- **Subagents import tools** from `..tools.redshift_tools` and pass them as `custom_tools` to the SDK.
- **Orchestrator** does not import tools directly — it delegates to subagents via MCP `InvokeAgent`.

## Conventions
- System prompts are module-level constants named `*_SYSTEM_PROMPT`.
- Factory functions follow the signature `create_*(mcp_client, storage_dir) -> Agent`.
- Each agent listens on a distinct port (8080–8084).
- Environment config via `.env` files (see `.env.example`).
