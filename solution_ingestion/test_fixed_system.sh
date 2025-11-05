#!/bin/bash
# Test the properly fixed system without fallbacks

echo "Testing the properly fixed system..."

ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion

echo "Running test with proper imports (no fallbacks)..."
python3 test_local_setup.py
EOF