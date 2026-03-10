#!/bin/bash

# Redshift Modernization Agents - Finch Deployment Script
# Deploys all agents to the customer account using Finch (Docker-compatible container tool)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration — single customer account
AWS_PROFILE="${AWS_PROFILE:-default}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
REGION="${AWS_REGION:-us-east-2}"

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

    if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
        print_error "AWS credentials not configured (profile: $AWS_PROFILE)"
        exit 1
    fi

    # Auto-detect account ID if not set
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)
    fi
    print_info "Customer account: $AWS_ACCOUNT_ID ✓"
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
    print_step "Creating ECR repositories in customer account..."

    for agent in orchestrator assessment scoring architecture execution; do
        aws ecr create-repository \
            --repository-name redshift-${agent} \
            --region $REGION \
            --profile "$AWS_PROFILE" \
            2>/dev/null || print_warning "Repository redshift-${agent} may already exist"
    done

    print_info "ECR repositories ready ✓"
}

# Function to push all images to ECR
push_images() {
    print_step "Pushing all images to ECR (customer account)..."

    # Authenticate
    print_info "Authenticating Finch to ECR..."
    aws ecr get-login-password \
        --region $REGION \
        --profile "$AWS_PROFILE" | \
        finch login --username AWS --password-stdin \
        $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

    # Tag and push each agent
    for agent in orchestrator assessment scoring architecture execution; do
        print_info "Tagging and pushing redshift-${agent}..."

        finch tag redshift-${agent}:latest \
            $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest

        finch push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest

        print_info "Pushed redshift-${agent} ✓"
    done

    print_info "All images pushed to ECR ✓"
}

# Function to display next steps
show_next_steps() {
    echo
    print_step "Container images pushed to ECR successfully! 🎉"
    echo
    echo "All images are in customer account $AWS_ACCOUNT_ID."
    echo
    echo "Next steps:"
    echo
    echo "1. Deploy to Bedrock AgentCore via Console:"
    echo "   - Open AWS Bedrock Console → AgentCore"
    echo "   - Create Agent for each image"
    echo "   - Use these Image URIs:"
    echo
    for agent in orchestrator assessment scoring architecture execution; do
        echo "   $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/redshift-${agent}:latest"
    done
    echo
    echo "2. Set environment variables for each agent:"
    echo "   All agents: AWS_REGION, STORAGE_DIR"
    echo "   Orchestrator: WORKSPACE_ID, MCP_AUTH_TOKEN"
    echo
    echo "3. Register agents with ATX Agent Registry"
    echo
    echo "4. Test deployment"
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
            push_images
            echo
            show_next_steps
            ;;
        3)
            create_ecr_repos
            echo
            push_images
            echo
            show_next_steps
            ;;
        4)
            build_images
            echo
            create_ecr_repos
            echo
            push_images
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
