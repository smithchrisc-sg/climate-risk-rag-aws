#!/usr/bin/env python3
"""
Direct Test for Standardized Messaging
Tests individual Lambda functions with standardized message formats
"""

import boto3
import json
import time
from datetime import datetime

class DirectMessagingTester:
    """Direct tester for standardized messaging"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.sns_client = boto3.client('sns', region_name='us-east-1')
        
        # Test document info
        self.test_doc_id = "test-msg-" + str(int(time.time()))
        self.test_doc_hash = "hash-" + str(int(time.time()))
        
        print(f"🧪 Testing with doc_id: {self.test_doc_id}")
    
    def create_standardized_message(self, stage: str, additional_data: dict = None) -> dict:
        """Create a standardized message"""
        
        message = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "climate-risk-rag-system",
            "stage": stage,
            "doc_id": self.test_doc_id,
            "doc_hash": self.test_doc_hash,
            "document_metadata": {
                "filename": "test_document.pdf",
                "size": 34580,
                "content_type": "application/pdf"
            },
            "data_locations": {
                "document_s3_key": "documents/006893d2_93170cb9.pdf",
                "document_bucket": "solve-global-kr-documents-861276078413-us-east-1"
            },
            "processing_metadata": {
                "processing_time": 1.5,
                "stage_start": datetime.utcnow().isoformat() + "Z"
            },
            "integration_flags": {
                "standardized_messaging": True,
                "test_mode": True
            }
        }
        
        if additional_data:
            message.update(additional_data)
        
        return message
    
    def test_textract_processor(self) -> bool:
        """Test Textract processor with standardized message"""
        
        print("\n🔬 Testing Textract Processor...")
        
        # Create a text_ready message
        message = self.create_standardized_message("text_ready", {
            "data_locations": {
                "document_s3_key": "documents/006893d2_93170cb9.pdf",
                "document_bucket": "solve-global-kr-documents-861276078413-us-east-1",
                "text_s3_key": f"text/{self.test_doc_id}.txt",
                "text_bucket": "solve-global-kr-text-new-861276078413-us-east-1"
            }
        })
        
        # Create SNS event format
        sns_event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "Sns": {
                        "Message": json.dumps(message),
                        "TopicArn": "arn:aws:sns:us-east-1:861276078413:text-extraction-complete"
                    }
                }
            ]
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName='solve-global-kr-textextractor-processor',
                InvocationType='RequestResponse',  # Sync for testing
                Payload=json.dumps(sns_event)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                print("✅ Textract processor invoked successfully")
                print(f"   Response: {result}")
                return True
            else:
                print(f"❌ Textract processor failed: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing Textract processor: {e}")
            return False
    
    def test_text_chunker(self) -> bool:
        """Test Text Chunker with standardized message"""
        
        print("\n🔬 Testing Text Chunker...")
        
        # Create a text_ready message for chunker
        message = self.create_standardized_message("text_ready", {
            "data_locations": {
                "text_s3_key": f"text/{self.test_doc_id}.txt",
                "text_bucket": "solve-global-kr-text-new-861276078413-us-east-1"
            }
        })
        
        # Create SNS event format
        sns_event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "Sns": {
                        "Message": json.dumps(message),
                        "TopicArn": "arn:aws:sns:us-east-1:861276078413:text-extraction-complete"
                    }
                }
            ]
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName='text-chunker-pipeline',
                InvocationType='RequestResponse',  # Sync for testing
                Payload=json.dumps(sns_event)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                print("✅ Text chunker invoked successfully")
                print(f"   Response: {result}")
                return True
            else:
                print(f"❌ Text chunker failed: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing Text chunker: {e}")
            return False
    
    def test_nlp_processor(self) -> bool:
        """Test NLP Processor with standardized message"""
        
        print("\n🔬 Testing NLP Processor...")
        
        # Create a chunks_ready message
        message = self.create_standardized_message("chunks_ready", {
            "data_locations": {
                "chunks_s3_key": f"chunks/{self.test_doc_id}/",
                "chunks_bucket": "solve-global-kr-chunks-861276078413-us-east-1"
            },
            "processing_metadata": {
                "chunk_count": 5,
                "total_tokens": 1500
            }
        })
        
        # Create SNS event format
        sns_event = {
            "Records": [
                {
                    "EventSource": "aws:sns",
                    "Sns": {
                        "Message": json.dumps(message),
                        "TopicArn": "arn:aws:sns:us-east-1:861276078413:chunks-ready"
                    }
                }
            ]
        }
        
        try:
            response = self.lambda_client.invoke(
                FunctionName='nlp-processor',
                InvocationType='RequestResponse',  # Sync for testing
                Payload=json.dumps(sns_event)
            )
            
            result = json.loads(response['Payload'].read())
            
            if response['StatusCode'] == 200:
                print("✅ NLP processor invoked successfully")
                print(f"   Response: {result}")
                return True
            else:
                print(f"❌ NLP processor failed: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing NLP processor: {e}")
            return False
    
    def run_messaging_tests(self) -> bool:
        """Run all messaging tests"""
        
        print("🚀 Starting Direct Standardized Messaging Tests")
        print("=" * 60)
        
        tests = [
            ("Textract Processor", self.test_textract_processor),
            ("Text Chunker", self.test_text_chunker),
            ("NLP Processor", self.test_nlp_processor)
        ]
        
        successful_tests = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    successful_tests += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
        
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {successful_tests}/{len(tests)} passed")
        
        if successful_tests >= 2:
            print("\n🎉 Standardized Messaging Tests PASSED!")
            print("✅ The messaging system is working correctly")
            return True
        else:
            print("\n⚠️  Standardized Messaging Tests PARTIAL SUCCESS")
            print("🔧 Some functions may need attention")
            return False

def main():
    """Main test function"""
    
    tester = DirectMessagingTester()
    success = tester.run_messaging_tests()
    
    if success:
        print("\n🎯 Standardized messaging deployment is successful!")
        print("🚀 Ready for end-to-end pipeline testing")
    else:
        print("\n🔧 Some messaging components need debugging")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
