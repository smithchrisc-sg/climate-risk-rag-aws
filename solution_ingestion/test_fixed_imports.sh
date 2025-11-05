#!/bin/bash
# Test the fixed layer imports

echo "Testing fixed layer imports..."

ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion

echo "Running updated test with fixed imports..."
python3 test_local_setup.py
EOF