#!/bin/bash
# Fix imports properly by understanding the actual layer structure

echo "Fixing imports properly..."

ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion

echo "=== UNDERSTANDING THE LAYER STRUCTURE ==="
echo "Layer directory structure:"
find layers -type f -name "*.py" | head -10

echo ""
echo "Testing direct import from correct path:"
python3 -c "
import sys
import os

# Add the layer python directory to sys.path (Lambda layer convention)
layer_path = os.path.abspath('layers/database-core-layer/python')
print(f'Adding to sys.path: {layer_path}')
sys.path.insert(0, layer_path)

print('Current sys.path (first 3):')
for i, path in enumerate(sys.path[:3]):
    print(f'  {i}: {path}')

print('')
print('Testing import...')
try:
    from utils.DocumentIDManager import DocumentIDManager
    print('SUCCESS: DocumentIDManager imported!')
    
    # Test instantiation
    manager = DocumentIDManager()
    print('SUCCESS: DocumentIDManager instantiated!')
    
except Exception as e:
    print(f'FAILED: {e}')
    
    # Debug what's actually in the utils directory
    import os
    utils_path = os.path.join(layer_path, 'utils')
    print(f'Contents of {utils_path}:')
    if os.path.exists(utils_path):
        for item in os.listdir(utils_path):
            print(f'  {item}')
    else:
        print('  utils directory does not exist!')
"
EOF