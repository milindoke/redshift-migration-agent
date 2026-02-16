#!/usr/bin/env python3
"""
Test the Lambda handler locally to debug issues
"""

import json
from lambda_handler import lambda_handler

# Test event
event = {
    "message": "List my Redshift clusters in us-east-2"
}

# Mock context
class MockContext:
    def __init__(self):
        self.function_name = "redshift-migration-agent"
        self.memory_limit_in_mb = 2048
        self.invoked_function_arn = "arn:aws:lambda:us-east-2:123456789012:function:redshift-migration-agent"
        self.aws_request_id = "test-request-id"

context = MockContext()

print("Testing Lambda handler locally...")
print(f"Event: {json.dumps(event, indent=2)}")
print("\n" + "="*50 + "\n")

try:
    response = lambda_handler(event, context)
    print("Response:")
    print(json.dumps(response, indent=2))
    
    if response.get('statusCode') == 200:
        body = json.loads(response['body'])
        print("\n" + "="*50)
        print("Agent Response:")
        print(body.get('response', 'No response'))
    else:
        print("\n❌ Error occurred")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()
