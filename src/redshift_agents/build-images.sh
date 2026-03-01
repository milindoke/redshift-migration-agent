#!/bin/bash

# Simple script to build all container images with Finch

set -e

echo "Building Redshift Modernization Agent Images..."
echo "================================================"
echo

# Build orchestrator
echo "[1/5] Building orchestrator..."
finch build -t redshift-orchestrator:latest \
    -f src/redshift_agents/docker/Dockerfile.orchestrator \
    .

echo "✓ Orchestrator built"
echo

# Build assessment
echo "[2/5] Building assessment subagent..."
finch build -t redshift-assessment:latest \
    -f src/redshift_agents/docker/Dockerfile.assessment \
    .

echo "✓ Assessment built"
echo

# Build scoring
echo "[3/5] Building scoring subagent..."
finch build -t redshift-scoring:latest \
    -f src/redshift_agents/docker/Dockerfile.scoring \
    .

echo "✓ Scoring built"
echo

# Build architecture
echo "[4/5] Building architecture subagent..."
finch build -t redshift-architecture:latest \
    -f src/redshift_agents/docker/Dockerfile.architecture \
    .

echo "✓ Architecture built"
echo

# Build execution
echo "[5/5] Building execution subagent..."
finch build -t redshift-execution:latest \
    -f src/redshift_agents/docker/Dockerfile.execution \
    .

echo "✓ Execution built"
echo

echo "================================================"
echo "All images built successfully! 🎉"
echo
echo "Images:"
finch images | grep redshift
echo
echo "Next steps:"
echo "1. Configure AWS credentials (service-account and customer-account profiles)"
echo "2. Run ./src/redshift_agents/deploy-with-finch.sh to push to ECR"
echo "3. Deploy to Bedrock AgentCore via console"
