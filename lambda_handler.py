#!/usr/bin/env python3
"""
AWS Lambda handler for Redshift Migration Agent

Provides serverless execution of the agent via Lambda function with persistent memory support.

Expected event format:
{
    "message": "your message here",
    "session_id": "optional-session-id",  # For conversation continuity
    "actor_id": "optional-user-id"        # For user identification
}
"""

import json
import logging
import os
from datetime import datetime
from redshift_agent import create_agent

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cache for agent instances (keyed by session_id)
agent_cache = {}


def lambda_handler(event, context):
    """
    AWS Lambda handler for the Redshift Migration Agent.
    
    Expected event format:
    {
        "body": "{\"message\": \"your message here\", \"session_id\": \"optional-session-id\"}"
    }
    
    Or direct invocation:
    {
        "message": "your message here",
        "session_id": "optional-session-id",  # Auto-generated if not provided
        "actor_id": "optional-user-id"
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request - handle both API Gateway and direct invocation
        if 'body' in event:
            # API Gateway format
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            # Direct invocation
            body = event
        
        message = body.get('message', '')
        session_id = body.get('session_id')
        actor_id = body.get('actor_id')
        region = body.get('region', os.environ.get('AWS_REGION', 'us-east-2'))
        
        # Auto-generate session_id if not provided (use request ID for uniqueness)
        if not session_id:
            # Use Lambda request ID to create a unique but consistent session
            request_id = context.request_id if context else datetime.now().strftime('%Y%m%d-%H%M%S')
            session_id = f"lambda-{request_id[:8]}"
            logger.info(f"Auto-generated session_id: {session_id}")
        
        if not message:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'No message provided',
                    'usage': {
                        'message': 'Your question or command (required)',
                        'session_id': 'Unique session ID for conversation continuity (auto-generated if not provided)',
                        'actor_id': 'User identifier for personalization (optional)'
                    },
                    'example': {
                        'message': 'List my Redshift clusters',
                        'session_id': 'migration-2024-01-15',
                        'actor_id': 'user@example.com'
                    }
                })
            }
        
        logger.info(f"Processing message: {message[:100]}...")
        logger.info(f"Using session_id: {session_id}")
        if actor_id:
            logger.info(f"Using actor_id: {actor_id}")
        
        # Create or retrieve agent with memory (always enabled)
        agent = create_agent(
            session_id=session_id,
            actor_id=actor_id,
            region=region
        )
        
        # Get response from agent
        result = agent(message)
        
        # Extract response text from AgentResult
        if hasattr(result, 'text'):
            response = result.text
        elif hasattr(result, 'content'):
            response = result.content
        else:
            response = str(result)
        
        logger.info(f"Generated response: {response[:100]}...")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'response': response,
                'message': message,
                'session_id': session_id,
                'memory_enabled': True,
                'tip': 'Use the same session_id in your next request to continue this conversation'
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        
        # Check if it's a toolUse/toolResult imbalance error
        error_msg = str(e)
        if 'toolResult blocks' in error_msg and 'toolUse blocks' in error_msg:
            logger.warning("Detected toolUse/toolResult imbalance - conversation history corrupted")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Conversation history has become imbalanced',
                    'suggestion': 'Please start a new session with a different session_id to continue',
                    'tip': f'Use a new session_id like: migration-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                    'technical_details': 'The sliding window dropped messages in a way that created toolUse/toolResult imbalance'
                })
            }
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }
