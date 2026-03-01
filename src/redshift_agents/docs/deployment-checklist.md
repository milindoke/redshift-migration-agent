# Deployment Checklist

Use this checklist to track your deployment progress.

## Pre-Deployment ✅

- [x] All code uncommented
- [x] All SDK imports active
- [x] All @tool decorators added
- [x] All files compile successfully
- [x] Build script created (`build-all.sh`)
- [x] Documentation complete

## Phase 1: Build Docker Images (10 minutes)

- [ ] Navigate to project directory
  ```bash
  cd src/redshift_agents
  ```

- [ ] Run build script
  ```bash
  ./build-all.sh
  ```

- [ ] Verify all 5 images created
  ```bash
  docker images | grep redshift
  ```

Expected output:
```
redshift-orchestrator    latest    ...
redshift-assessment      latest    ...
redshift-scoring         latest    ...
redshift-architecture    latest    ...
redshift-execution       latest    ...
```

## Phase 2: Local Testing (Optional, 15 minutes)

- [ ] Copy environment template
  ```bash
  cp .env.example .env
  ```

- [ ] Edit .env with credentials
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_SESSION_TOKEN (if using temporary credentials)
  - AWS_REGION=us-east-2
  - WORKSPACE_ID (from SA)
  - MCP_AUTH_TOKEN (from SA)

- [ ] Start all agents
  ```bash
  docker-compose up -d
  ```

- [ ] Check logs
  ```bash
  docker-compose logs -f orchestrator
  docker-compose logs -f assessment
  ```

- [ ] Test orchestrator (optional)
  ```bash
  curl -X POST http://localhost:8080/invoke \
    -H "Content-Type: application/json" \
    -d '{"message": "Analyze cluster prod-cluster-01", "customer_account_id": "188199011335"}'
  ```

- [ ] Stop agents
  ```bash
  docker-compose down
  ```

## Phase 3: Push to ECR - Service Account (10 minutes)

### Orchestrator to Service Account (497316421912)

- [ ] Login to ECR
  ```bash
  aws ecr get-login-password --region us-east-2 --profile service-account | \
    docker login --username AWS --password-stdin 497316421912.dkr.ecr.us-east-2.amazonaws.com
  ```

- [ ] Create repository
  ```bash
  aws ecr create-repository \
    --repository-name redshift-orchestrator \
    --region us-east-2 \
    --profile service-account
  ```

- [ ] Tag image
  ```bash
  docker tag redshift-orchestrator:latest \
    497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-orchestrator:latest
  ```

- [ ] Push image
  ```bash
  docker push 497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-orchestrator:latest
  ```

- [ ] Verify push
  ```bash
  aws ecr describe-images \
    --repository-name redshift-orchestrator \
    --region us-east-2 \
    --profile service-account
  ```

## Phase 4: Push to ECR - Customer Account (15 minutes)

### Subagents to Customer Account (188199011335)

- [ ] Login to ECR
  ```bash
  aws ecr get-login-password --region us-east-2 --profile customer-account | \
    docker login --username AWS --password-stdin 188199011335.dkr.ecr.us-east-2.amazonaws.com
  ```

- [ ] Create repositories
  ```bash
  aws ecr create-repository --repository-name redshift-assessment --region us-east-2 --profile customer-account
  aws ecr create-repository --repository-name redshift-scoring --region us-east-2 --profile customer-account
  aws ecr create-repository --repository-name redshift-architecture --region us-east-2 --profile customer-account
  aws ecr create-repository --repository-name redshift-execution --region us-east-2 --profile customer-account
  ```

- [ ] Tag and push assessment
  ```bash
  docker tag redshift-assessment:latest 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-assessment:latest
  docker push 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-assessment:latest
  ```

- [ ] Tag and push scoring
  ```bash
  docker tag redshift-scoring:latest 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-scoring:latest
  docker push 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-scoring:latest
  ```

- [ ] Tag and push architecture
  ```bash
  docker tag redshift-architecture:latest 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-architecture:latest
  docker push 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-architecture:latest
  ```

