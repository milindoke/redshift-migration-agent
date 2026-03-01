#!/bin/bash
# Package all agents for deployment (no Docker needed!)

set -e

echo "Packaging Redshift Modernization Agents..."
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create packages directory
mkdir -p packages

# Package orchestrator
echo -e "${BLUE}Packaging orchestrator...${NC}"
zip -r packages/orchestrator-deployment.zip \
  orchestrator/ \
  tools/ \
  requirements.txt \
  __init__.py \
  -x "*.pyc" -x "__pycache__/*" -x "*.md" -x ".env*" -x "docker-compose.yml" -x "Dockerfile*"
echo -e "${GREEN}✓ Orchestrator packaged${NC}"

# Package assessment subagent
echo -e "${BLUE}Packaging assessment subagent...${NC}"
zip -r packages/assessment-deployment.zip \
  subagents/assessment.py \
  subagents/__init__.py \
  tools/ \
  requirements.txt \
  __init__.py \
  -x "*.pyc" -x "__pycache__/*"
echo -e "${GREEN}✓ Assessment subagent packaged${NC}"

# Package scoring subagent
echo -e "${BLUE}Packaging scoring subagent...${NC}"
zip -r packages/scoring-deployment.zip \
  subagents/scoring.py \
  subagents/__init__.py \
  tools/ \
  requirements.txt \
  __init__.py \
  -x "*.pyc" -x "__pycache__/*"
echo -e "${GREEN}✓ Scoring subagent packaged${NC}"

# Package architecture subagent
echo -e "${BLUE}Packaging architecture subagent...${NC}"
zip -r packages/architecture-deployment.zip \
  subagents/architecture.py \
  subagents/__init__.py \
  tools/ \
  requirements.txt \
  __init__.py \
  -x "*.pyc" -x "__pycache__/*"
echo -e "${GREEN}✓ Architecture subagent packaged${NC}"

# Package execution subagent
echo -e "${BLUE}Packaging execution subagent...${NC}"
zip -r packages/execution-deployment.zip \
  subagents/execution.py \
  subagents/__init__.py \
  tools/ \
  requirements.txt \
  __init__.py \
  -x "*.pyc" -x "__pycache__/*"
echo -e "${GREEN}✓ Execution subagent packaged${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "All packages created successfully!"
echo "==========================================${NC}"
echo ""
echo "Packages created in ./packages/:"
ls -lh packages/

echo ""
echo "Next steps:"
echo "1. Upload to S3:"
echo "   aws s3 cp packages/orchestrator-deployment.zip s3://YOUR-BUCKET/orchestrator/ --profile service-account"
echo "   aws s3 cp packages/assessment-deployment.zip s3://YOUR-BUCKET/assessment/ --profile customer-account"
echo "   (repeat for other subagents)"
echo ""
echo "2. Deploy via Bedrock AgentCore Console:"
echo "   - Create agent"
echo "   - Point to S3 location"
echo "   - Bedrock builds container automatically"
echo ""
echo "3. Register with ATX:"
echo "   atx-cli register-agent --agent-id redshift-orchestrator --agent-type orchestrator"
echo ""
echo "See DEPLOY_WITHOUT_DOCKER.md for detailed instructions."
