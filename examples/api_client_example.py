#!/usr/bin/env python3
"""
Example client for the Redshift Migration Agent API

Shows how to interact with the agent via REST API.
"""

import requests
import json

# API endpoint
API_URL = "http://localhost:8000"

def chat(message: str, session_id: str = None):
    """Send a message to the agent."""
    response = requests.post(
        f"{API_URL}/chat",
        json={
            "message": message,
            "session_id": session_id
        }
    )
    response.raise_for_status()
    return response.json()

def health_check():
    """Check if the API is healthy."""
    response = requests.get(f"{API_URL}/health")
    response.raise_for_status()
    return response.json()

def main():
    """Example usage of the API client."""
    
    # Check health
    print("Checking API health...")
    health = health_check()
    print(f"Status: {health['status']}")
    print(f"Agent Ready: {health['agent_ready']}")
    print()
    
    # Example conversations
    session_id = "example-session-1"
    
    examples = [
        "List all Redshift clusters in us-east-2",
        "What's the simplest way to migrate a cluster?",
        "Extract configuration from cluster my-cluster-1 in us-east-2",
    ]
    
    for message in examples:
        print(f"You: {message}")
        result = chat(message, session_id)
        print(f"Agent: {result['response']}")
        print()

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API server.")
        print("Make sure the server is running: python api_server.py")
    except Exception as e:
        print(f"Error: {e}")
