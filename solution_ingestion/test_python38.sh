#!/bin/bash
# Test layer imports with Python 3.8

echo "Testing layer imports with Python 3.8..."

ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion

echo "Testing with python3.8 directly..."
python3.8 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('layers/database-core-layer/python').absolute()))

print('Python version:', sys.version)

try:
    import ssl
    print('OpenSSL version:', ssl.OPENSSL_VERSION)
except:
    print('Could not get OpenSSL version')

try:
    from utils.DocumentIDManager import DocumentIDManager
    from utils.DatabaseManager import DatabaseManager
    print('SUCCESS: Both managers imported!')
    
    # Test instantiation
    doc_mgr = DocumentIDManager()
    print('SUCCESS: DocumentIDManager instantiated!')
    
    db_mgr = DatabaseManager()
    print('SUCCESS: DatabaseManager instantiated!')
    
except Exception as e:
    print('FAILED:', str(e))
    import traceback
    traceback.print_exc()
"

echo ""
echo "Now testing the full test suite with python3.8..."
python3.8 test_local_setup.py
EOF