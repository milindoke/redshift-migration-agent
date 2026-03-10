# Tasks: Redshift Modernization Agents

## 1. Project Scaffolding
- [x] Task 1.1: Create project structure (`src/redshift_agents/` with `orchestrator/`, `subagents/`, `tools/`, `tests/`, `docker/`, `docs/`)
- [x] Task 1.2: Create `requirements.txt` with core dependencies (boto3, aiohttp, python-dotenv, python-json-logger)
- [x] Task 1.3: Create `.env.example` with all required environment variables
- [x] Task 1.4: Add `__init__.py` files for package structure

## 2. Shared Redshift Tools
- [x] Task 2.1: Implement `analyze_redshift_cluster(cluster_id, region)` — calls `redshift.describe_clusters()`, returns dict with config, security, network, endpoint info
  - File: `src/redshift_agents/tools/redshift_tools.py`
- [x] Task 2.2: Implement `get_cluster_metrics(cluster_id, region, hours)` — fetches 7 CloudWatch metrics (CPU, connections, network rx/tx, disk, read/write latency), returns summary stats
  - File: `src/redshift_agents/tools/redshift_tools.py`
- [x] Task 2.3: Implement `list_redshift_clusters(region)` — calls `redshift.describe_clusters()` without filter, returns list of cluster summaries
  - File: `src/redshift_agents/tools/redshift_tools.py`

## 3. Assessment Subagent
- [x] Task 3.1: Define `ASSESSMENT_SYSTEM_PROMPT` covering configuration analysis, performance analysis, usage pattern identification, risk assessment, and structured JSON output format
  - File: `src/redshift_agents/subagents/assessment.py`
- [x] Task 3.2: Implement `create_assessment_subagent(mcp_client, storage_dir)` factory — returns `AsyncBaseSubagent` with all 3 tools
  - File: `src/redshift_agents/subagents/assessment.py`
- [x] Task 3.3: Implement `main()` CLI entry point with `AgentRuntimeServer` on port 8081
  - File: `src/redshift_agents/subagents/assessment.py`

## 4. Scoring Subagent
- [x] Task 4.1: Define `SCORING_SYSTEM_PROMPT` with full scoring methodology (Security 35pts, Performance 35pts, Cost 30pts), subcategory point breakdowns, grading scale, and structured JSON output format
  - File: `src/redshift_agents/subagents/scoring.py`
- [x] Task 4.2: Implement `create_scoring_subagent(mcp_client, storage_dir)` factory — returns `AsyncBaseSubagent` with `analyze_redshift_cluster` and `get_cluster_metrics` tools
  - File: `src/redshift_agents/subagents/scoring.py`
- [x] Task 4.3: Implement `main()` CLI entry point on port 8082
  - File: `src/redshift_agents/subagents/scoring.py`

## 5. Architecture Subagent
- [x] Task 5.1: Define `ARCHITECTURE_SYSTEM_PROMPT` covering workload analysis, three architecture patterns (hub-and-spoke, independent, hybrid), sizing recommendations, and structured JSON output
  - File: `src/redshift_agents/subagents/architecture.py`
- [x] Task 5.2: Implement `create_architecture_subagent(mcp_client, storage_dir)` factory — reasoning-only agent with no custom tools
  - File: `src/redshift_agents/subagents/architecture.py`
- [x] Task 5.3: Implement `main()` CLI entry point on port 8083
  - File: `src/redshift_agents/subagents/architecture.py`

## 6. Execution Subagent
- [x] Task 6.1: Define `EXECUTION_SYSTEM_PROMPT` covering 5-phase migration approach, IaC generation, data migration strategy, rollback procedures, monitoring plan, and structured JSON output
  - File: `src/redshift_agents/subagents/execution.py`
- [x] Task 6.2: Implement `create_execution_subagent(mcp_client, storage_dir)` factory — reasoning-only agent with no custom tools
  - File: `src/redshift_agents/subagents/execution.py`
- [x] Task 6.3: Implement `main()` CLI entry point on port 8084
  - File: `src/redshift_agents/subagents/execution.py`

