# Redshift Modernization Agents

Multi-agent system for comprehensive Amazon Redshift cluster modernization using AWS Transform (ATX) BaseAgent SDK.

## Status: Ready for Bedrock Deployment 🚀

✅ All container images built and pushed to ECR
✅ Ready to deploy to Bedrock AgentCore

See [ECR_PUSH_SUCCESS.md](./ECR_PUSH_SUCCESS.md) for deployment instructions.

## What This Does

Guides customers through complete Redshift modernization with AI agents:
- **Assessment**: Analyzes cluster configuration and performance
- **Scoring**: Evaluates best practices (Security 35%, Performance 35%, Cost 30%)
- **Architecture**: Designs multi-warehouse architectures
- **Execution**: Creates phased migration plans

## Architecture

```
Service Account (497316421912)          Customer Account (188199011335)
┌─────────────────────────┐            ┌──────────────────────────────┐
│   Orchestrator Agent    │            │  Assessment Subagent         │
│   • Coordinates workflow│───ATX─────▶│  • Cluster analysis          │
│   • Customer comms      │   MCP      │  • Performance metrics       │
│   • No cluster access   │            │  • Direct Redshift access    │
└─────────────────────────┘            ├──────────────────────────────┤
                                       │  Scoring Subagent            │
                                       │  • Best practices evaluation │
                                       ├──────────────────────────────┤
                                       │  Architecture Subagent       │
                                       │  • Multi-warehouse design    │
                                       ├──────────────────────────────┤
                                       │  Execution Subagent          │
                                       │  • Migration planning        │
                                       └──────────────────────────────┘
```

## Prerequisites

- AWS CLI configured with two profiles:
  - `service-account` (497316421912)
  - `customer-account` (188199011335)
- Python 3.10+
- ATX credentials (workspace ID, auth token from SA)
- BaseAgent SDK (automatically available via pip with atx-dev power)

## Quick Start

### Recommended: Use Amazon Bedrock AgentCore Starter Toolkit

The toolkit handles containerization automatically - no Docker required!

```bash
# Install toolkit
pip install bedrock-agentcore-starter-toolkit

# Deploy everything
cd src/redshift_agents
./deploy-with-toolkit.sh
```

See [GETTING_STARTED.md](./GETTING_STARTED.md) for detailed instructions.

### Alternative: Manual Deployment

If you prefer manual control, see [AGENTCORE_TOOLKIT_DEPLOYMENT.md](./AGENTCORE_TOOLKIT_DEPLOYMENT.md).

### Legacy: Package-Based Deployment

<details>
<summary>Click to expand legacy S3 package deployment method</summary>

#### 1. Package Code

```bash
cd src/redshift_agents
./package-all.sh
```

Creates deployment packages in `packages/` directory.

### 2. Upload to S3

**Service Account (Orchestrator):**
```bash
aws s3 mb s3://redshift-agents-497316421912 --region us-east-2 --profile service-account

aws s3 cp packages/orchestrator-deployment.zip \
  s3://redshift-agents-497316421912/orchestrator/ \
  --profile service-account
```

**Customer Account (Subagents):**
```bash
aws s3 mb s3://redshift-agents-188199011335 --region us-east-2 --profile customer-account

for agent in assessment scoring architecture execution; do
  aws s3 cp packages/${agent}-deployment.zip \
    s3://redshift-agents-188199011335/${agent}/ \
    --profile customer-account
done
```

### 3. Deploy via Bedrock Console

For each agent:
1. Open AWS Bedrock AgentCore Console
2. Create Agent
3. Choose "Upload from S3"
4. Provide S3 URI
5. Set runtime: Python 3.12
6. Set handler (see table below)
7. Configure IAM role
8. Set environment variables
9. Deploy (Bedrock builds container automatically)

**Handlers:**
| Agent | Handler |
|-------|---------|
| Orchestrator | `orchestrator.orchestrator.create_orchestrator` |
| Assessment | `subagents.assessment.create_assessment_subagent` |
| Scoring | `subagents.scoring.create_scoring_subagent` |
| Architecture | `subagents.architecture.create_architecture_subagent` |
| Execution | `subagents.execution.create_execution_subagent` |

### 4. Register with ATX

```bash
# Orchestrator
atx-cli register-agent \
  --agent-id redshift-orchestrator \
  --agent-type orchestrator \
  --account-id 497316421912 \
  --region us-east-2

# Subagents
for agent in assessment scoring architecture execution; do
  atx-cli register-agent \
    --agent-id redshift-${agent}-subagent \
    --agent-type subagent \
    --account-id 188199011335 \
    --region us-east-2
done
```

</details>

### 5. Test

```bash
atx-cli invoke-agent \
  --agent-id redshift-orchestrator \
  --message "Analyze cluster prod-cluster-01 in us-east-2" \
  --customer-account-id 188199011335
```

## Configuration

### Environment Variables

**Orchestrator:**
```
WORKSPACE_ID=<from-sa>
MCP_AUTH_TOKEN=<from-sa>
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/orchestrator
```

