#!/bin/bash
# Master AWS Deployment Script for Redshift Migration Agent

set -e

echo "🚀 AWS Deployment for Redshift Migration Agent"
echo "==============================================="
echo ""
echo "Choose your deployment option:"
echo ""
echo "1) ECS Fargate (Recommended for production)"
echo "   - Always-on service"
echo "   - Auto-scaling"
echo "   - Cost: ~\$30-50/month"
echo ""
echo "2) AWS Lambda (Recommended for low usage)"
echo "   - Serverless, pay-per-request"
echo "   - Auto-scaling"
echo "   - Cost: ~\$0-20/month"
echo ""
echo "3) App Runner (Easiest deployment)"
echo "   - Fully managed"
echo "   - Auto-scaling"
echo "   - Cost: ~\$25-40/month"
echo ""
echo "4) EC2 Instance (Full control)"
echo "   - Traditional VM"
echo "   - Manual scaling"
echo "   - Cost: ~\$15-30/month"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Deploying to ECS Fargate..."
        ./aws_deploy/deploy-to-ecs.sh
        ;;
    
    2)
        echo ""
        echo "Deploying to AWS Lambda..."
        ./aws_deploy/deploy-to-lambda.sh
        ;;
    
    3)
        echo ""
        echo "Deploying to App Runner..."
        echo ""
        echo "App Runner deployment requires:"
        echo "1. Push image to ECR (run ECS deployment first)"
        echo "2. Create App Runner service in AWS Console"
        echo ""
        echo "Or use AWS CLI:"
        echo "  aws apprunner create-service \\"
        echo "    --service-name redshift-agent \\"
        echo "    --source-configuration file://aws_deploy/apprunner-config.json"
        ;;
    
    4)
        echo ""
        echo "EC2 Deployment Steps:"
        echo ""
        echo "1. Launch EC2 instance:"
        echo "   aws ec2 run-instances \\"
        echo "     --image-id ami-0c55b159cbfafe1f0 \\"
        echo "     --instance-type t3.medium \\"
        echo "     --key-name your-key-pair \\"
        echo "     --security-group-ids sg-xxx \\"
        echo "     --user-data file://aws_deploy/ec2-user-data.sh"
        echo ""
        echo "2. SSH to instance and run:"
        echo "   git clone your-repo"
        echo "   cd redshift-migration-agent"
        echo "   ./deploy_agent.sh"
        echo "   python api_server.py"
        ;;
    
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "==============================================="
echo "For detailed AWS deployment guide, see:"
echo "  AWS_DEPLOYMENT.md"