## 7. Orchestrator
- [x] Task 7.1: Define `ORCHESTRATOR_SYSTEM_PROMPT` with subagent registry (4 agent IDs, capabilities, when-to-use), 4-phase workflow, InvokeAgent usage examples, and communication guidelines
  - File: `src/redshift_agents/orchestrator/orchestrator.py`
- [x] Task 7.2: Implement `create_orchestrator(mcp_client, storage_dir)` factory — uses `create_default_async_orchestrator_with_subagent()` from SDK
  - File: `src/redshift_agents/orchestrator/orchestrator.py`

## 8. Docker & Deployment
- [x] Task 8.1: Create `Dockerfile.orchestrator` — SDK wheels + orchestrator code, uses `orchestrator_cli`, port 8080
  - File: `src/redshift_agents/docker/Dockerfile.orchestrator`
- [x] Task 8.2: Create `Dockerfile.assessment` — SDK wheels + subagent + tools code, uses `subagent_cli`, port 8080 (internal)
  - File: `src/redshift_agents/docker/Dockerfile.assessment`
- [x] Task 8.3: Create `Dockerfile.scoring`, `Dockerfile.architecture`, `Dockerfile.execution` — same pattern as assessment
  - Files: `src/redshift_agents/docker/Dockerfile.scoring`, `Dockerfile.architecture`, `Dockerfile.execution`
- [x] Task 8.4: Create `docker-compose.yml` for local multi-agent testing with bridge network, env passthrough, and volume mounts
  - File: `src/redshift_agents/docker/docker-compose.yml`
- [x] Task 8.5: Create build and deploy shell scripts (`build-images.sh`, `deploy-with-finch.sh`, `push-to-ecr.sh`)
  - Files: `src/redshift_agents/build-images.sh`, `deploy-with-finch.sh`, `push-to-ecr.sh`

## 9. Testing
- [x] Task 9.1: Write unit tests for `analyze_redshift_cluster` — mock `boto3.client('redshift')`, test success and error cases
  - File: `src/redshift_agents/tests/test_redshift_tools.py`
- [x] Task 9.2: Write unit tests for `get_cluster_metrics` — mock `boto3.client('cloudwatch')`, test with data and empty datapoints
  - File: `src/redshift_agents/tests/test_redshift_tools.py`
- [x] Task 9.3: Write unit tests for `list_redshift_clusters` — mock responses for multiple clusters, empty list, and errors
  - File: `src/redshift_agents/tests/test_redshift_tools.py`
- [x] Task 9.4: Create `requirements-test.txt` with pytest, pytest-cov, pytest-mock
  - File: `src/redshift_agents/tests/requirements-test.txt`

## 10. Documentation
- [x] Task 10.1: Write project README with architecture overview, quick start, usage examples, and cost estimates
  - File: `README.md`
- [x] Task 10.2: Write deployment checklist with phases (build, local test, ECR push, Bedrock deploy, ATX registration, E2E test, monitoring, post-deploy)
  - File: `src/redshift_agents/docs/deployment-checklist.md`
- [x] Task 10.3: Write agent-specific README with detailed documentation
  - File: `src/redshift_agents/README.md`

## 11. Fleet Audit Observability
- [x] Task 11.1: Create `tools/audit_logger.py` with `emit_audit_event()` function that emits structured JSON to `redshift_modernization_audit` logger with `customer_account_id`, `agent_name`, `event_type`, `cluster_id`, `region`, `timestamp`, and optional `details`
  - File: `src/redshift_agents/tools/audit_logger.py`
- [x] Task 11.2: Add `emit_audit_event("tool_invocation", ...)` calls to each `@tool` function in `redshift_tools.py` before AWS API calls
  - File: `src/redshift_agents/tools/redshift_tools.py`
- [x] Task 11.3: Add `emit_audit_event("agent_start", ...)` calls to each agent factory function (orchestrator + 4 subagents)
  - Files: `orchestrator.py`, `assessment.py`, `scoring.py`, `architecture.py`, `execution.py`
