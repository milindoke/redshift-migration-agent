#!/bin/bash
# Deployment script for Redshift Migration Strand Agent

set -e

echo "🚀 Deploying Redshift Migration Strand Agent"
echo "=============================================="

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Check Python version
echo ""
echo "Checking Python version..."
PYTHON_VERSION=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python 3.10+ required, found Python $PYTHON_VERSION"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"

# Step 1: Install migration tool
echo ""
echo "Step 1: Installing redshift-migrate CLI tool..."
pip install -e .

# Step 2: Install Strand dependencies
echo ""
echo "Step 2: Installing Strand agent dependencies..."
pip install -r requirements-agent.txt

# Step 3: Check AWS credentials
echo ""
echo "Step 3: Checking AWS credentials..."
if [ -z "$AWS_BEDROCK_API_KEY" ] && [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "⚠️  Warning: No AWS credentials found!"
    echo ""
    echo "Please set one of:"
    echo "  - AWS_BEDROCK_API_KEY (for Bedrock API key)"
    echo "  - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (for AWS credentials)"
    echo ""
    echo "Example:"
    echo "  export AWS_BEDROCK_API_KEY=your_key"
    echo ""
    echo "You can continue and set credentials later."
else
    echo "✓ AWS credentials configured"
fi

# Step 4: Test the agent
echo ""
echo "Step 4: Testing agent installation..."
python -c "from redshift_agent import create_agent; print('✓ Agent created successfully')"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "To run the agent:"
echo "  source venv/bin/activate"
echo "  python redshift_agent.py"
echo ""
echo "To use programmatically:"
echo "  from redshift_agent import create_agent"
echo "  agent = create_agent()"
echo "  response = agent('Help me migrate my cluster')"
