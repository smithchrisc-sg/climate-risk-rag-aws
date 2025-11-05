#!/bin/bash
# Simple urllib3 fix for EC2

echo "Fixing urllib3 compatibility on EC2..."

# Check current version
echo "Current urllib3 version:"
ssh ec2-user@ec2-dev "python3 -c 'import urllib3; print(urllib3.__version__)'"

# Install compatible version
echo "Installing compatible urllib3..."
ssh ec2-user@ec2-dev "pip3 install --user 'urllib3<2.0'"

# Verify
echo "New urllib3 version:"
ssh ec2-user@ec2-dev "python3 -c 'import urllib3; print(urllib3.__version__)'"

# Test imports
echo "Testing layer imports..."
ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('layers/database-core-layer/python').absolute()))
try:
    from utils.DocumentIDManager import DocumentIDManager
    print('SUCCESS: DocumentIDManager imported!')
except Exception as e:
    print('FAILED:', e)
"
EOF