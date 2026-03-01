# ✅ ECR Push Successful!

## Status: Images in ECR! 🎉

All 5 container images have been successfully pushed to Amazon ECR!

## ECR Image URIs

### Service Account (497316421912) - Orchestrator

```
497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-orchestrator:latest
```

### Customer Account (188199011335) - Subagents

```
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-assessment:latest
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-scoring:latest
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-architecture:latest
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-execution:latest
```

## Next Step: Deploy to Bedrock AgentCore

### Prerequisites

You'll need ATX credentials from your SA:
- **Workspace ID**
- **MCP Auth Token** (from AWS Secrets Manager)

### Deployment Process

Deploy each agent via the Bedrock Console. Here's the step-by-step for each:

---

## 1. Deploy Orchestrator (Service Account)

### Open Bedrock Console

1. Switch to **service-account** profile (497316421912)
2. Navigate to: **AWS Bedrock Console** → **AgentCore**
3. Click **Create Agent**

### Configure Agent

**Basic Settings:**
- **Agent Name**: `redshift-orchestrator`
- **Description**: `Redshift Modernization Orchestrator - coordinates workflow`

**Runtime Configuration:**
- **Runtime Type**: Container
- **Image URI**: 
  ```
  497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-orchestrator:latest
  ```
- **Port**: `8080`

**Execution Role:**
- Create new role or select existing
- Required permissions:
  - ECR: Pull images
  - Bedrock: InvokeAgent (for subagents)
  - CloudWatch Logs: Write
  - S3: Read/Write (for conversation storage)

**Environment Variables:**
```
WORKSPACE_ID=<from-your-SA>
MCP_AUTH_TOKEN=<from-secrets-manager>
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/orchestrator
```

**Health Check:**
- **Path**: `/ping`
- **Port**: `8080`
- **Interval**: 30 seconds

### Deploy

1. Click **Create**
2. Wait for deployment (~3-5 minutes)
3. **Note the Agent ARN** - you'll need this for ATX registration

---

## 2. Deploy Assessment Subagent (Customer Account)

### Open Bedrock Console

1. Switch to **customer-account** profile (188199011335)
2. Navigate to: **AWS Bedrock Console** → **AgentCore**
3. Click **Create Agent**

### Configure Agent

**Basic Settings:**
- **Agent Name**: `redshift-assessment-subagent`
- **Description**: `Analyzes Redshift cluster configuration and performance`

**Runtime Configuration:**
- **Runtime Type**: Container
- **Image URI**: 
  ```
  188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-assessment:latest
  ```
- **Port**: `8080`

**Execution Role:**
- Create new role or select existing
- Required permissions:
  - ECR: Pull images
  - Redshift: DescribeClusters (read-only)
  - CloudWatch: GetMetricStatistics (read-only)
  - CloudWatch Logs: Write

**Environment Variables:**
```
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/assessment
```

**Health Check:**
- **Path**: `/ping`
- **Port**: `8080`
- **Interval**: 30 seconds

### Deploy

1. Click **Create**
2. Wait for deployment (~3-5 minutes)
3. **Note the Agent ARN**

---

## 3. Deploy Scoring Subagent (Customer Account)

Repeat the process above with these changes:

**Basic Settings:**
- **Agent Name**: `redshift-scoring-subagent`
- **Description**: `Evaluates best practices (Security 35%, Performance 35%, Cost 30%)`

**Runtime Configuration:**
- **Image URI**: 
  ```
  188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-scoring:latest
  ```

**Environment Variables:**
```
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/scoring
```

---

## 4. Deploy Architecture Subagent (Customer Account)

**Basic Settings:**
- **Agent Name**: `redshift-architecture-subagent`
- **Description**: `Designs multi-warehouse architecture`

**Runtime Configuration:**
- **Image URI**: 
  ```
  188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-architecture:latest
  ```

**Environment Variables:**
```
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/architecture
```

---

## 5. Deploy Execution Subagent (Customer Account)

