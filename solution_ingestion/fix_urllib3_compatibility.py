#!/usr/bin/env python3
"""
Fix urllib3 compatibility issue on EC2
Downgrades urllib3 to compatible version
"""

import subprocess
import sys

def run_remote_command(cmd, description):
    """Run command on EC2."""
    print("\n" + description)
    print("=" * len(description))
    
    full_cmd = 'ssh ec2-user@ec2-dev "{}"'.format(cmd)
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def main():
    """Fix urllib3 compatibility on EC2."""
    
    print("Fixing urllib3 compatibility on EC2")
    print("=" * 40)
    
    # Check current urllib3 version
    run_remote_command(
        "python3 -c 'import urllib3; print(f\"urllib3 version: {urllib3.__version__}\")'",
        "Checking current urllib3 version"
    )
    
    # Install compatible urllib3 version
    run_remote_command(
        "pip3 install --user 'urllib3<2.0'",
        "Installing compatible urllib3 version"
    )
    
    # Verify fix
    run_remote_command(
        "python3 -c 'import urllib3; print(f\"urllib3 version: {urllib3.__version__}\")'",
        "Verifying urllib3 version"
    )
    
    # Test the imports now
    print("\nTesting layer imports after fix...")
    test_cmd = '''ssh ec2-user@ec2-dev << 'EOF'
cd ~/climate-risk-rag-aws/solution_ingestion
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('layers/database-core-layer/python').absolute()))
try:
    from utils.DocumentIDManager import DocumentIDManager
    from utils.DatabaseManager import DatabaseManager
    print('✅ Database layer imports successful!')
except Exception as e:
    print(f'❌ Still failing: {e}')
"
EOF'''
    
    subprocess.run(test_cmd, shell=True)

if __name__ == "__main__":
    main()