- [ ] Tag and push execution
  ```bash
  docker tag redshift-execution:latest 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-execution:latest
  docker push 188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-execution:latest
  ```

- [ ] Verify all pushes
  ```bash
  aws ecr describe-repositories --region us-east-2 --profile customer-account | grep redshift
  ```

## Phase 5: Deploy to Bedrock AgentCore (30 minutes)

### Deploy Orchestrator (Service Account)

- [ ] Open Bedrock AgentCore console (Service Account)
- [ ] Create new agent: "redshift-orchestrator"
- [ ] Set foundation model: anthropic.claude-3-sonnet-20240229-v1:0
- [ ] Configure container:
  - Image URI: `497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-orchestrator:latest`
  - Port: 8080
- [ ] Set IAM role with permissions:
  - S3 access for conversation storage
  - Bedrock InvokeAgent permissions
  - CloudWatch Logs write
- [ ] Set environment variables:
  - WORKSPACE_ID
  - MCP_AUTH_TOKEN
  - AWS_REGION=us-east-2
- [ ] Deploy agent
- [ ] Note agent ID: ________________

### Deploy Assessment Subagent (Customer Account)

- [ ] Open Bedrock AgentCore console (Customer Account)
- [ ] Create new agent: "redshift-assessment-subagent"
- [ ] Set foundation model: anthropic.claude-3-sonnet-20240229-v1:0
- [ ] Configure container:
  - Image URI: `188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-assessment:latest`
  - Port: 8081
- [ ] Set IAM role with permissions:
  - Redshift DescribeClusters (read-only)
  - CloudWatch GetMetricStatistics (read-only)
  - CloudWatch Logs write
- [ ] Set environment variables:
  - AWS_REGION=us-east-2
- [ ] Deploy agent
- [ ] Note agent ID: ________________

### Deploy Scoring Subagent (Customer Account)

- [ ] Create new agent: "redshift-scoring-subagent"
- [ ] Set foundation model: anthropic.claude-3-sonnet-20240229-v1:0
- [ ] Configure container:
  - Image URI: `188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-scoring:latest`
  - Port: 8082
- [ ] Set IAM role (same as assessment)
- [ ] Set environment variables
- [ ] Deploy agent
- [ ] Note agent ID: ________________

### Deploy Architecture Subagent (Customer Account)

- [ ] Create new agent: "redshift-architecture-subagent"
- [ ] Set foundation model: anthropic.claude-3-sonnet-20240229-v1:0
- [ ] Configure container:
  - Image URI: `188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-architecture:latest`
  - Port: 8083
- [ ] Set IAM role (same as assessment)
- [ ] Set environment variables
- [ ] Deploy agent
- [ ] Note agent ID: ________________

### Deploy Execution Subagent (Customer Account)

- [ ] Create new agent: "redshift-execution-subagent"
- [ ] Set foundation model: anthropic.claude-3-sonnet-20240229-v1:0
- [ ] Configure container:
  - Image URI: `188199011335.dkr.ecr.us-east-2.amazonaws.com/redshift-execution:latest`
  - Port: 8084
- [ ] Set IAM role (same as assessment)
- [ ] Set environment variables
- [ ] Deploy agent
- [ ] Note agent ID: ________________

## Phase 6: Register with ATX Agent Registry (10 minutes)

- [ ] Register orchestrator
  ```bash
  atx-cli register-agent \
    --agent-id redshift-orchestrator \
    --agent-type orchestrator \
    --account-id 497316421912 \
    --region us-east-2
  ```

- [ ] Register assessment subagent
  ```bash
  atx-cli register-agent \
    --agent-id redshift-assessment-subagent \
    --agent-type subagent \
    --account-id 188199011335 \
    --region us-east-2
  ```

- [ ] Register scoring subagent
  ```bash
  atx-cli register-agent \
    --agent-id redshift-scoring-subagent \
    --agent-type subagent \
    --account-id 188199011335 \
    --region us-east-2
  ```

