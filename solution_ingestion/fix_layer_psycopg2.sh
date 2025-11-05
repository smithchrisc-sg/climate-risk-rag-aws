#!/bin/bash
# Fix psycopg2 in layer by removing incompatible binary

echo "Fixing psycopg2 compatibility in layer..."

ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion

# Remove the incompatible psycopg2 from the layer
echo "Removing incompatible psycopg2 from layer..."
rm -rf layers/database-core-layer/python/psycopg2*

# Install pandas for the CSV parser
echo "Installing pandas..."
python3.8 -m pip install --user pandas

# Test imports now
echo "Testing imports after psycopg2 removal..."
python3.8 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('layers/database-core-layer/python').absolute()))

try:
    from utils.DocumentIDManager import DocumentIDManager
    from utils.DatabaseManager import DatabaseManager
    print('SUCCESS: Both managers imported!')
    
    # Test instantiation
    doc_mgr = DocumentIDManager()
    print('SUCCESS: DocumentIDManager instantiated!')
    
except Exception as e:
    print('FAILED:', str(e))
    import traceback
    traceback.print_exc()
"

echo ""
echo "Testing full pipeline..."
python3.8 test_local_setup.py
EOF