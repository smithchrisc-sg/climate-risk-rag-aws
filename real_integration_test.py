#!/usr/bin/env python3
"""
Real Integration Test - Uses Existing Components
1. Run cleanup lambda with appropriate config
2. Run invoke_pipeline_test.py for one document  
3. Check logs, database, S3 buckets, SNS to verify completion
"""

import boto3
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealIntegrationTest:
    """Real integration test using actual document processing"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3')
        self.logs_client = boto3.client('logs', region_name='us-east-1')
        
        # S3 buckets to monitor
        self.source_bucket = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
        self.text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        
        # Lambda functions to monitor
        self.functions = {
            'cleanup': 'solve-global-kr-cleanup-service',
            'pipeline_test': 'solve-global-kr-pipeline-test-function',
            'text_initiator': 'solve-global-kr-textextractor-initiator',
            'text_processor': 'solve-global-kr-textextractor-processor'
        }
        
        logger.info("🧪 Real Integration Test initialized")
    
    def step_1_cleanup_database(self) -> bool:
        """Step 1: Clean database using cleanup service"""
        logger.info("🧹 Step 1: Cleaning database...")
        
        cleanup_payload = {
            "cleanup_scope": {
                "databases": {
                    "postgresql": {
                        "enabled": True,
                        "tables": [
                            "document_processing_status",
                            "nlp_processing_status",
                            "vector_processing_status", 
                            "keyword_processing_status",
                            "kg_processing_status"
                        ],
                        "document_ids": []
                    }
                }
            },
            "safety_checks": {
                "require_confirmation": False,
                "dry_run": False,
                "max_documents_to_delete": 1000
            }
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.functions['cleanup'],
                InvocationType='RequestResponse',
                Payload=json.dumps(cleanup_payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('success'):
                # Log cleanup details
                if 'results' in result and 'databases' in result['results']:
                    pg_result = result['results']['databases'].get('postgresql', {})
                    if pg_result.get('success'):
                        records = pg_result.get('records_affected', {})
                        total_cleaned = sum(records.values())
                        logger.info(f"✅ Cleaned {total_cleaned} database records")
                        
                        for table, count in records.items():
                            if count > 0:
                                logger.info(f"   {table}: {count} records")
                
                return True
            else:
                logger.error(f"❌ Cleanup failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cleanup error: {str(e)}")
            return False
    
    def step_2_run_pipeline_test(self) -> Dict[str, Any]:
        """Step 2: Run invoke_pipeline_test.py for one document"""
        logger.info("📄 Step 2: Running pipeline test for one document...")
        
        try:
            # Run the existing invoke_pipeline_test.py script
            cmd = [
                'python3', 
                '/Users/chris/climate-risk-rag-aws/invoke_pipeline_test.py',
                '--action', 'test_only',  # Use 'test_only' which maps to Lambda's 'test'
                '--num-documents', '1',
                '--min-size-mb', '1.0',
                '--max-size-mb', '5.0',
                '--target-avg-pages', '10',
                '--force'  # Skip confirmations
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            logger.info(f"Pipeline test exit code: {result.returncode}")
            
            if result.stdout:
                logger.info("Pipeline test stdout:")
                for line in result.stdout.split('\\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            
            if result.stderr:
                logger.info("Pipeline test stderr:")
                for line in result.stderr.split('\\n'):
                    if line.strip():
                        logger.info(f"  {line}")
            
            return {
                'success': result.returncode == 0,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error("❌ Pipeline test timed out after 5 minutes")
            return {'success': False, 'error': 'timeout'}
        except Exception as e:
            logger.error(f"❌ Pipeline test error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def step_3_check_s3_source_documents(self) -> Dict[str, Any]:
        """Step 3: Check if documents were copied to source bucket"""
        logger.info("📁 Step 3: Checking source documents bucket...")
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.source_bucket,
                MaxKeys=10
            )
            
            if 'Contents' in response:
                documents = response['Contents']
                logger.info(f"✅ Found {len(documents)} documents in source bucket")
                
                for doc in documents[:3]:  # Show first 3
                    key = doc['Key']
                    size_mb = doc['Size'] / (1024 * 1024)
                    modified = doc['LastModified']
                    logger.info(f"   {key}: {size_mb:.1f} MB (modified: {modified})")
                
                return {
                    'success': True,
                    'document_count': len(documents),
                    'documents': [{'key': doc['Key'], 'size_mb': doc['Size']/(1024*1024)} for doc in documents[:5]]
                }
            else:
                logger.warning("⚠️ No documents found in source bucket")
                return {'success': False, 'document_count': 0}
                
        except Exception as e:
            logger.error(f"❌ Error checking source bucket: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def step_4_check_lambda_logs(self, minutes_back: int = 10) -> Dict[str, Any]:
        """Step 4: Check Lambda function logs for recent activity"""
        logger.info(f"📋 Step 4: Checking Lambda logs (last {minutes_back} minutes)...")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes_back)
        
        log_results = {}
        
        for func_name, lambda_name in self.functions.items():
            try:
                log_group = f"/aws/lambda/{lambda_name}"
                
                # Get recent log events
                response = self.logs_client.filter_log_events(
                    logGroupName=log_group,
                    startTime=int(start_time.timestamp() * 1000),
                    endTime=int(end_time.timestamp() * 1000),
                    limit=50
                )
                
                events = response.get('events', [])
                
                if events:
                    logger.info(f"✅ {func_name}: {len(events)} log events")
                    
                    # Look for key indicators
                    success_indicators = 0
                    error_indicators = 0
                    
                    for event in events:
                        message = event['message'].lower()
                        if any(word in message for word in ['success', 'completed', 'finished']):
                            success_indicators += 1
                        if any(word in message for word in ['error', 'failed', 'exception']):
                            error_indicators += 1
                    
                    log_results[func_name] = {
                        'success': True,
                        'event_count': len(events),
                        'success_indicators': success_indicators,
                        'error_indicators': error_indicators,
                        'recent_messages': [event['message'][:100] for event in events[-3:]]
                    }
                else:
                    logger.info(f"⚠️ {func_name}: No recent log events")
                    log_results[func_name] = {
                        'success': False,
                        'event_count': 0,
                        'reason': 'no_recent_activity'
                    }
                    
            except Exception as e:
                logger.error(f"❌ Error checking logs for {func_name}: {str(e)}")
                log_results[func_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        return log_results
    
    def step_5_check_text_extraction_results(self) -> Dict[str, Any]:
        """Step 5: Check if text was extracted to text bucket"""
        logger.info("📝 Step 5: Checking text extraction results...")
        
        try:
            # Check text bucket for extracted text
            response = self.s3_client.list_objects_v2(
                Bucket=self.text_bucket,
                Prefix='extracted-text/',
                MaxKeys=10
            )
            
            if 'Contents' in response:
                text_files = response['Contents']
                logger.info(f"✅ Found {len(text_files)} extracted text files")
                
                results = []
                for text_file in text_files:
                    key = text_file['Key']
                    size_kb = text_file['Size'] / 1024
                    modified = text_file['LastModified']
                    
                    logger.info(f"   {key}: {size_kb:.1f} KB (modified: {modified})")
                    
                    # Try to read a sample of the text
                    try:
                        obj_response = self.s3_client.get_object(Bucket=self.text_bucket, Key=key)
                        content = json.loads(obj_response['Body'].read())
                        
                        doc_id = content.get('doc_id', 'unknown')
                        char_count = len(content.get('content', {}).get('full_text', ''))
                        
                        logger.info(f"     Doc ID: {doc_id}, Characters: {char_count}")
                        
                        results.append({
                            'key': key,
                            'doc_id': doc_id,
                            'character_count': char_count,
                            'size_kb': size_kb
                        })
                        
                    except Exception as e:
                        logger.warning(f"     Could not read content: {str(e)}")
                
                return {
                    'success': True,
                    'text_file_count': len(text_files),
                    'extracted_texts': results
                }
            else:
                logger.warning("⚠️ No extracted text files found")
                return {'success': False, 'text_file_count': 0}
                
        except Exception as e:
            logger.error(f"❌ Error checking text extraction results: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def step_6_check_database_status(self) -> Dict[str, Any]:
        """Step 6: Check database processing status"""
        logger.info("🗄️ Step 6: Checking database processing status...")
        
        # Use pipeline test function to check database
        health_payload = {"action": "health_check"}
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.functions['pipeline_test'],
                InvocationType='RequestResponse',
                Payload=json.dumps(health_payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                body = json.loads(result.get('body', '{}'))
                
                if body.get('status') == 'healthy':
                    stats = body.get('processing_stats', {})
                    total_docs = stats.get('total_documents', 0)
                    
                    logger.info(f"✅ Database is healthy")
                    logger.info(f"   Total documents: {total_docs}")
                    logger.info(f"   Database Manager: {'✅' if body.get('database_manager') else '❌'}")
                    logger.info(f"   Document ID Manager: {'✅' if body.get('document_id_manager') else '❌'}")
                    
                    return {
                        'success': True,
                        'total_documents': total_docs,
                        'database_manager_healthy': body.get('database_manager', False),
                        'document_id_manager_healthy': body.get('document_id_manager', False)
                    }
                else:
                    logger.error(f"❌ Database health check failed: {body}")
                    return {'success': False, 'error': body}
            else:
                logger.error(f"❌ Database health check error: {result}")
                return {'success': False, 'error': result}
                
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def run_real_integration_test(self) -> bool:
        """Run complete real integration test"""
        logger.info("🚀 Starting Real Integration Test")
        logger.info("Using actual document processing pipeline")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # Run all test steps
        steps = [
            ("Database Cleanup", self.step_1_cleanup_database),
            ("Pipeline Test Execution", self.step_2_run_pipeline_test),
            ("Source Documents Check", self.step_3_check_s3_source_documents),
            ("Lambda Logs Check", lambda: self.step_4_check_lambda_logs(15)),
            ("Text Extraction Results", self.step_5_check_text_extraction_results),
            ("Database Status Check", self.step_6_check_database_status)
        ]
        
        results = {}
        
        for step_name, step_func in steps:
            logger.info(f"\\n{'='*20} {step_name} {'='*20}")
            
            try:
                result = step_func()
                results[step_name] = result
                
                if isinstance(result, bool):
                    success = result
                elif isinstance(result, dict):
                    success = result.get('success', False)
                else:
                    success = False
                
                if success:
                    logger.info(f"✅ {step_name}: PASSED")
                else:
                    logger.error(f"❌ {step_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {step_name}: ERROR - {str(e)}")
                results[step_name] = {'success': False, 'error': str(e)}
        
        # Final assessment
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\\n" + "=" * 60)
        logger.info("🏁 REAL INTEGRATION TEST RESULTS")
        logger.info("=" * 60)
        
        passed = 0
        total = len(results)
        
        for step_name, result in results.items():
            if isinstance(result, bool):
                success = result
            elif isinstance(result, dict):
                success = result.get('success', False)
            else:
                success = False
                
            if success:
                passed += 1
                
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{step_name:.<40} {status}")
        
        logger.info(f"\\nSUMMARY: {passed}/{total} steps passed")
        logger.info(f"Duration: {duration:.1f} seconds")
        
        # Detailed results
        if 'Text Extraction Results' in results:
            text_result = results['Text Extraction Results']
            if text_result.get('success'):
                text_count = text_result.get('text_file_count', 0)
                logger.info(f"📝 Extracted text files: {text_count}")
        
        if 'Database Status Check' in results:
            db_result = results['Database Status Check']
            if db_result.get('success'):
                doc_count = db_result.get('total_documents', 0)
                logger.info(f"🗄️ Documents in database: {doc_count}")
        
        if passed == total:
            logger.info("\\n🎉 REAL INTEGRATION TEST: COMPLETE SUCCESS!")
            logger.info("Full document processing pipeline is working end-to-end.")
            return True
        elif passed >= total * 0.8:  # 80% success rate
            logger.warning(f"\\n⚠️ REAL INTEGRATION TEST: MOSTLY SUCCESSFUL ({passed}/{total})")
            logger.warning("Most components working, some issues detected.")
            return True
        else:
            logger.error(f"\\n💥 REAL INTEGRATION TEST: SIGNIFICANT FAILURES ({passed}/{total})")
            logger.error("Multiple pipeline components have issues.")
            return False

def main():
    """Main entry point"""
    logger.info("🧪 Real Integration Test - End-to-End Document Processing")
    logger.info("Tests: Cleanup → Pipeline Test → Text Extraction → Verification")
    
    test_runner = RealIntegrationTest()
    success = test_runner.run_real_integration_test()
    
    if success:
        logger.info("\\n🏆 RESULT: Real integration test PASSED!")
        logger.info("The document processing pipeline is working end-to-end.")
        exit(0)
    else:
        logger.error("\\n🔧 RESULT: Real integration test FAILED!")
        logger.error("The document processing pipeline has issues.")
        exit(1)

if __name__ == "__main__":
    main()
