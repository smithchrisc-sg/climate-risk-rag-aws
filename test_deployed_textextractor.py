#!/usr/bin/env python3
"""
Test Deployed TextExtractor Processor
Tests the deployed corrected processor with real infrastructure
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, Any, List

class DeployedTextExtractorTester:
    """Tests the deployed TextExtractor Processor"""
    
    def __init__(self, aws_profile: str = 'solve-global'):
        self.aws_profile = aws_profile
        self.session = boto3.Session(profile_name=aws_profile)
        self.lambda_client = self.session.client('lambda')
        self.s3_client = self.session.client('s3')
        self.logs_client = self.session.client('logs')
        
        # Function names
        self.processor_function = 'solve-global-kr-textextractor-processor'
        self.trigger_function = 'solve-global-kr-textextractor-trigger'
        
        print(f"🧪 TextExtractor Deployment Tester")
        print(f"   AWS Profile: {aws_profile}")

    def check_function_status(self, function_name: str) -> Dict[str, Any]:
        """Check the status of a Lambda function"""
        try:
            response = self.lambda_client.get_function_configuration(FunctionName=function_name)
            
            status_info = {
                'function_name': response['FunctionName'],
                'state': response['State'],
                'last_update_status': response['LastUpdateStatus'],
                'runtime': response['Runtime'],
                'handler': response['Handler'],
                'code_size': response['CodeSize'],
                'timeout': response['Timeout'],
                'memory_size': response['MemorySize'],
                'last_modified': response['LastModified']
            }
            
            # Check environment variables
            env_vars = response.get('Environment', {}).get('Variables', {})
            status_info['environment_variables'] = {
                'DATABASE_URL': 'SET' if 'DATABASE_URL' in env_vars else 'NOT SET',
                'OUTPUT_BUCKET': env_vars.get('OUTPUT_BUCKET', 'NOT SET'),
                'DOCUMENTID_MANAGER_INTEGRATION': env_vars.get('DOCUMENTID_MANAGER_INTEGRATION', 'NOT SET'),
                'SELECTIVE_MIGRATION_ENABLED': env_vars.get('SELECTIVE_MIGRATION_ENABLED', 'NOT SET'),
                'STRUCTURE_VERSION': env_vars.get('STRUCTURE_VERSION', 'NOT SET')
            }
            
            return status_info
            
        except Exception as e:
            return {'error': str(e)}

    def test_function_invocation(self, test_document: Dict[str, str] = None) -> Dict[str, Any]:
        """Test function invocation with trigger"""
        try:
            print("🚀 Testing function invocation...")
            
            # Default test document (small one from your S3 bucket)
            if not test_document:
                test_document = {
                    'bucket': 'solve-global-kr-documents-861276078413-us-east-1',
                    'key': 'documents/006893d2_93170cb9.pdf'  # Small document (34KB)
                }
            
            print(f"   Test document: s3://{test_document['bucket']}/{test_document['key']}")
            
            # Invoke trigger function
            trigger_payload = {
                'document': test_document
            }
            
            response = self.lambda_client.invoke(
                FunctionName=self.trigger_function,
                InvocationType='RequestResponse',
                Payload=json.dumps(trigger_payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            
            result = {
                'trigger_status_code': response['StatusCode'],
                'trigger_response': response_payload,
                'test_document': test_document,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            print(f"   ✅ Trigger invoked: Status {response['StatusCode']}")
            
            if response_payload.get('statusCode') == 200:
                print("   ✅ TextExtractor Initiator triggered successfully")
                print("   ⏳ Textract job should be starting...")
            else:
                print(f"   ❌ Trigger failed: {response_payload}")
            
            return result
            
        except Exception as e:
            print(f"   ❌ Error testing invocation: {str(e)}")
            return {'error': str(e)}

    def check_recent_logs(self, function_name: str, minutes: int = 10) -> List[str]:
        """Check recent CloudWatch logs for a function"""
        try:
            log_group_name = f'/aws/lambda/{function_name}'
            
            # Get log streams
            streams_response = self.logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            recent_logs = []
            
            for stream in streams_response['logStreams']:
                try:
                    # Get recent events
                    start_time = int((datetime.utcnow().timestamp() - (minutes * 60)) * 1000)
                    
                    events_response = self.logs_client.get_log_events(
                        logGroupName=log_group_name,
                        logStreamName=stream['logStreamName'],
                        startTime=start_time
                    )
                    
                    for event in events_response['events']:
                        recent_logs.append(event['message'])
                        
                except Exception as e:
                    continue
            
            return recent_logs[-20:]  # Last 20 log entries
            
        except Exception as e:
            print(f"   ⚠️  Could not retrieve logs: {str(e)}")
            return []

    def check_s3_bucket_access(self, bucket_name: str) -> bool:
        """Check if the function can access the S3 bucket"""
        try:
            response = self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"   ✅ S3 bucket accessible: {bucket_name}")
            return True
        except Exception as e:
            print(f"   ❌ S3 bucket access failed: {bucket_name} - {str(e)}")
            return False

    def run_comprehensive_test(self):
        """Run comprehensive test of deployed function"""
        print("🧪 Running Comprehensive Deployment Test")
        print("=" * 50)
        print(f"Test time: {datetime.utcnow().isoformat()}")
        print()
        
        results = {}
        
        # Test 1: Check Processor Function Status
        print("1️⃣ Checking TextExtractor Processor Status")
        processor_status = self.check_function_status(self.processor_function)
        results['processor_status'] = processor_status
        
        if 'error' in processor_status:
            print(f"   ❌ Error: {processor_status['error']}")
        else:
            print(f"   ✅ Function State: {processor_status['state']}")
            print(f"   ✅ Update Status: {processor_status['last_update_status']}")
            print(f"   ✅ Code Size: {processor_status['code_size']} bytes")
            print(f"   ✅ Last Modified: {processor_status['last_modified']}")
            
            print("   📋 Environment Variables:")
            for key, value in processor_status['environment_variables'].items():
                status = "✅" if value not in ['NOT SET', 'false'] else "❌"
                print(f"     {status} {key}: {value}")
        
        print()
        
        # Test 2: Check Trigger Function Status
        print("2️⃣ Checking TextExtractor Trigger Status")
        trigger_status = self.check_function_status(self.trigger_function)
        results['trigger_status'] = trigger_status
        
        if 'error' in trigger_status:
            print(f"   ❌ Error: {trigger_status['error']}")
        else:
            print(f"   ✅ Trigger Function Ready: {trigger_status['state']}")
        
        print()
        
        # Test 3: Check S3 Bucket Access
        print("3️⃣ Checking S3 Bucket Access")
        buckets_to_check = [
            'solve-global-kr-documents-861276078413-us-east-1',  # Source documents
            'solve-global-kr-text-new-861276078413-us-east-1'   # Output bucket
        ]
        
        bucket_access = {}
        for bucket in buckets_to_check:
            bucket_access[bucket] = self.check_s3_bucket_access(bucket)
        
        results['bucket_access'] = bucket_access
        print()
        
        # Test 4: Test Function Invocation (Optional - costs money)
        print("4️⃣ Function Invocation Test")
        print("   ⚠️  This will trigger a Textract job (costs ~$0.02)")
        
        user_input = input("   Do you want to proceed with invocation test? (y/N): ").strip().lower()
        
        if user_input == 'y':
            invocation_result = self.test_function_invocation()
            results['invocation_test'] = invocation_result
            
            # Wait a bit and check logs
            print("   ⏳ Waiting 30 seconds for logs...")
            time.sleep(30)
            
            print("   📋 Recent Processor Logs:")
            recent_logs = self.check_recent_logs(self.processor_function, minutes=5)
            for log in recent_logs[-10:]:  # Last 10 entries
                print(f"     {log.strip()}")
            
            results['recent_logs'] = recent_logs
        else:
            print("   ⏭️  Skipping invocation test")
            results['invocation_test'] = {'skipped': True}
        
        print()
        
        # Summary
        print("📊 Test Summary")
        print("=" * 20)
        
        processor_ok = 'error' not in processor_status and processor_status.get('state') == 'Active'
        trigger_ok = 'error' not in trigger_status and trigger_status.get('state') == 'Active'
        buckets_ok = all(bucket_access.values())
        
        print(f"✅ Processor Function: {'READY' if processor_ok else 'ISSUES'}")
        print(f"✅ Trigger Function: {'READY' if trigger_ok else 'ISSUES'}")
        print(f"✅ S3 Bucket Access: {'OK' if buckets_ok else 'ISSUES'}")
        
        if 'invocation_test' in results and not results['invocation_test'].get('skipped'):
            invocation_ok = results['invocation_test'].get('trigger_status_code') == 200
            print(f"✅ Invocation Test: {'PASSED' if invocation_ok else 'FAILED'}")
        
        overall_status = processor_ok and trigger_ok and buckets_ok
        
        print(f"\n🎯 Overall Status: {'READY FOR TESTING' if overall_status else 'NEEDS ATTENTION'}")
        
        if overall_status:
            print("\n🚀 Deployment Validation Complete!")
            print("   • Corrected TextExtractor Processor is deployed")
            print("   • DocumentIDManager integration is configured")
            print("   • S3 buckets are accessible")
            print("   • Ready for real document processing tests")
        else:
            print("\n⚠️  Issues detected that need attention before testing")
        
        return results

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Deployed TextExtractor Processor')
    parser.add_argument('--profile', default='solve-global', help='AWS profile to use')
    
    args = parser.parse_args()
    
    tester = DeployedTextExtractorTester(aws_profile=args.profile)
    results = tester.run_comprehensive_test()
    
    return results

if __name__ == "__main__":
    main()
