#!/usr/bin/env python3
"""
Interactive chat interface for Redshift Migration Agent

Provides a natural conversation experience with the Lambda-based agent.
"""

import boto3
import json
import sys
from datetime import datetime

# ANSI color codes for better UX
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner(session_id):
    """Print welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("🚀 Redshift Migration Agent - Interactive Chat")
    print(f"{'='*70}{Colors.END}\n")
    print(f"{Colors.GREEN}Type your questions naturally. The agent will help you migrate your")
    print(f"Redshift clusters to Serverless.{Colors.END}\n")
    print(f"{Colors.BLUE}💾 Memory enabled - Agent remembers this conversation{Colors.END}")
    print(f"{Colors.BLUE}📋 Session ID: {session_id}{Colors.END}\n")
    print(f"{Colors.YELLOW}Commands:{Colors.END}")
    print("  • Type 'exit' or 'quit' to end the conversation")
    print("  • Type 'clear' to clear conversation history")
    print("  • Type 'help' for migration guidance")
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}\n")

def invoke_agent(lambda_client, message, session_id, region='us-east-2'):
    """Invoke the Lambda agent and return response"""
    try:
        response = lambda_client.invoke(
            FunctionName='redshift-migration-agent',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'message': message,
                'session_id': session_id
            })
        )
        
        # Parse response
        payload = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            body = json.loads(payload.get('body', '{}'))
            return body.get('response', 'No response received'), None
        else:
            return None, f"Lambda returned status code: {response['StatusCode']}"
            
    except Exception as e:
        return None, str(e)

def format_agent_response(text):
    """Format agent response with colors"""
    # Add color to headers/bold text
    lines = text.split('\n')
    formatted = []
    
    for line in lines:
        if line.strip().startswith('**') and line.strip().endswith('**'):
            # Bold headers
            formatted.append(f"{Colors.BOLD}{line}{Colors.END}")
        elif line.strip().startswith('✅') or line.strip().startswith('✓'):
            # Success items
            formatted.append(f"{Colors.GREEN}{line}{Colors.END}")
        elif line.strip().startswith('❌') or line.strip().startswith('⚠️'):
            # Warning/error items
            formatted.append(f"{Colors.YELLOW}{line}{Colors.END}")
        elif line.strip().startswith('•') or line.strip().startswith('-'):
            # List items
            formatted.append(f"{Colors.BLUE}{line}{Colors.END}")
        else:
            formatted.append(line)
    
    return '\n'.join(formatted)

def main():
    """Main chat loop"""
    # Initialize AWS client
    try:
        lambda_client = boto3.client('lambda', region_name='us-east-2')
        
        # Test connection
        lambda_client.get_function(FunctionName='redshift-migration-agent')
    except Exception as e:
        print(f"{Colors.RED}❌ Error connecting to Lambda:{Colors.END}")
        print(f"   {str(e)}\n")
        print(f"{Colors.YELLOW}Make sure:{Colors.END}")
        print("  1. AWS credentials are configured (run: aws configure)")
        print("  2. You have permission to invoke the Lambda function")
        print("  3. The function 'redshift-migration-agent' exists in us-east-2")
        sys.exit(1)
    
    # Create a session ID for this chat session
    session_id = f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Print banner
    print_banner(session_id)
    
    # Conversation loop
    conversation_count = 0
    
    while True:
        try:
            # Get user input
            user_input = input(f"{Colors.BOLD}You:{Colors.END} ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print(f"\n{Colors.GREEN}👋 Thanks for using Redshift Migration Agent!{Colors.END}")
                print(f"{Colors.BLUE}💾 Your conversation is saved in session: {session_id}{Colors.END}")
                print(f"{Colors.BLUE}Happy migrating! 🚀{Colors.END}\n")
                break
            
            if user_input.lower() == 'clear':
                # Start a new session
                session_id = f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                print("\n" * 50)  # Clear screen
                print_banner(session_id)
                conversation_count = 0
                print(f"{Colors.YELLOW}🔄 Started new conversation session{Colors.END}\n")
                continue
            
            if user_input.lower() == 'help':
                user_input = "What can you help me with? Give me a quick overview of your capabilities."
            
            # Show thinking indicator
            print(f"\n{Colors.YELLOW}🤔 Agent is thinking...{Colors.END}", end='', flush=True)
            
            # Invoke agent with session_id
            response, error = invoke_agent(lambda_client, user_input, session_id)
            
            # Clear thinking indicator
            print('\r' + ' ' * 50 + '\r', end='', flush=True)
            
            if error:
                print(f"{Colors.RED}❌ Error: {error}{Colors.END}\n")
                continue
            
            # Display response
            print(f"{Colors.BOLD}{Colors.GREEN}Agent:{Colors.END}")
            print(format_agent_response(response))
            print()  # Empty line for spacing
            
            conversation_count += 1
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.END}")
            print(f"{Colors.BLUE}💾 Your conversation is saved in session: {session_id}{Colors.END}")
            print(f"{Colors.GREEN}👋 Goodbye!{Colors.END}\n")
            break
        except Exception as e:
            print(f"\n{Colors.RED}❌ Unexpected error: {str(e)}{Colors.END}\n")
            continue

if __name__ == '__main__':
    main()
