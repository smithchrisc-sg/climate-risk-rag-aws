#!/bin/bash
# Solution Ingestion Deployment Script

set -e

echo "Setting up Python path for layers..."
export PYTHONPATH="./layers/database-core-layer/python:./layers/knowledge-graph-layer/python:$PYTHONPATH"

echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo "Verifying layer imports..."
python3 -c "
import sys
sys.path.insert(0, './layers/database-core-layer/python')
sys.path.insert(0, './layers/knowledge-graph-layer/python')
from utils.DatabaseManager import DatabaseManager
from utils.DocumentIDManager import DocumentIDManager
from utils.KnowledgeGraphManager import KnowledgeGraphManager
print('✅ Layer imports successful')
"

echo "✅ Deployment complete. Ready to run:"
echo "python3 main.py --csv-path input_data/solutions.csv --output-dir output_data/"
