#!/bin/bash
# Deploy and Test Script
# Copies solution ingestion code to EC2 and runs tests

set -e

# Configuration
EC2_HOST="ec2-user@ec2-dev"
REMOTE_DIR="~/climate-risk-rag-aws/solution_ingestion"

echo "Deploying Solution Ingestion to EC2..."
echo "======================================"

# Create remote directory if it doesn't exist
ssh $EC2_HOST "mkdir -p $REMOTE_DIR"

# Copy all solution ingestion files
echo "Copying files to EC2..."
scp -r ./* $EC2_HOST:$REMOTE_DIR/

echo "Files copied successfully!"

# Run tests on EC2
echo ""
echo "Running tests on EC2..."
echo "======================="

ssh $EC2_HOST << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion

echo "Running local setup test..."
python3 test_local_setup.py

echo ""
echo "Running layer import diagnostics..."
python3 test_layer_imports.py
EOF

echo ""
echo "Deployment and testing complete!"