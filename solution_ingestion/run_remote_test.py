#!/usr/bin/env python3
"""
Remote Test Runner
Copies files to EC2 and runs tests via SSH
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{description}")
    print("=" * len(description))
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode != 0:
            print(f"❌ Command failed with exit code {result.returncode}")
            return False
        else:
            print("✅ Command completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def main():
    """Run remote tests."""
    
    ec2_host = "ec2-user@ec2-dev"
    remote_dir = "~/climate-risk-rag-aws/solution_ingestion"
    
    print("Remote Test Execution")
    print("=" * 30)
    print(f"EC2: {ec2_host}")
    print(f"Remote dir: {remote_dir}")
    
    # Create remote directory
    create_dir_cmd = f'ssh {ec2_host} "mkdir -p {remote_dir}"'
    if not run_command(create_dir_cmd, "Creating remote directory"):
        return False
    
    # Copy files
    copy_cmd = f'scp -r ./* {ec2_host}:{remote_dir}/'
    if not run_command(copy_cmd, "Copying files to EC2"):
        return False
    
    # Run tests
    test_cmd = f'''ssh {ec2_host} << 'EOF'
cd {remote_dir}
echo "Running local setup test..."
python3 test_local_setup.py
echo ""
echo "Running layer import diagnostics..."
python3 test_layer_imports.py
EOF'''
    
    run_command(test_cmd, "Running tests on EC2")
    
    print("\n" + "=" * 50)
    print("Remote test execution complete!")

if __name__ == "__main__":
    main()