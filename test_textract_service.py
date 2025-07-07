#!/usr/bin/env python3
"""
Test Textract service configuration and capabilities
"""

import boto3
import json

def test_textract_service():
    """Test Textract service configuration"""
    
    print("AWS Textract Service Configuration Test")
    print("=" * 60)
    
    session = boto3.Session(profile_name='solve-global')
    
    # Test different regions
    regions_to_test = ['us-east-1', 'us-west-2', 'eu-west-1']
    
    for region in regions_to_test:
        print(f"\nTesting region: {region}")
        print("-" * 30)
        
        try:
            textract = session.client('textract', region_name=region)
            
            # Test basic service availability
            try:
                # This should fail with InvalidJobIdException if service is working
                response = textract.get_document_analysis(JobId='test-job-id')
            except Exception as e:
                if 'InvalidJobIdException' in str(e):
                    print(f"✅ Service available in {region}")
                elif 'AccessDenied' in str(e):
                    print(f"❌ Access denied in {region}")
                else:
                    print(f"🤔 Unexpected response in {region}: {type(e).__name__}")
            
            # Check service limits/quotas
            try:
                # Try to get service quotas (if available)
                quotas = session.client('service-quotas', region_name=region)
                
                # List Textract quotas
                textract_quotas = quotas.list_service_quotas(
                    ServiceCode='textract'
                )
                
                print(f"📊 Textract quotas in {region}:")
                for quota in textract_quotas.get('Quotas', []):
                    print(f"  - {quota['QuotaName']}: {quota['Value']}")
                    
            except Exception as e:
                print(f"⚠️  Could not retrieve quotas: {str(e)}")
                
        except Exception as e:
            print(f"❌ Error testing {region}: {str(e)}")
    
    # Test account identity
    print(f"\nAccount Information:")
    print("-" * 30)
    
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"Account ID: {identity.get('Account')}")
        print(f"User ARN: {identity.get('Arn')}")
        print(f"User ID: {identity.get('UserId')}")
        
    except Exception as e:
        print(f"❌ Could not get account info: {str(e)}")

if __name__ == "__main__":
    test_textract_service()
    
    print(f"\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("1. Try testing Textract in a different AWS region")
    print("2. Check if there are account-level restrictions")
    print("3. Verify Textract service quotas and limits")
    print("4. Consider opening AWS support case for Textract issues")
    print("="*60)
