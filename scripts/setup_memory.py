#!/usr/bin/env python3
"""
Setup script for AgentCore Memory

This script creates the memory resource for the Redshift Migration Agent.
Run this once after deploying the Lambda function.
"""

import boto3
import sys
from bedrock_agentcore.memory import MemoryClient

def setup_memory(region='us-east-2'):
    """Create AgentCore Memory for the Redshift Migration Agent."""
    
    print("🧠 Setting up AgentCore Memory for Redshift Migration Agent")
    print("=" * 60)
    
    try:
        client = MemoryClient(region_name=region)
        
        print(f"\n📍 Region: {region}")
        print("🔨 Creating memory resource...")
        
        memory = client.create_memory(
            name="RedshiftMigrationMemory",
            description="Persistent memory for Redshift migration conversations and progress tracking",
            strategies=[
                {
                    "summaryMemoryStrategy": {
                        "name": "MigrationSummarizer",
                        "namespaces": ["/summaries/{actorId}/{sessionId}/"]
                    }
                },
                {
                    "userPreferenceMemoryStrategy": {
                        "name": "UserPreferences",
                        "namespaces": ["/preferences/{actorId}/"]
                    }
                },
                {
                    "semanticMemoryStrategy": {
                        "name": "MigrationFacts",
                        "namespaces": ["/facts/{actorId}/"]
                    }
                }
            ]
        )
        
        memory_id = memory.get('id')
        
        print(f"\n✅ Memory created successfully!")
        print(f"\n📋 Memory ID: {memory_id}")
        print(f"\n🔧 Next steps:")
        print(f"   1. Update your Lambda function environment variable:")
        print(f"      AGENTCORE_MEMORY_ID={memory_id}")
        print(f"\n   2. Or run this command:")
        print(f"      aws lambda update-function-configuration \\")
        print(f"        --function-name redshift-migration-agent \\")
        print(f"        --environment Variables={{AGENTCORE_MEMORY_ID={memory_id}}} \\")
        print(f"        --region {region}")
        print(f"\n   3. Test with session_id:")
        print(f"      aws lambda invoke \\")
        print(f"        --function-name redshift-migration-agent \\")
        print(f"        --payload '{{\"message\":\"List clusters\",\"session_id\":\"test-session\"}}' \\")
        print(f"        response.json")
        print(f"\n🎉 Setup complete!")
        
        return memory_id
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup AgentCore Memory for Redshift Migration Agent')
    parser.add_argument('--region', default='us-east-2', help='AWS region (default: us-east-2)')
    
    args = parser.parse_args()
    
    setup_memory(region=args.region)
