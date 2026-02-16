# Deploying Redshift Migration Agent on AWS

Complete guide for deploying your agent on AWS with multiple service options.

---

## Option 1: AWS ECS Fargate (Recommended)

Serverless container deployment - no server management required.

### Prerequisites
- AWS CLI configured
- Docker installed
- ECR repository created

### Step 1: Push Image to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 497316421912.dkr.ecr.us-east-2.amazonaws.com

# Create repository
aws ecr create-repository --repository-name redshift-migration-agent --region us-east-2

# Build and tag
docker build -t redshift-migration-agent .
docker tag redshift-migration-agent:latest 497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-migration-agent:latest

# Push
docker push 497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-migration-agent:latest
```

### Step 2: Create ECS Task Definition

```bash
# Create task-definition.json (see below)
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### Step 3: Create ECS Service

```bash
# Create cluster
aws ecs create-cluster --cluster-name redshift-agent-cluster --region us-east-2

# Create service
aws ecs create-service \
  --cluster redshift-agent-cluster \
  --service-name redshift-agent-service \
  --task-definition redshift-agent-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region us-east-2
```

### Cost Estimate
- ~$30-50/month for 1 task running 24/7
- Pay only for what you use

---

## Option 2: AWS Lambda + API Gateway

Serverless function - pay per request.

### Step 1: Create Lambda Handler

Already created in `lambda_handler.py`. Package it:

```bash
# Create deployment package
mkdir lambda_package
pip install -r requirements-agent.txt -t lambda_package/
cp -r src/ lambda_package/
cp redshift_agent.py lambda_package/
cp lambda_handler.py lambda_package/

cd lambda_package
zip -r ../lambda_deployment.zip .
cd ..
```

### Step 2: Create Lambda Function

```bash
# Create IAM role first
aws iam create-role \
  --role-name RedshiftAgentLambdaRole \
  --assume-role-policy-document file://lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name RedshiftAgentLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name RedshiftAgentLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonRedshiftFullAccess

# Create function
aws lambda create-function \
  --function-name redshift-migration-agent \
  --runtime python3.11 \
  --role arn:aws:iam::497316421912:role/RedshiftAgentLambdaRole \
  --handler lambda_handler.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={AWS_REGION=us-east-2} \
  --region us-east-2
```

### Step 3: Create API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name "Redshift Migration Agent API" \
  --region us-east-2

# Configure integration (see AWS Console for easier setup)
```

### Cost Estimate
- First 1M requests/month: Free
- After: $0.20 per 1M requests
- Very cost-effective for low-medium usage

---

## Option 3: AWS App Runner

Easiest deployment - just point to your container.

### Deploy with App Runner

```bash
# Create App Runner service
aws apprunner create-service \
  --service-name redshift-agent \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "497316421912.dkr.ecr.us-east-2.amazonaws.com/redshift-migration-agent:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "AWS_REGION": "us-east-2"
        }
      }
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  }' \
  --region us-east-2
```

### Cost Estimate
- ~$25-40/month for always-on service
- Automatic scaling included

---

## Option 4: EC2 Instance

Traditional VM deployment.

### Launch EC2 Instance

```bash
# Launch instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxx \
  --subnet-id subnet-xxx \
  --iam-instance-profile Name=RedshiftAgentRole \
  --user-data file://user-data.sh \
  --region us-east-2
```

### User Data Script (user-data.sh)

```bash
#!/bin/bash
yum update -y
yum install -y docker git

# Start Docker
systemctl start docker
systemctl enable docker

# Clone and run
cd /home/ec2-user
git clone https://github.com/YOUR_USERNAME/redshift-migration-agent.git
cd redshift-migration-agent

# Run with Docker
docker-compose up -d
```

### Cost Estimate
- t3.medium: ~$30/month
- t3.small: ~$15/month (may be sufficient)

---

## Option 5: AWS Bedrock Agents (Native)

Deploy as a native Bedrock Agent with built-in capabilities.

### Architecture
- Bedrock Agent handles conversation
- Lambda functions for tools
- S3 for knowledge base (optional)

### Steps

1. **Create Lambda functions for each tool**
2. **Create OpenAPI schema**
3. **Configure Bedrock Agent**
4. **Deploy**

This is more complex but provides native AWS integration.

See `bedrock_agent_deployment.md` for detailed steps.

---

## Comparison Table

| Service | Cost/Month | Complexity | Scalability | Best For |
|---------|-----------|------------|-------------|----------|
| ECS Fargate | $30-50 | Medium | High | Production, always-on |
| Lambda | $0-20 | Low | Very High | Sporadic usage |
| App Runner | $25-40 | Very Low | High | Quick deployment |
| EC2 | $15-30 | Medium | Medium | Full control needed |
| Bedrock Agents | $10-30 | High | High | Native AWS integration |

---

## Recommended Architecture

For production deployment, I recommend:

```
Internet
    ↓
Application Load Balancer (ALB)
    ↓
ECS Fargate Service (2+ tasks)
    ↓
VPC with Private Subnets
    ↓
AWS Bedrock (Claude)
    ↓
Redshift Clusters/Serverless
```

### Benefits:
- High availability (multiple tasks)
- Auto-scaling
- Secure (private subnets)
- Load balanced
- Health checks

---

## Security Best Practices

### 1. Use IAM Roles (Not API Keys)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "redshift:Describe*",
        "redshift:List*",
        "redshift-serverless:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. Use VPC Endpoints

```bash
# Create VPC endpoint for Bedrock
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.us-east-2.bedrock-runtime \
  --route-table-ids rtb-xxx
```

### 3. Enable CloudWatch Logging

```bash
# Create log group
aws logs create-log-group --log-group-name /aws/redshift-agent

# Configure in task definition or Lambda
```

### 4. Use Secrets Manager

```bash
# Store sensitive data
aws secretsmanager create-secret \
  --name redshift-agent/config \
  --secret-string '{"api_key":"xxx"}'
```

---

## Monitoring & Observability

### CloudWatch Dashboards

```bash
# Create dashboard
aws cloudwatch put-dashboard \
  --dashboard-name RedshiftAgent \
  --dashboard-body file://dashboard.json
```

### Key Metrics to Monitor:
- Request count
- Error rate
- Response time
- Bedrock API calls
- Migration success rate

### Alarms

```bash
# Create alarm for errors
aws cloudwatch put-metric-alarm \
  --alarm-name redshift-agent-errors \
  --alarm-description "Alert on agent errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

---

## Quick Start Scripts

I'll create automated deployment scripts for each option in the next files.

---

## Cost Optimization Tips

1. **Use Lambda for low traffic** - Pay per request
2. **Use Fargate Spot** - Save up to 70%
3. **Right-size instances** - Start small, scale up
4. **Use caching** - Reduce Bedrock API calls
5. **Set up auto-scaling** - Scale down during off-hours

---

## Next Steps

1. Choose your deployment option
2. Run the corresponding deployment script
3. Configure monitoring
4. Test the deployment
5. Share the endpoint with users

For automated deployment, see the deployment scripts in the `aws_deploy/` directory.
