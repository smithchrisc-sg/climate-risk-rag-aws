#!/bin/bash
# Deployment Script for Solution Ingestion CLI
# Packages and deploys to EC2 for testing with AWS services.

set -e

echo "Solution Ingestion CLI Deployment"
echo "================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "Error: Must run from solution_ingestion directory"
    exit 1
fi

# Create deployment package with proper directory structure
echo "Creating deployment package..."
cd ..
tar -czf solution_ingestion.tar.gz \
    --exclude="solution_ingestion/output_data/*" \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --exclude=".git" \
    solution_ingestion/
cd solution_ingestion

echo "Package created: ../solution_ingestion.tar.gz"
echo "Size: $(du -h ../solution_ingestion.tar.gz | cut -f1)"

echo ""
echo "Deployment Instructions:"
echo "1. Copy to EC2: scp ../solution_ingestion.tar.gz ec2-dev:~/"
echo "2. SSH to EC2: ssh ec2-dev"
echo "3. Clean up: rm -rf solution_ingestion"
echo "4. Extract: tar -xzf solution_ingestion.tar.gz"
echo "5. Install deps: cd solution_ingestion && pip3 install pandas==1.3.5"
echo "6. Test: python3 test_database_integration.py"

echo ""
echo "Environment variables needed on EC2:"
echo "export AWS_REGION=us-east-1"
echo "export PYTHONPATH=\"./layers/database-core-layer/python:./layers/knowledge-graph-layer/python:\$PYTHONPATH\""