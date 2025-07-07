#!/usr/bin/env python3
"""
Create Lambda layer with sentence-transformers for vector embeddings
"""
import os
import subprocess
import shutil
import boto3
import zipfile

def create_embeddings_layer():
    """Create lambda layer with sentence-transformers"""
    
    print("Creating Vector Embeddings Lambda Layer")
    print("=" * 50)
    
    # Create temporary directory
    layer_dir = "/tmp/vector-embeddings-layer"
    python_dir = os.path.join(layer_dir, "python")
    
    # Clean up if exists
    if os.path.exists(layer_dir):
        shutil.rmtree(layer_dir)
    
    os.makedirs(python_dir, exist_ok=True)
    
    print("Installing sentence-transformers...")
    
    # Install sentence-transformers and dependencies
    subprocess.run([
        "pip", "install", 
        "sentence-transformers==2.2.2",
        "numpy>=1.24.0",
        "--target", python_dir,
        "--no-deps"  # Install only what we need
    ], check=True)
    
    # Install core dependencies
    subprocess.run([
        "pip", "install",
        "torch==2.0.1",
        "transformers==4.21.0", 
        "tokenizers==0.13.3",
        "huggingface-hub==0.16.4",
        "--target", python_dir,
        "--no-deps"
    ], check=True)
    
    print("Creating layer zip file...")
    
    # Create zip file
    zip_path = "/tmp/vector-embeddings-layer.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(layer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, layer_dir)
                zipf.write(file_path, arc_path)
    
    print("Uploading layer to AWS...")
    
    # Upload to AWS Lambda
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    with open(zip_path, 'rb') as f:
        response = lambda_client.publish_layer_version(
            LayerName='vector-embeddings-dependencies',
            Description='SentenceTransformers and vector processing dependencies',
            Content={'ZipFile': f.read()},
            CompatibleRuntimes=['python3.11'],
            CompatibleArchitectures=['x86_64']
        )
    
    layer_arn = response['LayerVersionArn']
    print("SUCCESS: Layer created!")
    print("Layer ARN: {}".format(layer_arn))
    
    # Clean up
    shutil.rmtree(layer_dir)
    os.remove(zip_path)
    
    return layer_arn

if __name__ == "__main__":
    try:
        layer_arn = create_embeddings_layer()
        print("\nUpdate your CDK stack with this layer ARN:")
        print(layer_arn)
    except Exception as e:
        print("ERROR: {}".format(str(e)))
        print("You may need to create this layer manually or use a smaller dependency set")
