#!/bin/bash
# Deploy Redshift Migration Agent to AWS ECS Fargate

set -e

echo "🚀 Deploying Redshift Migration Agent to AWS ECS Fargate"
echo "=========================================================="

# Configuration
AWS_REGION="us-east-2"
AWS_ACCOUNT_ID="${AWS::AccountId}"
ECR_REPO_NAME="redshift-migration-agent"
CLUSTER_NAME="redshift-agent-cluster"
SERVICE_NAME="redshift-agent-service"
TASK_FAMILY="redshift-agent-task"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${YELLOW}Step 1: Creating ECR Repository${NC}"
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository \
  --repository-name $ECR_REPO_NAME \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true

echo -e "${GREEN}✓ ECR repository ready${NC}"

echo ""
echo -e "${YELLOW}Step 2: Building and Pushing Docker Image${NC}"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
cd ..
docker build -t $ECR_REPO_NAME .

# Tag and push
docker tag $ECR_REPO_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest

echo -e "${GREEN}✓ Image pushed to ECR${NC}"

echo ""
echo -e "${YELLOW}Step 3: Creating IAM Roles${NC}"

# Create task execution role
aws iam get-role --role-name ecsTaskExecutionRole 2>/dev/null || \
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://aws_deploy/ecs-trust-policy.json

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy 2>/dev/null || true

# Create task role
aws iam get-role --role-name RedshiftAgentTaskRole 2>/dev/null || \
aws iam create-role \
  --role-name RedshiftAgentTaskRole \
  --assume-role-policy-document file://aws_deploy/ecs-trust-policy.json

aws iam put-role-policy \
  --role-name RedshiftAgentTaskRole \
  --policy-name RedshiftAgentPolicy \
  --policy-document file://aws_deploy/task-role-policy.json

echo -e "${GREEN}✓ IAM roles configured${NC}"

echo ""
echo -e "${YELLOW}Step 4: Creating CloudWatch Log Group${NC}"

aws logs create-log-group --log-group-name /ecs/redshift-agent --region $AWS_REGION 2>/dev/null || \
echo "Log group already exists"

echo -e "${GREEN}✓ Log group ready${NC}"

echo ""
echo -e "${YELLOW}Step 5: Registering Task Definition${NC}"

aws ecs register-task-definition \
  --cli-input-json file://aws_deploy/ecs-task-definition.json \
  --region $AWS_REGION

echo -e "${GREEN}✓ Task definition registered${NC}"

echo ""
echo -e "${YELLOW}Step 6: Creating ECS Cluster${NC}"

aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION 2>/dev/null | grep -q "ACTIVE" || \
aws ecs create-cluster \
  --cluster-name $CLUSTER_NAME \
  --region $AWS_REGION

echo -e "${GREEN}✓ Cluster ready${NC}"

echo ""
echo -e "${YELLOW}Step 7: Getting VPC Configuration${NC}"

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION)
echo "Using VPC: $VPC_ID"

# Get subnets
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text --region $AWS_REGION | tr '\t' ',')
echo "Using subnets: $SUBNETS"

# Create or get security group
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=redshift-agent-sg" "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text --region $AWS_REGION 2>/dev/null)

if [ "$SG_ID" == "None" ] || [ -z "$SG_ID" ]; then
  echo "Creating security group..."
  SG_ID=$(aws ec2 create-security-group \
    --group-name redshift-agent-sg \
    --description "Security group for Redshift Migration Agent" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text)
  
  # Allow inbound HTTP
  aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION
fi

echo "Using security group: $SG_ID"

echo ""
echo -e "${YELLOW}Step 8: Creating ECS Service${NC}"

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query "services[0].status" --output text 2>/dev/null)

if [ "$SERVICE_EXISTS" == "ACTIVE" ]; then
  echo "Service already exists, updating..."
  aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $TASK_FAMILY \
    --region $AWS_REGION
else
  echo "Creating new service..."
  aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --task-definition $TASK_FAMILY \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --region $AWS_REGION
fi

echo -e "${GREEN}✓ Service deployed${NC}"

echo ""
echo "=========================================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================================="
echo ""
echo "Your agent is now deploying on ECS Fargate."
echo ""
echo "To get the public IP:"
echo "  aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $AWS_REGION"
echo "  aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks <task-arn> --region $AWS_REGION"
echo ""
echo "To view logs:"
echo "  aws logs tail /ecs/redshift-agent --follow --region $AWS_REGION"
echo ""
echo "To update the service:"
echo "  ./deploy-to-ecs.sh"
echo ""
echo "Estimated cost: ~\$30-50/month"
