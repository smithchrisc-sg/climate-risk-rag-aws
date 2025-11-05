#!/bin/bash
# Debug the actual layer structure and fix imports

echo "Debugging layer structure and fixing imports..."

ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion

echo "=== LAYER STRUCTURE DEBUG ==="
echo "Database layer structure:"
find layers/database-core-layer -name "*.py" | head -10

echo ""
echo "Contents of layers/database-core-layer/python:"
ls -la layers/database-core-layer/python/

echo ""
echo "Contents of layers/database-core-layer/python/utils:"
ls -la layers/database-core-layer/python/utils/

echo ""
echo "=== TESTING DIFFERENT IMPORT STRATEGIES ==="

# Test 1: Direct path to utils
echo "Test 1: Adding layers/database-core-layer/python to path"
python3 -c "
import sys
sys.path.insert(0, 'layers/database-core-layer/python')
print('sys.path:', sys.path[:3])
try:
    import utils
    print('utils module found:', utils.__file__)
    print('utils contents:', dir(utils))
except Exception as e:
    print('utils import failed:', e)

try:
    from utils import DocumentIDManager
    print('SUCCESS: DocumentIDManager imported from utils')
except Exception as e:
    print('DocumentIDManager import failed:', e)
"

echo ""
echo "Test 2: Adding layers/database-core-layer/python/utils to path"
python3 -c "
import sys
sys.path.insert(0, 'layers/database-core-layer/python/utils')
print('sys.path:', sys.path[:3])
try:
    import DocumentIDManager
    print('SUCCESS: DocumentIDManager imported directly')
except Exception as e:
    print('Direct DocumentIDManager import failed:', e)
"

echo ""
echo "Test 3: Check if __init__.py exists in utils"
ls -la layers/database-core-layer/python/utils/__init__.py
cat layers/database-core-layer/python/utils/__init__.py

EOF