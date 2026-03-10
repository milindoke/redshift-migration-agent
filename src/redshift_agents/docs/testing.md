# Testing Strategy

## The Reality: You Need AWS for Testing

You're absolutely right - since your Redshift clusters are on AWS, you need to deploy to AWS even for testing. "Local Docker testing" still requires:
- AWS credentials
- Network access to AWS Redshift
- Network access to AWS CloudWatch
- ATX MCP server credentials

So the Docker "local testing" isn't really local - it's just running containers on your laptop that connect to AWS.

## Recommended Testing Approach

### Skip "Local Testing" - Deploy Directly to AWS

**Why?**
- Redshift clusters are in AWS (not local)
- Need AWS credentials anyway
- Need network access to AWS anyway
- Bedrock AgentCore provides the same runtime environment
- Faster to just deploy and test in AWS

**How?**
1. Package code
2. Upload to S3
3. Deploy to Bedrock AgentCore
4. Test against real Redshift clusters in AWS

This is actually simpler and more realistic than "local" Docker testing.

## Testing Phases

### Phase 1: Deploy to Dev Environment (AWS)

Deploy all agents to AWS in a dev/test account:

```bash
# Package
cd src/redshift_agents
./package-all.sh

# Upload to S3
aws s3 cp packages/orchestrator-deployment.zip \
  s3://redshift-agents-dev-<ACCOUNT_ID>/orchestrator/

# Deploy via Bedrock Console
# - Point to S3 location
# - Set environment to "dev"
# - Use test Redshift cluster
```

### Phase 2: Test Individual Subagents

Test each subagent independently before testing the orchestrator:

**Test Assessment Subagent:**
```bash
atx-cli invoke-agent \
  --agent-id redshift-assessment-subagent \
  --message "Analyze cluster test-cluster-01 in us-east-2" \
  --customer-account-id 188199011335
```

**Test Scoring Subagent:**
```bash
atx-cli invoke-agent \
  --agent-id redshift-scoring-subagent \
  --message "Score cluster test-cluster-01 in us-east-2" \
  --customer-account-id 188199011335
```

**Test Architecture Subagent:**
```bash
atx-cli invoke-agent \
  --agent-id redshift-architecture-subagent \
  --message "Design multi-warehouse architecture for ETL and analytics workloads" \
  --customer-account-id 188199011335
```

**Test Execution Subagent:**
```bash
atx-cli invoke-agent \
  --agent-id redshift-execution-subagent \
  --message "Create migration plan for cluster test-cluster-01" \
  --customer-account-id 188199011335
```

### Phase 3: Test Orchestrator

Once subagents work individually, test the orchestrator:

```bash
atx-cli invoke-agent \
  --agent-id redshift-orchestrator \
  --message "Analyze cluster test-cluster-01 in us-east-2" \
  --customer-account-id 188199011335
```

Monitor logs to verify:
- Orchestrator receives request
- Orchestrator invokes assessment subagent
- Assessment subagent returns results
- Orchestrator presents results to user

### Phase 4: Test Full Workflow

Test the complete modernization workflow:

```bash
atx-cli invoke-agent \
  --agent-id redshift-orchestrator \
  --message "I want to modernize my Redshift cluster test-cluster-01 in us-east-2. Please perform a complete assessment, scoring, architecture design, and create a migration plan." \
  --customer-account-id 188199011335
```

Verify:
- Assessment phase completes
- Scoring phase completes
- Architecture design phase completes
- Execution planning phase completes
- All results are coherent and actionable

## What About "Local" Docker Testing?

### When Docker "Local Testing" Makes Sense

Docker local testing is useful for:
- **Unit testing** - Test individual functions without AWS
- **Integration testing** - Test agent logic with mocked AWS responses
- **Development iteration** - Quick feedback on code changes

### When It Doesn't Make Sense

Docker local testing is NOT useful for:
- **Testing against real Redshift clusters** - Clusters are in AWS
- **Testing ATX agent-to-agent communication** - Requires ATX platform
- **Testing end-to-end workflows** - Requires full AWS environment

### The Truth About Docker Compose

The `docker-compose.yml` we created would:
1. Start agents in containers on your laptop
2. Agents would still need AWS credentials
3. Agents would still connect to AWS Redshift over the internet
4. Agents would still need ATX MCP server (which may not work locally)

