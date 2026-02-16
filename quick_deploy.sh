#!/bin/bash
# Quick deployment script for Redshift Migration Agent

set -e

echo "🚀 Redshift Migration Agent - Quick Deploy"
echo "=========================================="
echo ""

# Check for deployment type
echo "Choose deployment option:"
echo "1) Local (run on this machine)"
echo "2) Docker (containerized)"
echo "3) API Server (FastAPI)"
echo "4) Docker Compose (with auto-restart)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Deploying locally..."
        ./deploy_agent.sh
        echo ""
        echo "✅ Deployment complete!"
        echo ""
        echo "To run the agent:"
        echo "  source venv/bin/activate"
        echo "  python redshift_agent.py"
        ;;
    
    2)
        echo ""
        echo "Building Docker image..."
        docker build -t redshift-migration-agent .
        
        echo ""
        echo "✅ Docker image built!"
        echo ""
        echo "To run the agent:"
        echo "  docker run -it \\"
        echo "    -e AWS_BEDROCK_API_KEY=\$AWS_BEDROCK_API_KEY \\"
        echo "    -e AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID \\"
        echo "    -e AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY \\"
        echo "    redshift-migration-agent"
        ;;
    
    3)
        echo ""
        echo "Installing API dependencies..."
        source venv/bin/activate 2>/dev/null || ./deploy_agent.sh
        pip install fastapi uvicorn
        
        echo ""
        echo "✅ API server ready!"
        echo ""
        echo "To start the API server:"
        echo "  source venv/bin/activate"
        echo "  python api_server.py"
        echo ""
        echo "API will be available at:"
        echo "  http://localhost:8000"
        echo "  http://localhost:8000/docs (interactive docs)"
        ;;
    
    4)
        echo ""
        echo "Starting with Docker Compose..."
        
        # Check if .env exists
        if [ ! -f .env ]; then
            echo "Creating .env file..."
            cat > .env << EOF
AWS_BEDROCK_API_KEY=${AWS_BEDROCK_API_KEY}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AWS_REGION=us-east-2
EOF
        fi
        
        docker-compose up -d
        
        echo ""
        echo "✅ Agent running in background!"
        echo ""
        echo "API available at: http://localhost:8000"
        echo "API docs at: http://localhost:8000/docs"
        echo ""
        echo "Useful commands:"
        echo "  docker-compose logs -f    # View logs"
        echo "  docker-compose stop       # Stop agent"
        echo "  docker-compose restart    # Restart agent"
        echo "  docker-compose down       # Stop and remove"
        ;;
    
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "For more deployment options, see DEPLOYMENT_OPTIONS.md"
