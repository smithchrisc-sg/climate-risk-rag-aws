#!/usr/bin/env python3
"""
Deploy Solution Ingestion Utility to EC2
Creates standalone deployment package with clean layer copies
"""

import os
import shutil
import zipfile
from pathlib import Path

def create_deployment_package():
    """Create deployment package for EC2"""
    
    # Create deployment directory
    deploy_dir = Path("solution_ingestion_deployment")
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir)
    deploy_dir.mkdir()
    
    # Copy main utility
    shutil.copy("solution_ingestion_utility.py", deploy_dir)
    
    # Copy clean layer utilities
    layer_source = Path("layers/database-core-layer/python")
    layer_dest = deploy_dir / "layers" / "database-core-layer" / "python"
    layer_dest.mkdir(parents=True)
    
    # Copy only essential utilities
    essential_utils = [
        "utils/database_manager.py",
        "utils/document_id_manager.py", 
        "utils/uri_manager.py",
        "utils/text_normalizer.py",
        "utils/triple_manager.py"
    ]
    
    for util_path in essential_utils:
        src = layer_source / util_path
        dst = layer_dest / util_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy(src, dst)
    
    # Create requirements.txt
    requirements = [
        "boto3>=1.26.0",
        "psycopg2-binary>=2.9.0",
        "opensearch-py>=2.0.0"
    ]
    
    with open(deploy_dir / "requirements.txt", "w") as f:
        f.write("\n".join(requirements))
    
    # Create deployment README
    readme_content = """# Solution Ingestion Utility Deployment

## Setup on EC2
1. Install dependencies: `pip install -r requirements.txt`
2. Configure AWS credentials and database connection
3. Run: `python solution_ingestion_utility.py <solutions.csv>`

## Environment Variables Required
- DATABASE_URL: PostgreSQL connection string
- OPENSEARCH_ENDPOINT: OpenSearch cluster endpoint
- AWS_REGION: AWS region (default: us-east-1)
"""
    
    with open(deploy_dir / "README.md", "w") as f:
        f.write(readme_content)
    
    # Create zip package
    with zipfile.ZipFile("solution_ingestion_package.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, deploy_dir)
                zf.write(file_path, arc_path)
    
    print(f"Deployment package created: solution_ingestion_package.zip")
    print(f"Package size: {os.path.getsize('solution_ingestion_package.zip')} bytes")

if __name__ == "__main__":
    create_deployment_package()
