# Quick Guide: Sharing Your Redshift Migration Agent

## Fastest Way to Share

### Option 1: GitHub (Recommended)
Share the code repository:

```bash
# Push to GitHub
git init
git add .
git commit -m "Redshift Migration Agent"
git remote add origin https://github.com/YOUR_USERNAME/redshift-migration-agent.git
git push -u origin main
```

Users can then:
```bash
git clone https://github.com/YOUR_USERNAME/redshift-migration-agent.git
cd redshift-migration-agent
./quick_deploy.sh
```

### Option 2: Docker (Easiest for Users)
Build and share a Docker image:

```bash
# Build
docker build -t redshift-migration-agent .

# Push to Docker Hub
docker tag redshift-migration-agent YOUR_USERNAME/redshift-migration-agent
docker push YOUR_USERNAME/redshift-migration-agent
```

Users run:
```bash
docker run -it \
  -e AWS_BEDROCK_API_KEY=$AWS_BEDROCK_API_KEY \
  YOUR_USERNAME/redshift-migration-agent
```

### Option 3: API Server (Best for Remote Access)
Deploy as a web service:

```bash
# Start API server
./quick_deploy.sh
# Choose option 3 or 4

# Share the URL with users
# They can access via: http://your-server:8000
```

Users interact via HTTP:
```bash
curl -X POST http://your-server:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List my Redshift clusters"}'
```

## What You've Created

Your agent deployment includes:

1. **redshift_agent.py** - Main agent (interactive CLI)
2. **api_server.py** - REST API server
3. **Dockerfile** - Container image
4. **docker-compose.yml** - Easy deployment
5. **quick_deploy.sh** - One-command deployment
6. **DEPLOYMENT_OPTIONS.md** - Full deployment guide

## Quick Commands

```bash
# Local deployment
./deploy_agent.sh
source venv/bin/activate
python redshift_agent.py

# API server
python api_server.py
# Visit http://localhost:8000/docs

# Docker
docker-compose up -d
# Visit http://localhost:8000

# Test API
python examples/api_client_example.py
```

## Security Notes

Before sharing:

1. **Remove credentials** from code
2. **Add .gitignore** for sensitive files
3. **Use environment variables** for AWS credentials
4. **Add authentication** for production APIs

## Next Steps

1. Choose your deployment method from DEPLOYMENT_OPTIONS.md
2. Test with `./quick_deploy.sh`
3. Share with your team
4. Monitor usage and iterate

For detailed deployment options, see **DEPLOYMENT_OPTIONS.md**.