- [ ] Register architecture subagent
  ```bash
  atx-cli register-agent \
    --agent-id redshift-architecture-subagent \
    --agent-type subagent \
    --account-id 188199011335 \
    --region us-east-2
  ```

- [ ] Register execution subagent
  ```bash
  atx-cli register-agent \
    --agent-id redshift-execution-subagent \
    --agent-type subagent \
    --account-id 188199011335 \
    --region us-east-2
  ```

- [ ] Verify registrations
  ```bash
  atx-cli list-agents --region us-east-2
  ```

## Phase 7: End-to-End Testing (15 minutes)

### Test 1: Invoke Orchestrator

- [ ] Invoke orchestrator
  ```bash
  atx-cli invoke-agent \
    --agent-id redshift-orchestrator \
    --message "Analyze cluster prod-cluster-01 in us-east-2" \
    --customer-account-id 188199011335
  ```

- [ ] Note agent instance ID: ________________

- [ ] Get agent instance status
  ```bash
  atx-cli get-agent-instance --agent-instance-id <instance-id>
  ```

- [ ] Check orchestrator logs
  ```bash
  aws logs tail /aws/bedrock/agents/redshift-orchestrator --follow --profile service-account
  ```

### Test 2: Verify Subagent Invocation

- [ ] Check assessment subagent logs
  ```bash
  aws logs tail /aws/bedrock/agents/redshift-assessment-subagent --follow --profile customer-account
  ```

- [ ] Verify subagent was invoked by orchestrator
- [ ] Verify subagent returned results to orchestrator

### Test 3: Full Workflow

- [ ] Invoke full modernization workflow
  ```bash
  atx-cli invoke-agent \
    --agent-id redshift-orchestrator \
    --message "I want to modernize my Redshift cluster prod-cluster-01 in us-east-2. Please perform a complete assessment, scoring, architecture design, and create a migration plan." \
    --customer-account-id 188199011335
  ```

- [ ] Monitor orchestrator progress
- [ ] Verify all 4 subagents are invoked
- [ ] Verify complete workflow execution
- [ ] Review final recommendations

## Phase 8: Monitoring Setup (10 minutes)

- [ ] Create CloudWatch dashboard for orchestrator
- [ ] Create CloudWatch dashboard for subagents
- [ ] Set up alarms for errors
- [ ] Set up alarms for high latency
- [ ] Configure SNS notifications

## Post-Deployment

- [ ] Document agent IDs
- [ ] Document ECR image URIs
- [ ] Update runbook with deployment details
- [ ] Share access with team
- [ ] Schedule regular reviews

## Troubleshooting

If issues occur, check:

1. **Build fails**: Check Docker is installed, requirements.txt is correct
2. **ECR push fails**: Verify AWS credentials, check repository exists
3. **Agent deployment fails**: Check IAM roles, verify image URI
4. **Agent invocation fails**: Check agent is registered, verify CloudWatch logs
5. **Subagent not invoked**: Check orchestrator has InvokeAgent permissions

## Success Criteria

Deployment is successful when:
- [ ] All 5 Docker images built
- [ ] All 5 images pushed to ECR
- [ ] All 5 agents deployed to Bedrock AgentCore
- [ ] All 5 agents registered with ATX
- [ ] Orchestrator can invoke all subagents
- [ ] Full workflow executes end-to-end
- [ ] CloudWatch logs show successful execution

## Estimated Timeline

- Build: 10 minutes
- Local testing (optional): 15 minutes
- ECR push: 25 minutes
- Bedrock deployment: 30 minutes
- ATX registration: 10 minutes
- Testing: 15 minutes
- Monitoring setup: 10 minutes

**Total: ~2 hours** (or ~1.5 hours without local testing)

## Next Steps After Deployment

1. Test with real Redshift clusters
2. Gather feedback from users
3. Iterate on system prompts
4. Add more tools as needed
5. Implement CI/CD pipeline
6. Create customer onboarding guide
