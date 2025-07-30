#!/usr/bin/env python3
"""
Rebuild Database Core Layer with Dependencies
Properly installs psycopg2 and other dependencies
"""

import os
import subprocess
import zipfile
import boto3
import tempfile
import shutil

def main():
    """Rebuild database core layer with dependencies"""
    print("🔧 Rebuilding Database Core Layer with Dependencies")
    print("==================================================")
    
    layer_dir = "/Users/chris/climate-risk-rag-aws/layers/database-core-layer"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create layer structure
        python_dir = os.path.join(temp_dir, "python")
        os.makedirs(python_dir)
        
        # Install dependencies
        print("Installing dependencies...")
        requirements_file = os.path.join(layer_dir, "requirements.txt")
        
        subprocess.run([
            "pip", "install", 
            "-r", requirements_file,
            "-t", python_dir,
            "--no-deps"  # Install without dependencies to avoid conflicts
        ], check=True)
        
        # Install psycopg2-binary specifically
        print("Installing psycopg2-binary...")
        subprocess.run([
            "pip", "install", 
            "psycopg2-binary==2.9.7",
            "-t", python_dir
        ], check=True)
        
        # Install boto3
        print("Installing boto3...")
        subprocess.run([
            "pip", "install", 
            "boto3>=1.28.0",
            "-t", python_dir
        ], check=True)
        
        # Copy our utils directory
        print("Copying utils directory...")
        utils_source = os.path.join(layer_dir, "python", "utils")
        utils_dest = os.path.join(python_dir, "utils")
        shutil.copytree(utils_source, utils_dest)
        
        # Create zip file
        print("Creating layer zip...")
        zip_path = os.path.join(temp_dir, "database-core-layer.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(python_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Deploy new layer version
        print("Deploying new layer version...")
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        with open(zip_path, 'rb') as f:
            response = lambda_client.publish_layer_version(
                LayerName='database-core-layer',
                Description='Core database utilities with dependencies (v2)',
                Content={'ZipFile': f.read()},
                CompatibleRuntimes=['python3.11'],
                CompatibleArchitectures=['x86_64']
            )
        
        new_layer_arn = response['LayerVersionArn']
        print(f"✅ New layer deployed: {new_layer_arn}")
        
        # Update pipeline test function to use new layer
        print("Updating pipeline test function...")
        lambda_client.update_function_configuration(
            FunctionName='solve-global-kr-pipeline-test-function',
            Layers=[new_layer_arn]
        )
        
        print("✅ Pipeline test function updated with new layer")
        return new_layer_arn

if __name__ == "__main__":
    try:
        layer_arn = main()
        print(f"\n🎉 SUCCESS: Database core layer rebuilt and deployed")
        print(f"Layer ARN: {layer_arn}")
        print("\n🔧 Next: Test the pipeline test function")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
