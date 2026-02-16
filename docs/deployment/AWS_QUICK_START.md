# AWS Deployment - Quick Start

Deploy your Redshift Migration Agent to AWS in minutes.

## 🚀 One-Command Deployment

```bash
./deploy_to_aws.sh
```

Choose your option and the script handles everything!

---

## Option 1: ECS Fargate (Recommended)

**Best for:** Production, always-on service

```bash
./aws_deploy/deploy-to-ecs.sh
```

**What it does:**
- Creates ECR repository
- Builds and pushes Docker image
- Creates IAM roles
- Deploys to ECS Fargate
- Sets up networking and security groups

**Access:** Get public IP from ECS console or CLI

**Cost:** ~$30-50/month

---

## Option 2: AWS Lambda (Serverless)

**Best for:** Sporadic usage, cost optimization

```bash
./aws_deploy/deploy-to-lambda.sh
```

**What it does:**
- Packages Lambda deployment
- Creates IAM role
- Deploys Lambda function
- Creates function URL

**Access:** Function URL provided after deployment

**Cost:** ~$0-20/month (pay per request)

---

## Quick Test

After deployment, test your agent:

### ECS Fargate
```bash
# Get task IP
TASK_ARN=$(aws ecs list-tasks --cluster redshift-agent-cluster --service-name redshift-agent-service --query 'taskArns[0]' --output text)
TASK_IP=$(aws ecs describe-tasks --cluster redshift-agent-cluster --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

# Test
curl -X POST http://$TASK_IP:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List my Redshift clusters"}'
```

### Lambda
```bash
# Get function URL
FUNCTION_URL=$(aws lambda get-function-url-config --function-name redshift-migration-agent --query 'FunctionUrl' --output text)

# Test
curl -X POST $FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{"message": "List my Redshift clusters"}'
```

---

## Monitoring

### View Logs

**ECS:**
```bash
aws logs tail /ecs/redshift-agent --follow
```

**Lambda:**
```bash
aws logs tail /aws/lambda/redshift-migration-agent --follow
```

### CloudWatch Metrics

Go to CloudWatch console to see:
- Request count
- Error rate
- Response time
- Bedrock API usage

---

## Updating Your Deployment

### ECS
```bash
# Rebuild and push image
./aws_deploy/deploy-to-ecs.sh

# ECS will automatically deploy new version
```

### Lambda
```bash
# Redeploy function
./aws_deploy/deploy-to-lambda.sh
```

---

## Cost Breakdown

| Service | Monthly Cost | Best For |
|---------|-------------|----------|
| ECS Fargate | $30-50 | Production, 24/7 |
| Lambda | $0-20 | Sporadic use |
| App Runner | $25-40 | Easy deployment |
| EC2 t3.small | $15 | Budget option |

---

## Troubleshooting

### ECS Task Won't Start
- Check IAM roles have correct permissions
- Verify security group allows port 8000
- Check CloudWatch logs for errors

### Lambda Timeout
- Increase timeout to 300 seconds
- Increase memory to 1024 MB
- Check Bedrock model access

### Can't Access API
- Verify security group rules
- Check if public IP is assigned
- Ensure health check is passing

---

## Security Checklist

- [ ] IAM roles use least privilege
- [ ] Security groups restrict access
- [ ] CloudWatch logging enabled
- [ ] VPC endpoints configured (optional)
- [ ] API authentication added (production)

---

## Next Steps

1. Deploy using `./deploy_to_aws.sh`
2. Test the deployment
3. Set up monitoring
4. Configure auto-scaling (ECS)
5. Add authentication (production)

For detailed information, see **AWS_DEPLOYMENT.md**.
