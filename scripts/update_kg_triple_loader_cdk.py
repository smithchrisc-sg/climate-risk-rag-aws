#!/usr/bin/env python3
"""
Update CDK files to rename kg-integration-worker to kg-triple-loader
"""
import os
import re

def update_cdk_files():
    """Update all CDK files with new kg-triple-loader naming"""
    
    cdk_dir = "/Users/chris/climate-risk-rag-aws/cdk"
    
    # Files that contain kg-integration-worker references
    files_to_update = [
        "app_document_structure_kg.py",
        "app_complete_standardized.py", 
        "app_kg_test.py",
        "app_production_ready.py",
        "app_production_ready_fixed.py",
        "app_kg_refactored.py"
    ]
    
    replacements = [
        # Function names and identifiers
        ("kg-integration-worker", "kg-triple-loader"),
        ("kg_integration_worker", "kg_triple_loader"),
        ("KGIntegrationWorker", "KGTripleLoader"),
        ("solve-global-kr-kg-integration-worker", "solve-global-kr-kg-triple-loader"),
        
        # Comments and descriptions
        ("KG Integration Worker", "KG Triple Loader"),
        ("integration worker", "triple loader"),
        ("Integration Worker", "Triple Loader"),
        
        # Directory references
        ("../lambda/kg-integration-worker", "../lambda/kg-triple-loader"),
        
        # Variable names
        ("kg_integration_worker", "kg_triple_loader"),
        ("self.kg_integration_worker", "self.kg_triple_loader"),
    ]
    
    updated_files = []
    
    for filename in files_to_update:
        filepath = os.path.join(cdk_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filepath}")
            continue
            
        try:
            # Read file
            with open(filepath, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Apply replacements
            for old_text, new_text in replacements:
                content = content.replace(old_text, new_text)
            
            # Write back if changed
            if content != original_content:
                with open(filepath, 'w') as f:
                    f.write(content)
                updated_files.append(filename)
                print(f"✅ Updated: {filename}")
            else:
                print(f"📋 No changes needed: {filename}")
                
        except Exception as e:
            print(f"❌ Error updating {filename}: {e}")
    
    return updated_files

def update_lambda_function_name():
    """Update the actual Lambda function name in AWS"""
    print("\n🔧 Lambda Function Renaming:")
    print("Note: AWS Lambda doesn't support renaming functions directly.")
    print("The CDK deployment will create a new function with the new name.")
    print("The old function will need to be manually deleted after verification.")
    
    return True

if __name__ == "__main__":
    print("🚀 Updating CDK files for kg-triple-loader rename...")
    print("=" * 60)
    
    updated_files = update_cdk_files()
    
    print(f"\n📊 Summary:")
    print(f"✅ Updated {len(updated_files)} CDK files")
    
    if updated_files:
        print(f"📋 Updated files:")
        for filename in updated_files:
            print(f"  - {filename}")
    
    update_lambda_function_name()
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Review the updated CDK files")
    print(f"2. Deploy with: cdk deploy --all")
    print(f"3. Verify new kg-triple-loader function works")
    print(f"4. Delete old kg-integration-worker function")
    print(f"5. Update any SNS topic subscriptions")
