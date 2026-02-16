#!/usr/bin/env python3
"""
Example: Using the Redshift Migration Strand Agent programmatically
"""

from redshift_agent import create_agent

# Create the agent
agent = create_agent()

# Example 1: Ask for help
print("Example 1: Getting help")
print("=" * 50)
response = agent("What's the simplest way to migrate a cluster?")
print(response)
print("\n")

# Example 2: Extract configuration
print("Example 2: Extract cluster configuration")
print("=" * 50)
response = agent("Extract configuration from cluster my-cluster-1 in us-east-1")
print(response)
print("\n")

# Example 3: Full migration with conversation
print("Example 3: Full migration conversation")
print("=" * 50)
agent("I want to migrate cluster prod-db to serverless")
agent("The cluster is in us-west-2")
response = agent("Yes, migrate the data too")
print(response)
