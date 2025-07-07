#!/usr/bin/env python3
"""
Create Lambda layer with numpy and basic scientific computing dependencies
"""
import os
import subprocess
import shutil
import boto3
import zipfile
import tempfile

def create_numpy_layer():
    """Create lambda layer with numpy and scientific dependencies"""
    
    print("Creating NumPy Lambda Layer for SentenceTransformers")
    print("=" * 60)
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        layer_dir = os.path.join(temp_dir, "numpy-layer")
        python_dir = os.path.join(layer_dir, "python")
        
        os.makedirs(python_dir, exist_ok=True)
        
        print("Installing numpy and dependencies...")
        
        # Install core scientific computing packages
        packages = [
            "numpy==1.24.3",
            "scipy==1.10.1", 
            "scikit-learn==1.3.0",
            "joblib==1.3.2",
            "threadpoolctl==3.2.0"
        ]
        
        for package in packages:
            print("Installing {}...".format(package))
            try:
                subprocess.run([
                    "pip", "install", package,
                    "--target", python_dir,
                    "--no-deps",
                    "--platform", "linux_x86_64",
                    "--only-binary=:all:"
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                print("Warning: Failed to install {} - {}".format(package, e))
                # Try without platform specification
                try:
                    subprocess.run([
                        "pip", "install", package,
                        "--target", python_dir,
                        "--no-deps"
                    ], check=True, capture_output=True)
                except subprocess.CalledProcessError:
                    print("Skipping {} due to installation issues".format(package))
        
        print("Creating layer zip file...")
        
        # Create zip file
        zip_path = os.path.join(temp_dir, "numpy-layer.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(layer_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, layer_dir)
                    zipf.write(file_path, arc_path)
        
        # Check zip size
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
        print("Layer zip size: {:.1f} MB".format(zip_size))
        
        if zip_size > 250:
            print("WARNING: Layer size exceeds 250MB limit. Trying minimal approach...")
            return create_minimal_numpy_layer()
        
        print("Uploading layer to AWS...")
        
        # Upload to AWS Lambda
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda', region_name='us-east-1')
        
        with open(zip_path, 'rb') as f:
            response = lambda_client.publish_layer_version(
                LayerName='numpy-scientific-computing',
                Description='NumPy and scientific computing dependencies for SentenceTransformers',
                Content={'ZipFile': f.read()},
                CompatibleRuntimes=['python3.11'],
                CompatibleArchitectures=['x86_64']
            )
        
        layer_arn = response['LayerVersionArn']
        print("SUCCESS: NumPy layer created!")
        print("Layer ARN: {}".format(layer_arn))
        
        return layer_arn

def create_minimal_numpy_layer():
    """Create minimal numpy layer if full layer is too large"""
    
    print("Creating minimal NumPy layer...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        layer_dir = os.path.join(temp_dir, "minimal-numpy")
        python_dir = os.path.join(layer_dir, "python")
        
        os.makedirs(python_dir, exist_ok=True)
        
        # Install only numpy
        subprocess.run([
            "pip", "install", "numpy==1.24.3",
            "--target", python_dir,
            "--platform", "linux_x86_64",
            "--only-binary=:all:"
        ], check=True)
        
        # Create zip
        zip_path = os.path.join(temp_dir, "minimal-numpy.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(layer_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, layer_dir)
                    zipf.write(file_path, arc_path)
        
        # Upload minimal layer
        session = boto3.Session(profile_name='solve-global')
        lambda_client = session.client('lambda', region_name='us-east-1')
        
        with open(zip_path, 'rb') as f:
            response = lambda_client.publish_layer_version(
                LayerName='minimal-numpy',
                Description='Minimal NumPy for Lambda functions',
                Content={'ZipFile': f.read()},
                CompatibleRuntimes=['python3.11'],
                CompatibleArchitectures=['x86_64']
            )
        
        return response['LayerVersionArn']

if __name__ == "__main__":
    try:
        layer_arn = create_numpy_layer()
        print("\nLayer created successfully!")
        print("ARN: {}".format(layer_arn))
        print("\nNext: Update worker function to use this layer")
    except Exception as e:
        print("ERROR: {}".format(str(e)))
        print("Trying minimal approach...")
        try:
            layer_arn = create_minimal_numpy_layer()
            print("Minimal layer created: {}".format(layer_arn))
        except Exception as e2:
            print("ERROR: Both approaches failed - {}".format(str(e2)))
