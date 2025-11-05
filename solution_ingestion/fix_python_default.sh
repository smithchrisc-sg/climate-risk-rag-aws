#!/bin/bash
# Fix Python default and test layer imports properly

echo "Setting Python 3.8 as default and testing layer imports..."

ssh ec2-user@ec2-dev << 'EOF'
# Set python3.8 as the default python3
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 2
sudo alternatives --set python3 /usr/bin/python3.8

# Verify the change
echo "New default Python version:"
python3 --version

# Test layer imports with the new default Python
cd ~/climate-risk-rag-aws/solution_ingestion

echo "Testing layer imports with new default Python..."
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('layers/database-core-layer/python').absolute()))

try:
    from utils.DocumentIDManager import DocumentIDManager
    from utils.DatabaseManager import DatabaseManager
    print('SUCCESS: Layer imports working with default Python!')
except Exception as e:
    print('FAILED:', str(e))
"

echo "Running full test suite with new default Python..."
python3 test_local_setup.py
EOF