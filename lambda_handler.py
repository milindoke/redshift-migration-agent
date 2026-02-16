#!/usr/bin/env python3
"""
AWS Lambda handler for Redshift Migration Agent

Provides serverless execution of the agent via Lambda function.
"""

import json
import logging
from redshift_agent import create_agent

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize agent once (cold start optimization)
logger.info("Initializing Redshift Migration Agent...")
agent = create_agent()
logger.info("Agent initialized successfully")


def lambda_handler(event, context):
    """
    AWS Lambda handler for the Redshift Migration Agent.
    
    Expected event format:
    {
        "body": "{\"message\": \"your message here\"}"
    }
    
    Or direct invocation:
    {
        "message": "your message here"
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
        
        if not message:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'No message provided',
                    'usage': 'Send a JSON body with a "message" field'
                })
            }
        
        logger.info(f"Processing message: {message[:100]}...")
        
        # Get response from agent
        response = agent(message)
        
        logger.info(f"Generated response: {response[:100]}...")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'response': response,
                'message': message
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
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