**Basic Settings:**
- **Agent Name**: `redshift-execution-subagent`
- **Description**: `Creates and executes 5-phase migration plans`

**Runtime Configuration:**
- **Image URI**: 
  ```
  188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-execution:latest
  ```

**Environment Variables:**
```
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/execution
```

---

## After Deployment: Register with ATX

Once all agents are deployed, register them with ATX Agent Registry:

```bash
# Register orchestrator
aws bedrock-agent register-agent \
  --agent-id redshift-orchestrator \
  --agent-arn <arn-from-bedrock-console> \
  --region us-east-2 \
  --profile service-account

# Register assessment subagent
aws bedrock-agent register-agent \
  --agent-id redshift-assessment-subagent \
  --agent-arn <arn-from-bedrock-console> \
  --region us-east-2 \
  --profile customer-account

# Register scoring subagent
aws bedrock-agent register-agent \
  --agent-id redshift-scoring-subagent \
  --agent-arn <arn-from-bedrock-console> \
  --region us-east-2 \
  --profile customer-account

# Register architecture subagent
aws bedrock-agent register-agent \
  --agent-id redshift-architecture-subagent \
  --agent-arn <arn-from-bedrock-console> \
  --region us-east-2 \
  --profile customer-account

# Register execution subagent
aws bedrock-agent register-agent \
  --agent-id redshift-execution-subagent \
  --agent-arn <arn-from-bedrock-console> \
  --region us-east-2 \
  --profile customer-account
```

## Testing

### Test Individual Subagent

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id redshift-assessment-subagent \
  --session-id test-$(date +%s) \
  --input-text "Analyze cluster test-cluster-01 in us-east-2" \
  --region us-east-2 \
  --profile customer-account \
  response.json

cat response.json
```

### Test Orchestrator

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id redshift-orchestrator \
  --session-id test-$(date +%s) \
  --input-text "Modernize cluster prod-cluster-01 in us-east-2" \
  --region us-east-2 \
  --profile service-account \
  response.json

cat response.json
```

## Monitoring

### CloudWatch Logs

```bash
# Orchestrator logs
aws logs tail /aws/bedrock/agentcore/redshift-orchestrator \
  --follow \
  --profile service-account

# Subagent logs
aws logs tail /aws/bedrock/agentcore/redshift-assessment-subagent \
  --follow \
  --profile customer-account
```

### Agent Status

Check agent status in Bedrock Console:
- Navigate to AgentCore
- Select your agent
- View status, logs, and metrics

## Timeline

| Step | Time | Status |
|------|------|--------|
| Build images | Done | ✅ |
| Push to ECR | Done | ✅ |
| Deploy orchestrator | 5 min | ⏳ Next |
| Deploy 4 subagents | 20 min | ⏳ Pending |
| Register with ATX | 2 min | ⏳ Pending |
| Test | 2 min | ⏳ Pending |
| **Total remaining** | **~30 min** | |

## Troubleshooting

### Image pull fails
- Verify execution role has ECR pull permissions
- Check image URI is correct
- Ensure region is us-east-2

### Agent won't start
- Check CloudWatch logs for errors
- Verify environment variables are set
- Ensure health check endpoint is accessible

### Registration fails
- Verify agent ARN is correct
- Check ATX credentials are valid
- Ensure agent is in "Running" state

## Quick Reference

### Image URIs (Copy-Paste Ready)

**Orchestrator:**
```
497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-orchestrator:latest
```

**Assessment:**
```
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-assessment:latest
```

**Scoring:**
```
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-scoring:latest
```

**Architecture:**
```
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-architecture:latest
```

**Execution:**
```
188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-execution:latest
```

### Environment Variables Template

**Orchestrator:**
```
WORKSPACE_ID=<from-SA>
MCP_AUTH_TOKEN=<from-secrets-manager>
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/orchestrator
```

**Subagents:**
```
AWS_REGION=us-east-2
STORAGE_DIR=/tmp/<agent-name>
```

---

**Status: Ready for Bedrock deployment!** 🚀

**Next action: Deploy agents via Bedrock Console using the URIs above**
