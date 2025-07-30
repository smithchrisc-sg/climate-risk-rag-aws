#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update Lambda functions to support LAYOUT analysis
Updates text-extractor-initiator, text-extractor-processor, and text-chunker-processor
"""

import subprocess
import os
import sys
import zipfile
import tempfile
import shutil

def create_lambda_zip(lambda_dir, zip_name):
    """Create a deployment zip for a Lambda function"""
    print("Creating deployment package for {}".format(lambda_dir))
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Copy lambda source to temp directory
        lambda_temp = os.path.join(temp_dir, "lambda")
        shutil.copytree(lambda_dir, lambda_temp)
        
        # Create zip file
        zip_path = "{}/{}".format(lambda_dir, zip_name)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(lambda_temp):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, lambda_temp)
                    zipf.write(file_path, arcname)
        
        print("Created {}".format(zip_path))
        return zip_path
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir)

def update_lambda_function(function_name, zip_path):
    """Update Lambda function code"""
    print("Updating Lambda function: {}".format(function_name))
    
    try:
        cmd = [
            "aws", "lambda", "update-function-code",
            "--function-name", function_name,
            "--zip-file", "fileb://{}".format(zip_path),
            "--region", "us-east-1"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Successfully updated {}".format(function_name))
        return True
        
    except subprocess.CalledProcessError as e:
        print("Failed to update {}: {}".format(function_name, e.stderr))
        return False
    except AttributeError:
        # Fallback for older Python versions
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            print("Successfully updated {}".format(function_name))
            return True
        except subprocess.CalledProcessError as e:
            print("Failed to update {}: {}".format(function_name, e.output))
            return False

def main():
    """Main deployment function"""
    print("Updating Lambda functions for LAYOUT support")
    print("=" * 50)
    
    # Lambda functions to update
    functions_to_update = [
        {
            "name": "text-extractor-initiator",
            "dir": "lambda/text-extractor-initiator",
            "zip": "text-extractor-initiator-layout.zip"
        },
        {
            "name": "text-extractor-processor", 
            "dir": "lambda/text-extractor-processor",
            "zip": "text-extractor-processor-layout.zip"
        },
        {
            "name": "text-chunker-processor",
            "dir": "lambda/text-chunker-processor", 
            "zip": "text-chunker-processor-layout.zip"
        }
    ]
    
    success_count = 0
    
    for func in functions_to_update:
        print("\nProcessing {}".format(func['name']))
        
        # Check if directory exists
        if not os.path.exists(func['dir']):
            print("Directory not found: {}".format(func['dir']))
            continue
        
        # Create deployment package
        zip_path = create_lambda_zip(func['dir'], func['zip'])
        
        # Update Lambda function
        if update_lambda_function(func['name'], zip_path):
            success_count += 1
        
        # Clean up zip file
        if os.path.exists(zip_path):
            os.remove(zip_path)
    
    print("\nDeployment complete!")
    print("Successfully updated: {}/{}".format(success_count, len(functions_to_update)))
    
    if success_count == len(functions_to_update):
        print("\nAll Lambda functions updated successfully!")
        print("LAYOUT analysis is now enabled for:")
        print("   • Text extraction (Textract with LAYOUT feature)")
        print("   • Text processing (Layout blocks captured)")
        print("   • Smart chunking (Layout-aware structure analysis)")
        print("\nNext steps:")
        print("   • Test with a new document to see improved structure capture")
        print("   • Check CloudWatch logs for layout analysis details")
    else:
        print("\nSome functions failed to update. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
