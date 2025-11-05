#!/bin/bash
# Fix psycopg2 compatibility

echo "Fixing psycopg2 compatibility..."

# Remove the incompatible psycopg2 from layer
ssh ec2-user@ec2-dev "rm -rf ~/climate-risk-rag-aws/solution_ingestion/layers/database-core-layer/python/psycopg2*"

# Install compatible psycopg2-binary for the EC2 environment
ssh ec2-user@ec2-dev "pip3 install --user psycopg2-binary"

# Test imports again
echo "Testing layer imports after psycopg2 fix..."
ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion
python3 -c "
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
    print('FAILED:', e)
"
EOF