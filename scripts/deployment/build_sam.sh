#!/bin/bash
# Build SAM application for deployment

set -e

echo "Building SAM application..."

# Install dependencies
pip install -r requirements-agent.txt -t .

# Build SAM
sam build

echo "✓ Build complete"
echo ""
echo "To deploy:"
echo "  sam deploy --guided"
