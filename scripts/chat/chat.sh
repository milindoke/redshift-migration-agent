#!/bin/bash

# Wrapper script to run chat with proper Python environment

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Check if venv exists
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    python3 "$SCRIPT_DIR/chat_with_agent.py" "$@"
else
    echo "⚠️  Virtual environment not found. Using system Python..."
    python3 "$SCRIPT_DIR/chat_with_agent.py" "$@"
fi