**It's not really "local" testing - it's just running containers locally that connect to AWS.**

## Recommended: Skip Docker, Deploy to AWS

### Fastest Path to Testing

1. **Package code** (2 minutes)
   ```bash
   ./package-all.sh
   ```

2. **Upload to S3** (5 minutes)
   ```bash
   aws s3 cp packages/*.zip s3://...
   ```

3. **Deploy to Bedrock** (20 minutes)
   - Via console or CLI
   - Bedrock builds containers

4. **Test in AWS** (10 minutes)
   ```bash
   atx-cli invoke-agent --agent-id redshift-orchestrator --message "..."
   ```

**Total: ~40 minutes to first test**

Compare to Docker "local" testing:
1. Install Docker (30 minutes)
2. Build images (10 minutes)
3. Configure AWS credentials for containers (10 minutes)
4. Configure ATX MCP server (may not work locally)
5. Start containers (5 minutes)
6. Test (10 minutes)
7. Still need to deploy to AWS for real testing

**Total: ~1+ hours, and you still need to deploy to AWS**

## Unit Testing (Actually Local)

If you want true local testing without AWS, write unit tests:

### Example Unit Test

```python
# tests/test_redshift_tools.py
import pytest
from unittest.mock import Mock, patch
from tools.redshift_tools import analyze_redshift_cluster

@patch('tools.redshift_tools.boto3.client')
def test_analyze_redshift_cluster(mock_boto3):
    # Mock AWS response
    mock_client = Mock()
    mock_client.describe_clusters.return_value = {
        'Clusters': [{
            'ClusterIdentifier': 'test-cluster',
            'NodeType': 'ra3.4xlarge',
            'NumberOfNodes': 4,
            'ClusterStatus': 'available',
            'Encrypted': True,
            'PubliclyAccessible': False,
        }]
    }
    mock_boto3.return_value = mock_client
    
    # Test function
    result = analyze_redshift_cluster('test-cluster', 'us-east-2')
    
    # Assertions
    assert result['cluster_identifier'] == 'test-cluster'
    assert result['node_type'] == 'ra3.4xlarge'
    assert result['encrypted'] == True
```

Run unit tests locally:
```bash
pytest tests/
```

This is true local testing - no AWS needed!

## Testing Checklist

### Before Deployment
- [ ] Unit tests pass locally
- [ ] Code compiles (python -m py_compile)
- [ ] Requirements.txt is complete

### After Deployment to Dev
- [ ] Assessment subagent works independently
- [ ] Scoring subagent works independently
- [ ] Architecture subagent works independently
- [ ] Execution subagent works independently
- [ ] Orchestrator can invoke each subagent
- [ ] Full workflow completes end-to-end

### Before Production
- [ ] Test with multiple Redshift clusters
- [ ] Test with different cluster configurations
- [ ] Test error handling (invalid cluster ID, etc.)
- [ ] Test conversation isolation (multiple customers)
- [ ] Test namespace-based session IDs
- [ ] Monitor CloudWatch logs for errors
- [ ] Verify IAM permissions are least-privilege

## Monitoring During Testing

### CloudWatch Logs

**Orchestrator:**
```bash
aws logs tail /aws/bedrock/agents/redshift-orchestrator \
  --follow
```

**Subagents:**
```bash
aws logs tail /aws/bedrock/agents/redshift-assessment-subagent \
  --follow
```

### ATX Agent Instance Status

```bash
# Get instance status
atx-cli get-agent-instance --agent-instance-id <instance-id>

# List recent invocations
atx-cli list-agent-instances --agent-id redshift-orchestrator
```

## Summary

**Don't bother with Docker "local testing"** - it's not really local since you need AWS anyway.

**Instead:**
1. Write unit tests for true local testing (no AWS needed)
2. Deploy to AWS dev environment for integration testing
3. Test against real Redshift clusters in AWS
4. Monitor CloudWatch logs
5. Iterate quickly by redeploying

This is faster, simpler, and more realistic than Docker "local" testing.

## Updated Recommendation

**For Development:**
- Write unit tests (run locally with pytest)
- Deploy to AWS dev environment
- Test against test Redshift clusters
- Iterate quickly

**For Production:**
- Deploy to AWS production environment
- Test with real customer clusters
- Monitor and gather feedback
- Iterate based on real usage

No Docker needed! 🚀
