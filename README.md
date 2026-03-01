# Redshift Modernization Agents 🚀

AI-powered multi-agent system for comprehensive AWS Redshift modernization using AWS Transform (ATX) framework and Amazon Bedrock AgentCore.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## 🎯 What It Does

This multi-agent system helps you modernize AWS Redshift Provisioned clusters to Serverless by:

- ✅ **Automated Assessment**: Analyzes cluster configuration, performance, and usage patterns
- ✅ **Best Practices Scoring**: Evaluates security, performance, and cost (0-100 score, A-F grade)
- ✅ **Architecture Design**: Designs multi-warehouse topology with workload separation
- ✅ **Phased Migration Planning**: Creates 12-18 week implementation plan with validation gates
- ✅ **Cross-Account Security**: Customer data never leaves customer account
- ✅ **Conversation Isolation**: Namespace-based session management per customer

## 🏗️ Architecture

### Multi-Agent System

```
Service Account (Orchestrator)  ←→  Customer Account (4 Subagents)
     No Cluster Access                  Direct Cluster Access
          ↓                                      ↓
    Coordinates workflow              Assessment, Scoring,
    Maintains state                   Architecture, Execution
```

**5 Agents Total:**

1. **Orchestrator** (Service Account)
   - Coordinates modernization workflow
   - Maintains conversation state
   - NO direct access to customer clusters

2. **Assessment Agent** (Customer Account)
   - Analyzes cluster configuration
   - Extracts IAM roles, VPC, parameters
   - Evaluates usage patterns

3. **Scoring Agent** (Customer Account)
   - Evaluates best practices (0-100 score)
   - Security: 35%, Performance: 35%, Cost: 30%
   - Provides A-F grade with recommendations

4. **Architecture Agent** (Customer Account)
   - Designs multi-warehouse topology
   - Plans workload separation strategies
   - Recommends data sharing approach

5. **Execution Agent** (Customer Account)
   - Creates phased implementation plan
   - Defines validation gates
   - Estimates timeline (12-18 weeks)

### Technology Stack

- **Framework**: AWS Transform (ATX) BaseAgent SDK
- **AI Platform**: Amazon Bedrock AgentCore
- **Communication**: ATX MCP (Model Context Protocol)
- **Deployment**: Docker containers on Bedrock AgentCore
- **Language**: Python 3.12+

## 🚀 Quick Start

### Prerequisites

- AWS Account (2 accounts for cross-account setup)
- Docker images built and pushed to ECR
- Bedrock model access enabled (Claude Sonnet 4.5)
- IAM permissions for Bedrock AgentCore

### Deployment Status

✅ Code complete (5 agents)  
✅ Docker images built with Finch  
✅ Images pushed to ECR  
⏳ Next: Deploy to Bedrock AgentCore  

See [ECR_PUSH_SUCCESS.md](src/redshift_agents/ECR_PUSH_SUCCESS.md) for deployment instructions.

### Deploy to Bedrock AgentCore

**Step 1: Build Images** (if not already done)
```bash
cd src/redshift_agents
./deploy-with-finch.sh
# Select option 1: Build images only
```

**Step 2: Push to ECR** (if not already done)
```bash
./deploy-with-finch.sh
# Select option 3: Push existing images to ECR
```

**Step 3: Deploy to Bedrock**

Follow the detailed instructions in [src/redshift_agents/ECR_PUSH_SUCCESS.md](src/redshift_agents/ECR_PUSH_SUCCESS.md) to:
1. Create agents in Bedrock Console (~25 min)
2. Register agents with ATX (~2 min)
3. Test the system (~2 min)

## 💬 How to Use

### Example Conversation

