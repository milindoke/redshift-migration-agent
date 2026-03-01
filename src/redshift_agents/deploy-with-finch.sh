#!/bin/bash

# Redshift Modernization Agents - Finch Deployment Script
# Deploys all agents using Finch (Docker-compatible container tool)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_ACCOUNT_PROFILE="service-account"
CUSTOMER_ACCOUNT_PROFILE="customer-account"
SERVICE_ACCOUNT_ID="497316421912"
CUSTOMER_ACCOUNT_ID="188199011335"
REGION="us-east-2"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check Finch
    if ! command -v finch &> /dev/null; then
        print_error "Finch is not installed"
        echo "Install from: https://github.com/runfinch/finch"
        exit 1
    fi
    print_info "Finch installed: $(finch --version)"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi
    print_info "AWS CLI installed ✓"
    
    # Verify AWS credentials
    print_info "Verifying AWS credentials..."
    
    if ! aws sts get-caller-identity --profile $SERVICE_ACCOUNT_PROFILE &> /dev/null; then
        print_error "Service account credentials not configured"
        exit 1
    fi
    print_info "Service account: $SERVICE_ACCOUNT_ID ✓"
    
    if ! aws sts get-caller-identity --profile $CUSTOMER_ACCOUNT_PROFILE &> /dev/null; then
        print_error "Customer account credentials not configured"
        exit 1
    fi
    print_info "Customer account: $CUSTOMER_ACCOUNT_ID ✓"
}

# Function to start Finch VM
start_finch() {
    print_step "Starting Finch VM..."
    
    if finch ps &> /dev/null; then
        print_info "Finch VM already running ✓"
        return 0
    fi
    
    print_info "Starting Finch VM (this may take 30 seconds)..."
    finch vm start
    
    # Wait for VM to be ready
    sleep 5
    
    if finch ps &> /dev/null; then
        print_info "Finch VM started successfully ✓"
    else
        print_error "Failed to start Finch VM"
        exit 1
    fi
}

# Function to build images
build_images() {
    print_step "Building container images with Finch..."
    
    local agents=("orchestrator" "assessment" "scoring" "architecture" "execution")
    
    for agent in "${agents[@]}"; do
        print_info "Building redshift-${agent}:latest..."
        finch build \
            -t redshift-${agent}:latest \
            -f src/redshift_agents/docker/Dockerfile.${agent} \
            . \
            --quiet
        print_info "Built redshift-${agent}:latest ✓"
    done
    
    print_info "All images built successfully ✓"
    finch images | grep redshift
}

# Function to create ECR repositories
create_ecr_repos() {
    print_step "Creating ECR repositories..."
    
    # Service account - orchestrator
    print_info "Creating orchestrator repository in service account..."
    aws ecr create-repository \
        --repository-name redshift-orchestrator \
        --region $REGION \
        --profile $SERVICE_ACCOUNT_PROFILE \
        2>/dev/null || print_warning "Repository may already exist"
    
    # Customer account - subagents
    print_info "Creating subagent repositories in customer account..."
    for agent in assessment scoring architecture execution; do
        aws ecr create-repository \
            --repository-name redshift-${agent} \
            --region $REGION \
            --profile $CUSTOMER_ACCOUNT_PROFILE \
            2>/dev/null || print_warning "Repository redshift-${agent} may already exist"
    done
    
    print_info "ECR repositories ready ✓"
}

# Function to push orchestrator to ECR
push_orchestrator() {
    print_step "Pushing orchestrator to ECR (service account)..."
    
    # Authenticate
    print_info "Authenticating Finch to ECR..."
    aws ecr get-login-password \
        --region $REGION \
        --profile $SERVICE_ACCOUNT_PROFILE | \
        finch login --username AWS --password-stdin \
        $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    # Tag
    print_info "Tagging orchestrator image..."
    finch tag redshift-orchestrator:latest \
        $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest
    
    # Push
    print_info "Pushing orchestrator to ECR (this may take 5 minutes)..."
    finch push $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest
    
    print_info "Orchestrator pushed to ECR ✓"
    echo "Image URI: $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest"
}

# Function to push subagents to ECR
push_subagents() {
    print_step "Pushing subagents to ECR (customer account)..."
    
    # Authenticate
    print_info "Authenticating Finch to ECR..."
    aws ecr get-login-password \
        --region $REGION \
        --profile $CUSTOMER_ACCOUNT_PROFILE | \
        finch login --username AWS --password-stdin \
        $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    # Tag and push each subagent
    for agent in assessment scoring architecture execution; do
        print_info "Tagging and pushing redshift-${agent}..."
        
        finch tag redshift-${agent}:latest \
            $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest
        
        finch push $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest
        
        print_info "Pushed redshift-${agent} ✓"
    done
    
    print_info "All subagents pushed to ECR ✓"
}

# Function to display next steps
show_next_steps() {
    echo
    print_step "Container images pushed to ECR successfully! 🎉"
    echo
    echo "Next steps:"
    echo
    echo "1. Deploy to Bedrock AgentCore via Console:"
    echo "   - Open AWS Bedrock Console → AgentCore"
    echo "   - Create Agent for each image"
    echo "   - Use these Image URIs:"
    echo
    echo "   Orchestrator (Service Account $SERVICE_ACCOUNT_ID):"
    echo "   $SERVICE_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-orchestrator:latest"
    echo
    echo "   Subagents (Customer Account $CUSTOMER_ACCOUNT_ID):"
    echo "   $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-assessment:latest"
    echo "   $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-scoring:latest"
    echo "   $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-architecture:latest"
    echo "   $CUSTOMER_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-execution:latest"
    echo
    echo "2. Set environment variables for each agent:"
    echo "   Orchestrator: WORKSPACE_ID, MCP_AUTH_TOKEN, AWS_REGION, STORAGE_DIR"
    echo "   Subagents: AWS_REGION, STORAGE_DIR"
    echo
    echo "3. Register agents with ATX Agent Registry"
    echo
    echo "4. Test deployment"
    echo
    echo "See FINCH_DEPLOYMENT.md for detailed instructions."
}

# Main execution
main() {
    echo
    print_info "Redshift Modernization Agents - Finch Deployment"
    print_info "=================================================="
    echo
    
    check_prerequisites
    echo
    
    start_finch
    echo
    
    # Ask what to do
    echo "What would you like to do?"
    echo "1) Build images only"
    echo "2) Build and push to ECR"
    echo "3) Push existing images to ECR"
    echo "4) Full deployment (build + push)"
    read -p "Enter choice [1-4]: " CHOICE
    echo
    
    case $CHOICE in
        1)
            build_images
            ;;
        2)
            build_images
            echo
            create_ecr_repos
            echo
            push_orchestrator
            echo
            push_subagents
            echo
            show_next_steps
            ;;
        3)
            create_ecr_repos
            echo
            push_orchestrator
            echo
            push_subagents
            echo
            show_next_steps
            ;;
        4)
            build_images
            echo
            create_ecr_repos
            echo
            push_orchestrator
            echo
            push_subagents
            echo
            show_next_steps
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    echo
    print_info "Done! ✓"
}

# Run main function
main
