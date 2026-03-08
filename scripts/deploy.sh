#!/bin/bash
# Deployment script for Databricks bundles

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if environment is provided
if [ -z "$1" ]; then
    print_error "Environment not specified!"
    echo "Usage: ./scripts/deploy.sh <dev|staging|prod>"
    exit 1
fi

ENVIRONMENT=$1

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    echo "Valid environments: dev, staging, prod"
    exit 1
fi

print_info "Starting deployment to $ENVIRONMENT environment..."

# Check if Databricks CLI is installed
if ! command -v databricks &> /dev/null; then
    print_error "Databricks CLI is not installed!"
    echo "Install it with: pip install databricks-cli"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    print_info "Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
else
    print_warning ".env file not found. Make sure environment variables are set."
fi

# Validate bundle configuration
print_info "Validating Databricks bundle configuration..."
if ! databricks bundle validate -t "$ENVIRONMENT"; then
    print_error "Bundle validation failed!"
    exit 1
fi

print_info "Bundle validation successful!"

# Deploy bundle
print_info "Deploying bundle to $ENVIRONMENT..."
if ! databricks bundle deploy -t "$ENVIRONMENT"; then
    print_error "Bundle deployment failed!"
    exit 1
fi

print_info "Bundle deployed successfully!"

# Optional: Run the pipeline
read -p "Do you want to run the DLT pipeline now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Running DLT pipeline..."
    databricks bundle run analytics_dlt_pipeline -t "$ENVIRONMENT" || print_warning "Pipeline run command failed. You can run it manually from Databricks UI."
fi

print_info "Deployment completed successfully! 🎉"