```
You: Analyze my Redshift cluster 'prod-cluster-1' in account 188199011335

Orchestrator → Assessment Agent:
  [Extracts cluster configuration, IAM roles, VPC settings]

You: Score this cluster against best practices

Orchestrator → Scoring Agent:
  Security: 75/100 (B)
  Performance: 82/100 (B+)
  Cost: 68/100 (C+)
  Overall: 75/100 (B)
  
  Recommendations:
  - Enable encryption at rest
  - Configure automated snapshots
  - Optimize WLM queues

You: Design a multi-warehouse architecture

Orchestrator → Architecture Agent:
  Recommended Topology:
  - Analytics Workgroup (BI queries)
  - ETL Workgroup (data processing)
  - Ad-hoc Workgroup (exploratory)
  
  Data Sharing Strategy:
  - Shared namespace for all workgroups
  - Workload isolation via separate compute

You: Create an implementation plan

Orchestrator → Execution Agent:
  Phase 1 (Weeks 1-2): Assessment & Design
  Phase 2 (Weeks 3-6): Pilot workgroup
  Phase 3 (Weeks 7-12): Production migration
  Phase 4 (Weeks 13-16): Optimization
  Phase 5 (Weeks 17-18): Validation & cutover
```

## 🔒 Security Features

### Cross-Account Architecture

- **Service Account**: Orchestrator with NO cluster access
- **Customer Account**: Subagents with direct cluster access
- **Data Isolation**: Customer data never leaves customer account
- **IAM Roles**: Cross-account assume role with least privilege

### Conversation Isolation

- **Namespace-based Sessions**: `customer_account_id` required
- **Session IDs**: Format `{namespace}:{conversation_id}`
- **Memory Isolation**: Each customer has isolated conversation history

## 📊 Best Practices Scoring

### Scoring Criteria

**Security (35%)**
- Encryption at rest and in transit
- VPC configuration
- IAM roles and policies
- Audit logging enabled

**Performance (35%)**
- WLM queue configuration
- Automated snapshots
- Maintenance windows
- Query monitoring rules

**Cost (30%)**
- Right-sized compute
- Usage limits configured
- Automated scaling enabled
- Reserved capacity utilization

### Grade Scale

- **A (90-100)**: Excellent - Production ready
- **B (80-89)**: Good - Minor improvements needed
- **C (70-79)**: Fair - Several improvements recommended
- **D (60-69)**: Poor - Significant changes required
- **F (<60)**: Failing - Major overhaul needed

## 🛠️ Development

### Local Testing

```bash
cd src/redshift_agents

# Run unit tests
pytest tests/ -v

# Test individual agents locally
python -m orchestrator.orchestrator
python -m subagents.assessment
```

### Build Images

```bash
# Build all images
./build-images.sh

# Or use the comprehensive deployment script
./deploy-with-finch.sh
```

## 📚 Documentation

- **[ECR Push Success](src/redshift_agents/ECR_PUSH_SUCCESS.md)** - Current status & next steps
- **[Main Documentation](src/redshift_agents/README.md)** - Complete agent documentation
- **[Deployment Checklist](src/redshift_agents/docs/deployment-checklist.md)** - Step-by-step deployment
- **[Testing Guide](src/redshift_agents/docs/testing.md)** - Testing strategies
- **[Contributing](CONTRIBUTING.md)** - How to contribute

## � Cost Estimate

**Bedrock AgentCore**:
- Per-agent pricing: ~$0.10-0.50 per invocation
- 5 agents × average usage
- Estimated: $50-200/month (varies by usage)

**ECR Storage**:
- 5 Docker images × ~500MB each
- ~$0.10/GB/month
- Estimated: ~$0.25/month

**Total**: ~$50-200/month depending on usage

## 🔗 Related Projects

- [AWS Transform (ATX)](https://w.amazon.com/bin/view/AWS/Teams/Transform/)
- [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/)
- [AWS Redshift Documentation](https://docs.aws.amazon.com/redshift/)

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

## 📝 License

Apache 2.0 License - see [LICENSE](LICENSE)

## 🆘 Support

- 📖 [Documentation](src/redshift_agents/)
- 🐛 Report Issues (internal AWS channels)
- 💬 Discussions (AWS Transform team)

---

**Made with ❤️ by the AWS Transform team**

Deploy now and start modernizing! 🚀
