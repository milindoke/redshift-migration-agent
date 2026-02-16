#!/bin/bash

# Quick test of the chat interface

echo "Testing chat interface..."
echo ""

# Send a test message via the chat script
python3 -c "
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-2')

response = lambda_client.invoke(
    FunctionName='redshift-migration-agent',
    InvocationType='RequestResponse',
    Payload=json.dumps({'message': 'Hello! Just testing. Can you confirm you are working?'})
)

payload = json.loads(response['Payload'].read())
body = json.loads(payload.get('body', '{}'))
agent_response = body.get('response', 'No response')

print('Agent Response:')
print('=' * 70)
print(agent_response)
print('=' * 70)
print()
print('✅ Chat interface is working!')
print()
print('Start chatting with: python3 chat_with_agent.py')
"