**Subagents:**
```
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/<subagent-name>
```

### IAM Roles

**Orchestrator Role (Service Account):**
- S3: Read/Write for conversation storage
- Bedrock: InvokeAgent permissions
- CloudWatch Logs: Write

**Subagent Roles (Customer Account):**
- Redshift: DescribeClusters (read-only)
- CloudWatch: GetMetricStatistics (read-only)
- CloudWatch Logs: Write

## Testing

### Quick Test with Toolkit

```bash
# Test individual subagent
atx-cli invoke-agent \
  --agent-id redshift-assessment-subagent \
  --message "Analyze cluster test-cluster-01"

# Test full workflow
atx-cli invoke-agent \
  --agent-id redshift-orchestrator \
  --message "Modernize cluster test-cluster-01" \
  --customer-account-id 188199011335
```

### Unit Tests (Local - No AWS)

```bash
pip install -r tests/requirements-test.txt
pytest tests/ -v
```

### Integration Tests (AWS)

Deploy to dev environment and test:

```bash
# Test individual subagent
atx-cli invoke-agent \
  --agent-id redshift-assessment-subagent \
  --message "Analyze cluster test-cluster-01"

# Test full workflow
atx-cli invoke-agent \
  --agent-id redshift-orchestrator \
  --message "Modernize cluster test-cluster-01"
```

## Monitoring

### Using AgentCore Toolkit

```bash
# View agent status
agentcore status --agent-name redshift-orchestrator --region us-east-2

# View logs (follow mode)
agentcore logs --agent-name redshift-orchestrator --region us-east-2 --follow
```

### CloudWatch Logs
```bash
# Orchestrator
aws logs tail /aws/bedrock/agentcore/redshift-orchestrator --follow --profile service-account

# Subagents
aws logs tail /aws/bedrock/agentcore/redshift-assessment-subagent --follow --profile customer-account
```

### Agent Status
```bash
# Using toolkit
agentcore status --agent-name redshift-orchestrator --region us-east-2

# Using ATX CLI
atx-cli get-agent-instance --agent-instance-id <instance-id>
```

## Troubleshooting

### Toolkit not found
```bash
pip install --upgrade bedrock-agentcore-starter-toolkit
```

### Package script fails
- Ensure you're in `src/redshift_agents/` directory
- Check zip is installed: `which zip`

### S3 upload fails
- Verify credentials: `aws sts get-caller-identity --profile service-account`
- Check bucket exists or create it

### Bedrock deployment fails
- Verify S3 URI is correct
- Check IAM role permissions
- Ensure handler path matches code structure

### Agent invocation fails
- Verify agent is registered: `atx-cli list-agents`
- Check CloudWatch logs for errors
- Ensure environment variables are set

## Project Structure

```
src/redshift_agents/
├── orchestrator/              # Orchestrator agent
│   ├── __init__.py
│   └── orchestrator.py
├── subagents/                 # Specialized subagents
│   ├── __init__.py
│   ├── assessment.py
│   ├── scoring.py
│   ├── architecture.py
│   └── execution.py
├── tools/                     # Redshift analysis tools
│   ├── __init__.py
│   └── redshift_tools.py
├── tests/                     # Unit tests
│   ├── __init__.py
│   ├── test_redshift_tools.py
│   └── requirements-test.txt
├── docs/                      # Detailed documentation
│   ├── deployment-checklist.md
│   └── testing.md
├── docker/                    # Optional Docker path
│   ├── README.md
│   ├── build-all.sh
│   ├── docker-compose.yml
│   └── Dockerfile.*
├── README.md                  # This file
├── package-all.sh            # Packaging script
├── requirements.txt          # Python dependencies
└── .env.example             # Environment template
```

## Advanced Topics

### Docker Deployment (Optional)

If you need pre-built container images, see `docker/README.md`.

### Detailed Guides

- Deployment checklist: `docs/deployment-checklist.md`
- Testing strategy: `docs/testing.md`

### Session Management

Use namespace-based session IDs:
```
{namespace-id}-{task-type}
```

Get namespace ID:
```bash
aws redshift describe-clusters \
  --cluster-identifier prod-cluster-01 \
  --query 'Clusters[0].ClusterNamespaceArn' \
  --output text | cut -d: -f6
```

## Key Features

- ✅ Cross-account security (orchestrator in service account, subagents in customer account)
- ✅ Conversation isolation (customer_account_id required)
- ✅ Namespace-based session IDs
- ✅ Best practices scoring (Security 35%, Performance 35%, Cost 30%)
- ✅ 5-phase migration planning
- ✅ Multi-warehouse architecture design

## Estimated Timeline

- Package: 2 minutes
- Upload to S3: 5 minutes
- Deploy via Bedrock: 20 minutes
- Register with ATX: 5 minutes
- Test: 5 minutes

**Total: ~40 minutes to production**

## Support

- Issues: Check CloudWatch logs
- Questions: Contact your SA
- Updates: Redeploy via S3 upload + Bedrock update

## License

Internal AWS Transform project - not for external distribution.
