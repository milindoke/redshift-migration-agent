#!/bin/bash
# Build all Redshift Modernization Agent Docker images

set -e

echo "Building Redshift Modernization Agents..."
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Build orchestrator
echo -e "${BLUE}Building orchestrator...${NC}"
docker build -f Dockerfile.orchestrator -t redshift-orchestrator:latest .
echo -e "${GREEN}✓ Orchestrator built${NC}"

# Build assessment subagent
echo -e "${BLUE}Building assessment subagent...${NC}"
docker build -f Dockerfile.assessment -t redshift-assessment:latest .
echo -e "${GREEN}✓ Assessment subagent built${NC}"

# Build scoring subagent
echo -e "${BLUE}Building scoring subagent...${NC}"
docker build -f Dockerfile.scoring -t redshift-scoring:latest .
echo -e "${GREEN}✓ Scoring subagent built${NC}"

# Build architecture subagent
echo -e "${BLUE}Building architecture subagent...${NC}"
docker build -f Dockerfile.architecture -t redshift-architecture:latest .
echo -e "${GREEN}✓ Architecture subagent built${NC}"

# Build execution subagent
echo -e "${BLUE}Building execution subagent...${NC}"
docker build -f Dockerfile.execution -t redshift-execution:latest .
echo -e "${GREEN}✓ Execution subagent built${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "All images built successfully!"
echo "==========================================${NC}"
echo ""
echo "Images created:"
docker images | grep redshift

echo ""
echo "Next steps:"
echo "1. Test locally: docker-compose up -d"
echo "2. Push to ECR: See SIMPLIFIED_DEPLOYMENT.md"
echo "3. Deploy to Bedrock AgentCore"
