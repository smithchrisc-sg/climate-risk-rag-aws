#!/usr/bin/env python3
"""
End-to-End Document Processing Test
1. Cleanup database
2. Copy a real document to source bucket
3. Trigger text extraction
4. Wait for and verify results
"""

import boto3
import json
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EndToEndTest:
    """End-to-end document processing test"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.s3_client = boto3.client('s3')
        
        # Buckets
        self.existing_bucket = "solve-global-kr-documents-861276078413-us-east-1"
        self.source_bucket = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
        self.text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        
        # Test document
        self.test_doc_key = "documents/07cf439f_b4e4c3d5.pdf"  # Known small document
        self.test_doc_id = "07cf439f_b4e4c3d5"
        
        logger.info("🧪 End-to-end test initialized")
    
    def step_1_cleanup(self):
        """Clean database"""
        logger.info("🧹 Step 1: Cleaning database...")
        
        cleanup_payload = {
            "cleanup_scope": {
                "databases": {
                    "postgresql": {
                        "enabled": True,
                        "tables": ["document_processing_status"],
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
        
        response = self.lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(cleanup_payload)
        )
        
        result = json.loads(response['Payload'].read())
        success = result.get('success', False)
        
        if success:
            logger.info("✅ Database cleaned")
        else:
            logger.error(f"❌ Cleanup failed: {result}")
        
        return success
    
    def step_2_copy_document(self):
        """Copy test document to source bucket"""
        logger.info("📄 Step 2: Copying test document to source bucket...")
        
        try:
            # Copy document from existing bucket to source bucket
            copy_source = {
                'Bucket': self.existing_bucket,
                'Key': self.test_doc_key
            }
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.source_bucket,
                Key=f"{self.test_doc_id}.pdf"
            )
            
            logger.info(f"✅ Copied {self.test_doc_key} to source bucket")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to copy document: {str(e)}")
            return False
    
    def step_3_trigger_text_extraction(self):
        """Trigger text extraction by invoking initiator"""
        logger.info("🚀 Step 3: Triggering text extraction...")
        
        # Create S3 event
        s3_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {
                            "name": self.source_bucket
                        },
                        "object": {
                            "key": f"{self.test_doc_id}.pdf"
                        }
                    }
                }
            ]
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-initiator',
                InvocationType='RequestResponse',
                Payload=json.dumps(s3_event)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                body = json.loads(result.get('body', '{}'))
                if body.get('success'):
                    logger.info("✅ Text extraction initiated successfully")
                    return True
                else:
                    logger.error(f"❌ Text extraction failed: {body.get('error')}")
                    return False
            else:
                logger.error(f"❌ Lambda invocation failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error triggering text extraction: {str(e)}")
            return False
    
    def step_4_wait_for_results(self, timeout_minutes=5):
        """Wait for text extraction results"""
        logger.info(f"⏳ Step 4: Waiting for text extraction results (timeout: {timeout_minutes} min)...")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check if extracted text file exists
                response = self.s3_client.list_objects_v2(
                    Bucket=self.text_bucket,
                    Prefix=f'extracted-text/{self.test_doc_id}.json'
                )
                
                if 'Contents' in response:
                    logger.info("✅ Text extraction completed!")
                    
                    # Read the extracted text
                    obj_response = self.s3_client.get_object(
                        Bucket=self.text_bucket,
                        Key=f'extracted-text/{self.test_doc_id}.json'
                    )
                    
                    content = json.loads(obj_response['Body'].read())
                    char_count = len(content.get('content', {}).get('full_text', ''))
                    
                    logger.info(f"   Document ID: {content.get('doc_id')}")
                    logger.info(f"   Characters extracted: {char_count}")
                    logger.info(f"   Extraction time: {content.get('extracted_at')}")
                    
                    return True
                
                # Wait before checking again
                logger.info(f"   Still waiting... ({int(time.time() - start_time)}s elapsed)")
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error checking results: {str(e)}")
                time.sleep(10)
        
        logger.error(f"❌ Timeout waiting for text extraction results")
        return False
    
    def step_5_verify_database(self):
        """Verify database was updated"""
        logger.info("🗄️ Step 5: Verifying database status...")
        
        health_payload = {"action": "health_check"}
        
        try:
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-pipeline-test-function',
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
                    
                    return total_docs > 0
                else:
                    logger.error(f"❌ Database unhealthy: {body}")
                    return False
            else:
                logger.error(f"❌ Database check failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database check error: {str(e)}")
            return False
    
    def run_end_to_end_test(self):
        """Run complete end-to-end test"""
        logger.info("🚀 Starting End-to-End Document Processing Test")
        logger.info(f"Test document: {self.test_doc_id}")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        steps = [
            ("Database Cleanup", self.step_1_cleanup),
            ("Copy Test Document", self.step_2_copy_document),
            ("Trigger Text Extraction", self.step_3_trigger_text_extraction),
            ("Wait for Results", self.step_4_wait_for_results),
            ("Verify Database", self.step_5_verify_database)
        ]
        
        results = {}
        
        for step_name, step_func in steps:
            logger.info(f"\\n{'='*20} {step_name} {'='*20}")
            
            try:
                success = step_func()
                results[step_name] = success
                
                if success:
                    logger.info(f"✅ {step_name}: PASSED")
                else:
                    logger.error(f"❌ {step_name}: FAILED")
                    # Don't continue if critical steps fail
                    if step_name in ["Database Cleanup", "Copy Test Document", "Trigger Text Extraction"]:
                        logger.error("Critical step failed, stopping test")
                        break
                        
            except Exception as e:
                logger.error(f"💥 {step_name}: ERROR - {str(e)}")
                results[step_name] = False
                break
        
        # Final assessment
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("\\n" + "=" * 60)
        logger.info("🏁 END-TO-END TEST RESULTS")
        logger.info("=" * 60)
        
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        for step_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{step_name:.<40} {status}")
        
        logger.info(f"\\nSUMMARY: {passed}/{total} steps passed")
        logger.info(f"Duration: {duration:.1f} seconds")
        
        if passed == total:
            logger.info("\\n🎉 END-TO-END TEST: COMPLETE SUCCESS!")
            logger.info("Full document processing pipeline is working!")
            return True
        else:
            logger.error(f"\\n💥 END-TO-END TEST: FAILED ({passed}/{total})")
            logger.error("Document processing pipeline has issues.")
            return False

def main():
    """Main entry point"""
    logger.info("🧪 End-to-End Document Processing Test")
    logger.info("Tests complete pipeline: Cleanup → Copy → Extract → Verify")
    
    test_runner = EndToEndTest()
    success = test_runner.run_end_to_end_test()
    
    if success:
        logger.info("\\n🏆 RESULT: End-to-end test PASSED!")
        exit(0)
    else:
        logger.error("\\n🔧 RESULT: End-to-end test FAILED!")
        exit(1)

if __name__ == "__main__":
    main()
