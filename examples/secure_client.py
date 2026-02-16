#!/usr/bin/env python3
"""
Secure client for Redshift Migration Agent Lambda

Uses IAM authentication to invoke the Lambda function securely.
"""

import boto3
import json
import os

class RedshiftAgentClient:
    """Secure client for the Redshift Migration Agent."""
    
    def __init__(self, region='us-east-2'):
        """
        Initialize the client.
        
        Requires AWS credentials with lambda:InvokeFunction permission.
        Configure with:
          - AWS CLI: aws configure
          - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
          - IAM role (if running on EC2/ECS/Lambda)
        """
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.function_name = 'redshift-migration-agent'
        self.region = region
    
    def chat(self, message: str) -> dict:
        """
        Send a message to the agent.
        
        Args:
            message: The message/question for the agent
            
        Returns:
            dict with 'response' key containing the agent's response
        """
        payload = {
            'message': message
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('FunctionError'):
                return {
                    'error': True,
                    'message': response_payload.get('errorMessage', 'Unknown error'),
                    'type': response_payload.get('errorType', 'Error')
                }
            
            # Parse the body if it's from API Gateway format
            if 'body' in response_payload:
                body = json.loads(response_payload['body'])
                return body
            
            return response_payload
            
        except Exception as e:
            return {
                'error': True,
                'message': str(e),
                'type': type(e).__name__
            }
    
    def list_clusters(self, region=None):
        """List Redshift clusters."""
        region_str = f" in {region}" if region else ""
        return self.chat(f"List all Redshift clusters{region_str}")
    
    def list_namespaces(self, region=None):
        """List Redshift Serverless namespaces."""
        region_str = f" in {region}" if region else ""
        return self.chat(f"List all Redshift Serverless namespaces{region_str}")
    
    def extract_config(self, cluster_id, region=None):
        """Extract configuration from a cluster."""
        region_str = f" in {region}" if region else ""
        return self.chat(f"Extract configuration from cluster {cluster_id}{region_str}")
    
    def migrate(self, cluster_id, region=None):
        """Start a migration."""
        region_str = f" in {region}" if region else ""
        return self.chat(f"Migrate cluster {cluster_id} to serverless{region_str}")


def main():
    """Example usage of the secure client."""
    
    # Check for credentials
    if not (os.getenv('AWS_ACCESS_KEY_ID') or os.path.exists(os.path.expanduser('~/.aws/credentials'))):
        print("❌ AWS credentials not found!")
        print("")
        print("Please configure AWS credentials:")
        print("  1. Run: aws configure")
        print("  2. Or set environment variables:")
        print("     export AWS_ACCESS_KEY_ID=your_key")
        print("     export AWS_SECRET_ACCESS_KEY=your_secret")
        print("")
        print("  3. Or load from file:")
        print("     source .agent-credentials")
        return
    
    # Create client
    print("🔒 Connecting to Redshift Migration Agent (secure)")
    print("=" * 60)
    
    client = RedshiftAgentClient(region='us-east-2')
    
    # Example 1: List clusters
    print("\n📋 Listing Redshift clusters...")
    result = client.list_clusters(region='us-east-2')
    
    if result.get('error'):
        print(f"❌ Error: {result.get('message')}")
    else:
        print(f"✓ Response: {result.get('response', result)[:200]}...")
    
    # Example 2: Ask a question
    print("\n💬 Asking about migration...")
    result = client.chat("What's the simplest way to migrate a cluster?")
    
    if result.get('error'):
        print(f"❌ Error: {result.get('message')}")
    else:
        print(f"✓ Response: {result.get('response', result)[:200]}...")
    
    print("\n" + "=" * 60)
    print("✅ Secure communication successful!")


if __name__ == "__main__":
    main()
