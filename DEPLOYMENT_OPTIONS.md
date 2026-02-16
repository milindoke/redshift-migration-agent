# Deployment Options for Redshift Migration Agent

This guide covers multiple ways to deploy and share your Redshift Migration Agent with others.

## Option 1: GitHub Repository (Recommended for Teams)

Share the code via GitHub so others can run it locally.

### Steps:

1. **Create a GitHub repository:**
```bash
# Initialize git (if not already done)
git init

# Add files
git add .
git commit -m "Initial commit: Redshift Migration Agent"

# Create repo on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/redshift-migration-agent.git
git push -u origin main
```

2. **Users clone and run:**
```bash
git clone https://github.com/YOUR_USERNAME/redshift-migration-agent.git
cd redshift-migration-agent
./deploy_agent.sh
source venv/bin/activate
python redshift_agent.py
```

3. **Add a .gitignore:**
```
venv/
*.pyc
__pycache__/
.env
*.egg-info/
cluster-config.json
```

---

## Option 2: Web API with FastAPI

Deploy as a REST API that others can call from anywhere.

### Create API Server:

```python
# api_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redshift_agent import create_agent
import uvicorn

app = FastAPI(title="Redshift Migration Agent API")

# Global agent instance
agent = create_agent()

class ChatRequest(BaseModel):
    message: str
    
class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the Redshift Migration Agent."""
    try:
        response = agent(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Deploy to AWS:

**Using EC2:**
```bash
# On EC2 instance
git clone your-repo
cd redshift-migration-agent
./deploy_agent.sh
source venv/bin/activate
pip install fastapi uvicorn
python api_server.py
```

**Using ECS/Fargate:**
Create a Dockerfile:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -e .
RUN pip install -r requirements-agent.txt
RUN pip install fastapi uvicorn

EXPOSE 8000
CMD ["python", "api_server.py"]
```

---

## Option 3: Slack Bot

Deploy as a Slack bot for team collaboration.

### Create Slack Bot:

```python
# slack_bot.py
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from redshift_agent import create_agent
import os

app = App(token=os.environ["SLACK_BOT_TOKEN"])
agent = create_agent()

@app.message(".*")
def handle_message(message, say):
    """Respond to messages in Slack."""
    user_message = message['text']
    
    # Skip bot messages
    if message.get('bot_id'):
        return
    
    # Get response from agent
    response = agent(user_message)
    say(response)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
```

### Setup:
1. Create Slack app at api.slack.com/apps
2. Enable Socket Mode
3. Add Bot Token Scopes: `chat:write`, `app_mentions:read`
4. Install to workspace
5. Set environment variables and run

---

## Option 4: AWS Lambda Function

Serverless deployment for cost-effective scaling.

### Lambda Handler:

```python
# lambda_handler.py
import json
from redshift_agent import create_agent

# Initialize agent once (cold start)
agent = create_agent()

def lambda_handler(event, context):
    """AWS Lambda handler for the agent."""
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        message = body.get('message', '')
        
        if not message:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No message provided'})
            }
        
        # Get response from agent
        response = agent(message)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'response': response})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### Deploy with SAM:

```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  RedshiftAgentFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: .
      Handler: lambda_handler.lambda_handler
      Runtime: python3.11
      Timeout: 300
      MemorySize: 1024
      Environment:
        Variables:
          AWS_BEDROCK_API_KEY: !Ref BedrockApiKey
      Events:
        Api:
          Type: Api
          Properties:
            Path: /chat
            Method: post
```

Deploy:
```bash
sam build
sam deploy --guided
```

---

## Option 5: Docker Container

Package everything in a container for easy deployment anywhere.

### Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir -r requirements-agent.txt

# Set environment variables (override at runtime)
ENV AWS_REGION=us-east-2

# Run the agent
CMD ["python", "redshift_agent.py"]
```

### Build and Run:

```bash
# Build
docker build -t redshift-migration-agent .

# Run locally
docker run -it \
  -e AWS_BEDROCK_API_KEY=$AWS_BEDROCK_API_KEY \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  redshift-migration-agent

# Push to ECR
aws ecr create-repository --repository-name redshift-migration-agent
docker tag redshift-migration-agent:latest 123456789012.dkr.ecr.us-east-2.amazonaws.com/redshift-migration-agent:latest
docker push 123456789012.dkr.ecr.us-east-2.amazonaws.com/redshift-migration-agent:latest
```

---

## Option 6: Python Package (PyPI)

Publish as a pip-installable package.

### Update pyproject.toml:

```toml
[project]
name = "redshift-migration-agent"
version = "1.0.0"
description = "AI agent for migrating Redshift Provisioned to Serverless"
authors = [{name = "Your Name", email = "your.email@example.com"}]
dependencies = [
    "strands-agents>=1.26.0",
    "strands-agents-tools>=0.2.20",
    "boto3>=1.26.0",
    "click>=8.1.0",
    "rich>=13.0.0",
]

[project.scripts]
redshift-agent = "redshift_agent:main"
```

### Publish:

```bash
# Build
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

### Users install:

```bash
pip install redshift-migration-agent
redshift-agent
```

---

## Option 7: AWS Bedrock Agent (Native Integration)

Deploy as a native Bedrock Agent with action groups.

This requires creating:
1. Lambda functions for each tool
2. OpenAPI schema for action groups
3. Bedrock Agent configuration

See AWS Bedrock Agents documentation for details.

---

## Recommended Approach by Use Case

| Use Case | Recommended Option | Why |
|----------|-------------------|-----|
| Internal team | GitHub + Docker | Easy to maintain and update |
| External customers | Web API (FastAPI) | Standard REST interface |
| Slack workspace | Slack Bot | Native integration |
| Serverless/cost-sensitive | AWS Lambda | Pay per use |
| Enterprise deployment | Docker + ECS | Scalable and manageable |
| Open source project | PyPI Package | Easy installation |

---

## Security Considerations

For all deployment options:

1. **Never commit credentials:**
   - Use environment variables
   - Use AWS IAM roles when possible
   - Use AWS Secrets Manager for sensitive data

2. **Add authentication:**
   - API keys for REST APIs
   - IAM authentication for AWS services
   - OAuth for Slack bots

3. **Network security:**
   - Use VPC for AWS deployments
   - Enable HTTPS/TLS
   - Restrict security groups

4. **Audit logging:**
   - Log all agent interactions
   - Monitor AWS API calls
   - Track migration operations

---

## Next Steps

Choose the deployment option that fits your needs and follow the specific guide above. For most teams, I recommend starting with **Option 1 (GitHub)** for easy sharing, then moving to **Option 2 (Web API)** or **Option 5 (Docker)** for production deployments.
