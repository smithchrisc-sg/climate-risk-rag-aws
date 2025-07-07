#!/usr/bin/env python3
"""
Deploy Corrected TextExtractor Processor
Archives current version and deploys the corrected DocumentIDManager integration
"""

import os
import sys
import json
import boto3
import shutil
import zipfile
import tempfile
from datetime import datetime
from typing import Dict, Any

class TextExtractorDeployment:
    """Handles deployment of corrected TextExtractor Processor"""
    
    def __init__(self, aws_profile: str = 'solve-global'):
        self.aws_profile = aws_profile
        self.session = boto3.Session(profile_name=aws_profile)
        self.lambda_client = self.session.client('lambda')
        self.s3_client = self.session.client('s3')
        
        # Function configuration
        self.function_name = 'solve-global-kr-textextractor-processor'
        self.region = 'us-east-1'
        self.account_id = self.session.client('sts').get_caller_identity()['Account']
        
        # Paths
        self.project_root = '/Users/chris/climate-risk-rag-aws'
        self.lambda_dir = f'{self.project_root}/lambda/text_extractor_processor'
        self.corrected_file = f'{self.lambda_dir}/text_extractor_processor_CORRECTED.py'
        self.original_file = f'{self.lambda_dir}/text_extractor_processor.py'
        self.backup_dir = f'{self.project_root}/backups'
        
        print(f"🚀 TextExtractor Deployment Manager")
        print(f"   AWS Profile: {aws_profile}")
        print(f"   Function: {self.function_name}")
        print(f"   Region: {self.region}")
        print(f"   Account: {self.account_id}")

    def create_backup_directory(self):
        """Create backup directory if it doesn't exist"""
        os.makedirs(self.backup_dir, exist_ok=True)
        print(f"📁 Backup directory ready: {self.backup_dir}")

    def archive_current_version(self) -> str:
        """Archive the current deployed Lambda function"""
        try:
            print("📦 Archiving current deployed version...")
            
            # Get current function code
            response = self.lambda_client.get_function(FunctionName=self.function_name)
            
            # Download current code
            code_location = response['Code']['Location']
            import requests
            code_response = requests.get(code_location)
            
            # Create backup filename with timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'textextractor_processor_backup_{timestamp}.zip'
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Save current code
            with open(backup_path, 'wb') as f:
                f.write(code_response.content)
            
            # Also backup current local file
            if os.path.exists(self.original_file):
                local_backup = os.path.join(self.backup_dir, f'text_extractor_processor_local_{timestamp}.py')
                shutil.copy2(self.original_file, local_backup)
                print(f"✅ Local file backed up: {local_backup}")
            
            print(f"✅ Current version archived: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"❌ Error archiving current version: {str(e)}")
            raise

    def prepare_corrected_version(self):
        """Prepare the corrected version for deployment"""
        try:
            print("🔧 Preparing corrected version...")
            
            if not os.path.exists(self.corrected_file):
                raise FileNotFoundError(f"Corrected file not found: {self.corrected_file}")
            
            # Replace the original file with corrected version
            shutil.copy2(self.corrected_file, self.original_file)
            print(f"✅ Replaced original with corrected version")
            
            # Ensure S3 mappings file is accessible
            mappings_file = f'{self.project_root}/selective_poc_s3_mappings.json'
            if os.path.exists(mappings_file):
                # Copy to lambda directory for packaging
                lambda_mappings = f'{self.lambda_dir}/selective_poc_s3_mappings.json'
                shutil.copy2(mappings_file, lambda_mappings)
                print(f"✅ S3 mappings included in package")
            else:
                print(f"⚠️  S3 mappings file not found: {mappings_file}")
            
        except Exception as e:
            print(f"❌ Error preparing corrected version: {str(e)}")
            raise

    def create_deployment_package(self) -> str:
        """Create deployment package for Lambda"""
        try:
            print("📦 Creating deployment package...")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                package_dir = os.path.join(temp_dir, 'package')
                os.makedirs(package_dir)
                
                # Copy Lambda function files
                for file in os.listdir(self.lambda_dir):
                    if file.endswith(('.py', '.json')):
                        src = os.path.join(self.lambda_dir, file)
                        dst = os.path.join(package_dir, file)
                        shutil.copy2(src, dst)
                
                # Rename main file to expected handler name
                main_file = os.path.join(package_dir, 'text_extractor_processor.py')
                if os.path.exists(main_file):
                    # The handler expects the main function to be in the file
                    print("✅ Main handler file ready")
                
                # Create zip file
                zip_path = f'{self.project_root}/textextractor_processor_corrected.zip'
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(package_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, package_dir)
                            zipf.write(file_path, arcname)
                
                print(f"✅ Deployment package created: {zip_path}")
                return zip_path
                
        except Exception as e:
            print(f"❌ Error creating deployment package: {str(e)}")
            raise

    def get_current_environment_variables(self) -> Dict[str, str]:
        """Get current Lambda environment variables"""
        try:
            response = self.lambda_client.get_function_configuration(FunctionName=self.function_name)
            current_env = response.get('Environment', {}).get('Variables', {})
            
            print("📋 Current environment variables:")
            for key, value in current_env.items():
                # Mask sensitive values
                display_value = value if 'PASSWORD' not in key.upper() else '***masked***'
                print(f"   {key}: {display_value}")
            
            return current_env
            
        except Exception as e:
            print(f"❌ Error getting environment variables: {str(e)}")
            return {}

    def update_environment_variables(self, current_env: Dict[str, str]) -> Dict[str, str]:
        """Update environment variables for corrected processor"""
        try:
            print("🔧 Updating environment variables...")
            
            # Required environment variables for corrected processor
            updated_env = current_env.copy()
            
            # Ensure OUTPUT_BUCKET points to new text bucket
            updated_env['OUTPUT_BUCKET'] = f'solve-global-kr-text-new-{self.account_id}-{self.region}'
            
            # Ensure DATABASE_URL is set (should already be there)
            if 'DATABASE_URL' not in updated_env:
                print("⚠️  DATABASE_URL not found in current environment")
                print("   This will need to be set manually or the function will fail")
            
            # Add any new environment variables needed
            updated_env['DOCUMENTID_MANAGER_INTEGRATION'] = 'true'
            updated_env['SELECTIVE_MIGRATION_ENABLED'] = 'true'
            updated_env['STRUCTURE_VERSION'] = '2025-07-04-corrected'
            
            print("📋 Updated environment variables:")
            for key, value in updated_env.items():
                if key not in current_env or current_env[key] != value:
                    display_value = value if 'PASSWORD' not in key.upper() else '***masked***'
                    print(f"   🆕 {key}: {display_value}")
            
            return updated_env
            
        except Exception as e:
            print(f"❌ Error updating environment variables: {str(e)}")
            raise

    def deploy_function(self, zip_path: str, updated_env: Dict[str, str]):
        """Deploy the corrected Lambda function"""
        try:
            print("🚀 Deploying corrected Lambda function...")
            
            # Read the zip file
            with open(zip_path, 'rb') as zip_file:
                zip_content = zip_file.read()
            
            # Update function code
            print("   Updating function code...")
            code_response = self.lambda_client.update_function_code(
                FunctionName=self.function_name,
                ZipFile=zip_content
            )
            
            print(f"   ✅ Code updated: {code_response['CodeSize']} bytes")
            
            # Update environment variables
            print("   Updating environment variables...")
            env_response = self.lambda_client.update_function_configuration(
                FunctionName=self.function_name,
                Environment={'Variables': updated_env}
            )
            
            print(f"   ✅ Environment updated")
            
            # Wait for function to be ready
            print("   Waiting for function to be ready...")
            waiter = self.lambda_client.get_waiter('function_updated')
            waiter.wait(FunctionName=self.function_name)
            
            print("✅ Deployment completed successfully!")
            
            return {
                'function_arn': code_response['FunctionArn'],
                'code_size': code_response['CodeSize'],
                'last_modified': code_response['LastModified'],
                'environment_updated': True
            }
            
        except Exception as e:
            print(f"❌ Error deploying function: {str(e)}")
            raise

    def verify_deployment(self):
        """Verify the deployment was successful"""
        try:
            print("🔍 Verifying deployment...")
            
            # Get function configuration
            response = self.lambda_client.get_function_configuration(FunctionName=self.function_name)
            
            print("✅ Deployment verification:")
            print(f"   Function Name: {response['FunctionName']}")
            print(f"   Runtime: {response['Runtime']}")
            print(f"   Handler: {response['Handler']}")
            print(f"   Last Modified: {response['LastModified']}")
            print(f"   Code Size: {response['CodeSize']} bytes")
            print(f"   Timeout: {response['Timeout']} seconds")
            print(f"   Memory: {response['MemorySize']} MB")
            
            # Check key environment variables
            env_vars = response.get('Environment', {}).get('Variables', {})
            key_vars = ['DATABASE_URL', 'OUTPUT_BUCKET', 'DOCUMENTID_MANAGER_INTEGRATION']
            
            print("   Key Environment Variables:")
            for var in key_vars:
                if var in env_vars:
                    value = env_vars[var] if 'PASSWORD' not in var else '***masked***'
                    print(f"     ✅ {var}: {value}")
                else:
                    print(f"     ❌ {var}: NOT SET")
            
            return True
            
        except Exception as e:
            print(f"❌ Error verifying deployment: {str(e)}")
            return False

    def cleanup_deployment_files(self, zip_path: str):
        """Clean up temporary deployment files"""
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
                print(f"🧹 Cleaned up deployment package: {zip_path}")
            
            # Remove S3 mappings from lambda directory (keep original)
            lambda_mappings = f'{self.lambda_dir}/selective_poc_s3_mappings.json'
            if os.path.exists(lambda_mappings):
                os.remove(lambda_mappings)
                print("🧹 Cleaned up temporary S3 mappings file")
                
        except Exception as e:
            print(f"⚠️  Error during cleanup: {str(e)}")

    def deploy(self):
        """Execute complete deployment process"""
        try:
            print("🚀 Starting TextExtractor Processor Deployment")
            print("=" * 60)
            
            # Step 1: Create backup directory
            self.create_backup_directory()
            
            # Step 2: Archive current version
            backup_path = self.archive_current_version()
            
            # Step 3: Prepare corrected version
            self.prepare_corrected_version()
            
            # Step 4: Create deployment package
            zip_path = self.create_deployment_package()
            
            # Step 5: Get current environment variables
            current_env = self.get_current_environment_variables()
            
            # Step 6: Update environment variables
            updated_env = self.update_environment_variables(current_env)
            
            # Step 7: Deploy function
            deploy_result = self.deploy_function(zip_path, updated_env)
            
            # Step 8: Verify deployment
            verification_success = self.verify_deployment()
            
            # Step 9: Cleanup
            self.cleanup_deployment_files(zip_path)
            
            print("\n🎉 Deployment Summary")
            print("=" * 30)
            print(f"✅ Current version backed up: {backup_path}")
            print(f"✅ Corrected version deployed: {deploy_result['function_arn']}")
            print(f"✅ Code size: {deploy_result['code_size']} bytes")
            print(f"✅ Environment variables updated")
            print(f"✅ Verification: {'PASSED' if verification_success else 'FAILED'}")
            
            print("\n📋 Key Changes Deployed:")
            print("  • DocumentIDManager integration")
            print("  • Selective migration S3 mappings support")
            print("  • GUID-based doc_id directory structure")
            print("  • Enhanced message format for text chunker")
            print("  • Fallback strategy for new documents")
            
            print("\n🧪 Ready for Testing:")
            print("  • Function is deployed and ready")
            print("  • Test with existing POC document")
            print("  • Monitor CloudWatch logs for integration")
            print("  • Verify S3 structure uses proper doc_ids")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {str(e)}")
            print("\n🔄 Rollback Information:")
            print(f"   Backup available: {backup_path if 'backup_path' in locals() else 'Not created'}")
            print("   Manual rollback may be required")
            return False

def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy Corrected TextExtractor Processor')
    parser.add_argument('--profile', default='solve-global', help='AWS profile to use')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deployed without deploying')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No actual deployment will occur")
        print("This would deploy the corrected TextExtractor Processor with:")
        print("  • DocumentIDManager integration")
        print("  • Selective migration support")
        print("  • Updated environment variables")
        print("  • Backup of current version")
        return True
    
    # Execute deployment
    deployer = TextExtractorDeployment(aws_profile=args.profile)
    success = deployer.deploy()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
