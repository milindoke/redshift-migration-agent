#!/bin/bash

# Wrapper script to run chat with proper Python environment

# Check if venv exists
if [ -d "venv" ]; then
    source venv/bin/activate
    python3 chat_with_agent.py "$@"
else
    echo "⚠️  Virtual environment not found. Using system Python..."
    python3 chat_with_agent.py "$@"
fi
