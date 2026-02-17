#!/bin/bash

# Wrapper script to run chat with proper Python environment

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Check if venv exists, create if not
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
    
    echo "📥 Installing dependencies..."
    source "$PROJECT_ROOT/venv/bin/activate"
    pip install --quiet --upgrade pip
    pip install --quiet boto3 rich
    echo "✅ Setup complete!"
    echo ""
else
    source "$PROJECT_ROOT/venv/bin/activate"
fi

python3 "$SCRIPT_DIR/chat_with_agent.py" "$@"
