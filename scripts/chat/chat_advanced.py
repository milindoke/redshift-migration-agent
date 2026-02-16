#!/usr/bin/env python3
"""
Advanced interactive chat interface for Redshift Migration Agent

Features:
- Conversation history
- Rich formatting
- Auto-save conversations
- Command history
"""

import boto3
import json
import sys
import os
from datetime import datetime
from pathlib import Path

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  For better experience, install rich: pip install rich")
    print()

class AgentChat:
    def __init__(self, region='us-east-2'):
        self.region = region
        self.lambda_client = None
        self.conversation_history = []
        self.console = Console() if RICH_AVAILABLE else None
        
    def connect(self):
        """Connect to AWS Lambda"""
        try:
            self.lambda_client = boto3.client('lambda', region_name=self.region)
            self.lambda_client.get_function(FunctionName='redshift-migration-agent')
            return True, None
        except Exception as e:
            return False, str(e)
    
    def invoke_agent(self, message):
        """Invoke the Lambda agent"""
        try:
            # Add to history
            self.conversation_history.append({
                'timestamp': datetime.now().isoformat(),
                'role': 'user',
                'content': message
            })
            
            response = self.lambda_client.invoke(
                FunctionName='redshift-migration-agent',
                InvocationType='RequestResponse',
                Payload=json.dumps({'message': message})
            )
            
            payload = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                body = json.loads(payload.get('body', '{}'))
                agent_response = body.get('response', 'No response received')
                
                # Add to history
                self.conversation_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'role': 'agent',
                    'content': agent_response
                })
                
                return agent_response, None
            else:
                return None, f"Lambda returned status code: {response['StatusCode']}"
                
        except Exception as e:
            return None, str(e)
    
    def save_conversation(self):
        """Save conversation to file"""
        if not self.conversation_history:
            return
        
        # Create conversations directory
        conv_dir = Path.home() / '.redshift-agent' / 'conversations'
        conv_dir.mkdir(parents=True, exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = conv_dir / f'conversation_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.conversation_history, f, indent=2)
        
        return filename
    
    def print_banner(self):
        """Print welcome banner"""
        if RICH_AVAILABLE:
            self.console.print("\n[bold blue]" + "="*70)
            self.console.print("🚀 Redshift Migration Agent - Interactive Chat", style="bold blue")
            self.console.print("="*70 + "[/bold blue]\n")
            self.console.print("[green]Chat naturally with the agent. It will help you migrate your")
            self.console.print("Redshift clusters to Serverless.[/green]\n")
            self.console.print("[yellow]Commands:[/yellow]")
            self.console.print("  • [cyan]exit/quit[/cyan] - End conversation")
            self.console.print("  • [cyan]clear[/cyan] - Clear screen")
            self.console.print("  • [cyan]history[/cyan] - Show conversation history")
            self.console.print("  • [cyan]save[/cyan] - Save conversation to file")
            self.console.print("  • [cyan]help[/cyan] - Get migration guidance")
            self.console.print("\n[blue]" + "="*70 + "[/blue]\n")
        else:
            print("\n" + "="*70)
            print("🚀 Redshift Migration Agent - Interactive Chat")
            print("="*70 + "\n")
            print("Chat naturally with the agent. It will help you migrate your")
            print("Redshift clusters to Serverless.\n")
            print("Commands:")
            print("  • exit/quit - End conversation")
            print("  • clear - Clear screen")
            print("  • history - Show conversation history")
            print("  • save - Save conversation to file")
            print("  • help - Get migration guidance")
            print("\n" + "="*70 + "\n")
    
    def print_response(self, text):
        """Print agent response with formatting"""
        if RICH_AVAILABLE:
            md = Markdown(text)
            panel = Panel(md, title="[bold green]Agent Response[/bold green]", border_style="green")
            self.console.print(panel)
        else:
            print("\nAgent:")
            print(text)
            print()
    
    def show_history(self):
        """Show conversation history"""
        if not self.conversation_history:
            if RICH_AVAILABLE:
                self.console.print("[yellow]No conversation history yet[/yellow]\n")
            else:
                print("No conversation history yet\n")
            return
        
        if RICH_AVAILABLE:
            self.console.print("\n[bold cyan]Conversation History:[/bold cyan]\n")
            for i, entry in enumerate(self.conversation_history, 1):
                role = entry['role'].capitalize()
                content = entry['content'][:100] + "..." if len(entry['content']) > 100 else entry['content']
                time = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
                
                if entry['role'] == 'user':
                    self.console.print(f"[cyan]{i}. [{time}] You:[/cyan] {content}")
                else:
                    self.console.print(f"[green]{i}. [{time}] Agent:[/green] {content}")
            print()
        else:
            print("\nConversation History:\n")
            for i, entry in enumerate(self.conversation_history, 1):
                role = entry['role'].capitalize()
                content = entry['content'][:100] + "..." if len(entry['content']) > 100 else entry['content']
                time = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
                print(f"{i}. [{time}] {role}: {content}")
            print()
    
    def run(self):
        """Main chat loop"""
        # Connect to Lambda
        success, error = self.connect()
        if not success:
            if RICH_AVAILABLE:
                self.console.print(f"[red]❌ Error connecting to Lambda:[/red]")
                self.console.print(f"   {error}\n")
                self.console.print("[yellow]Make sure:[/yellow]")
                self.console.print("  1. AWS credentials are configured (run: aws configure)")
                self.console.print("  2. You have permission to invoke the Lambda function")
                self.console.print("  3. The function exists in us-east-2")
            else:
                print(f"❌ Error connecting to Lambda:")
                print(f"   {error}\n")
                print("Make sure:")
                print("  1. AWS credentials are configured")
                print("  2. You have permission to invoke the Lambda function")
                print("  3. The function exists in us-east-2")
            sys.exit(1)
        
        # Print banner
        self.print_banner()
        
        # Chat loop
        while True:
            try:
                # Get user input
                if RICH_AVAILABLE:
                    user_input = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
                else:
                    user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    # Auto-save conversation
                    if self.conversation_history:
                        filename = self.save_conversation()
                        if RICH_AVAILABLE:
                            self.console.print(f"\n[green]💾 Conversation saved to: {filename}[/green]")
                            self.console.print("[green]👋 Thanks for using Redshift Migration Agent![/green]")
                            self.console.print("[blue]Happy migrating! 🚀[/blue]\n")
                        else:
                            print(f"\n💾 Conversation saved to: {filename}")
                            print("👋 Thanks for using Redshift Migration Agent!")
                            print("Happy migrating! 🚀\n")
                    break
                
                if user_input.lower() == 'clear':
                    os.system('clear' if os.name != 'nt' else 'cls')
                    self.print_banner()
                    continue
                
                if user_input.lower() == 'history':
                    self.show_history()
                    continue
                
                if user_input.lower() == 'save':
                    filename = self.save_conversation()
                    if RICH_AVAILABLE:
                        self.console.print(f"[green]💾 Conversation saved to: {filename}[/green]\n")
                    else:
                        print(f"💾 Conversation saved to: {filename}\n")
                    continue
                
                if user_input.lower() == 'help':
                    user_input = "What can you help me with? Give me a quick overview of your capabilities."
                
                # Show thinking indicator
                if RICH_AVAILABLE:
                    with self.console.status("[yellow]🤔 Agent is thinking...[/yellow]"):
                        response, error = self.invoke_agent(user_input)
                else:
                    print("🤔 Agent is thinking...", end='', flush=True)
                    response, error = self.invoke_agent(user_input)
                    print('\r' + ' ' * 50 + '\r', end='', flush=True)
                
                if error:
                    if RICH_AVAILABLE:
                        self.console.print(f"[red]❌ Error: {error}[/red]\n")
                    else:
                        print(f"❌ Error: {error}\n")
                    continue
                
                # Display response
                self.print_response(response)
                
            except KeyboardInterrupt:
                if RICH_AVAILABLE:
                    self.console.print("\n\n[yellow]Interrupted by user[/yellow]")
                    self.console.print("[green]👋 Goodbye![/green]\n")
                else:
                    print("\n\nInterrupted by user")
                    print("👋 Goodbye!\n")
                break
            except Exception as e:
                if RICH_AVAILABLE:
                    self.console.print(f"\n[red]❌ Unexpected error: {str(e)}[/red]\n")
                else:
                    print(f"\n❌ Unexpected error: {str(e)}\n")
                continue

if __name__ == '__main__':
    chat = AgentChat()
    chat.run()
