#!/usr/bin/env python3
"""
Test script for Lambda functions
Tests the core functionality without deploying to AWS
"""

import json
import sys
import os
from unittest.mock import Mock, patch

# Add lambda directories to path
sys.path.append('lambda/document_processor')
sys.path.append('lambda/query_handler')
sys.path.append('lambda/kg_manager')
sys.path.append('lambda/bulk_processor')

def test_document_processor():
    """Test document processor Lambda"""
    print("🔍 Testing Document Processor...")
    
    # Mock environment variables
    with patch.dict(os.environ, {
        'OPENSEARCH_ENDPOINT': 'test-endpoint',
        'DOCUMENTS_BUCKET': 'test-docs-bucket',
        'ARTIFACTS_BUCKET': 'test-artifacts-bucket',
        'AWS_REGION': 'us-east-1'
    }):
        # Mock AWS clients
        with patch('boto3.client') as mock_boto3:
            mock_textract = Mock()
            mock_comprehend = Mock()
            mock_bedrock = Mock()
            mock_s3 = Mock()
            
            # Configure mocks
            mock_boto3.side_effect = lambda service: {
                'textract': mock_textract,
                'comprehend': mock_comprehend,
                'bedrock-runtime': mock_bedrock,
                's3': mock_s3,
                'opensearchserverless': Mock()
            }[service]
            
            # Mock Textract response
            mock_textract.detect_document_text.return_value = {
                'Blocks': [
                    {'BlockType': 'LINE', 'Text': 'Climate change poses significant risks'},
                    {'BlockType': 'LINE', 'Text': 'Carbon emissions must be reduced'}
                ]
            }
            
            # Mock Comprehend response
            mock_comprehend.detect_entities.return_value = {
                'Entities': [
                    {'Text': 'Climate change', 'Type': 'OTHER', 'Score': 0.95},
                    {'Text': 'Carbon emissions', 'Type': 'OTHER', 'Score': 0.90}
                ]
            }
            
            # Mock Bedrock response
            mock_bedrock.invoke_model.return_value = {
                'body': Mock(read=lambda: json.dumps({'embedding': [0.1] * 1536}).encode())
            }
            
            # Mock S3 response
            mock_s3.get_object.return_value = {
                'Body': Mock(read=lambda: b'Climate change is a critical issue.')
            }
            
            # Import and test
            from document_processor import handler
            
            test_event = {
                'action': 'extract_text',
                'bucket': 'test-bucket',
                'key': 'test-document.txt'
            }
            
            result = handler(test_event, {})
            
            assert result['statusCode'] == 200
            print("✅ Document Processor test passed")

def test_query_handler():
    """Test query handler Lambda"""
    print("🔍 Testing Query Handler...")
    
    with patch.dict(os.environ, {
        'OPENSEARCH_ENDPOINT': 'test-endpoint',
        'NEPTUNE_ENDPOINT': 'test-neptune',
        'DOCUMENTS_BUCKET': 'test-docs-bucket',
        'ARTIFACTS_BUCKET': 'test-artifacts-bucket',
        'AWS_REGION': 'us-east-1'
    }):
        with patch('boto3.client') as mock_boto3:
            mock_comprehend = Mock()
            mock_bedrock = Mock()
            mock_s3 = Mock()
            
            mock_boto3.side_effect = lambda service: {
                'comprehend': mock_comprehend,
                'bedrock-runtime': mock_bedrock,
                's3': mock_s3
            }[service]
            
            # Mock Comprehend response
            mock_comprehend.detect_entities.return_value = {
                'Entities': [{'Text': 'climate risk', 'Type': 'OTHER', 'Score': 0.95}]
            }
            mock_comprehend.detect_key_phrases.return_value = {
                'KeyPhrases': [{'Text': 'climate risk assessment', 'Score': 0.90}]
            }
            mock_comprehend.detect_sentiment.return_value = {
                'Sentiment': 'NEUTRAL',
                'SentimentScore': {'Neutral': 0.8}
            }
            
            # Mock Bedrock responses
            mock_bedrock.invoke_model.side_effect = [
                # Embedding response
                {'body': Mock(read=lambda: json.dumps({'embedding': [0.1] * 1536}).encode())},
                # LLM response
                {'body': Mock(read=lambda: json.dumps({
                    'content': [{'text': 'Climate risk refers to potential negative impacts...'}],
                    'usage': {'output_tokens': 50}
                }).encode())}
            ]
            
            # Mock S3 list response
            mock_s3.list_objects_v2.return_value = {'Contents': []}
            
            from query_handler import handler
            
            test_event = {
                'body': json.dumps({'query': 'What are the main climate risks?'})
            }
            
            result = handler(test_event, {})
            
            assert result['statusCode'] == 200
            print("✅ Query Handler test passed")

def test_kg_manager():
    """Test knowledge graph manager Lambda"""
    print("🔍 Testing Knowledge Graph Manager...")
    
    with patch.dict(os.environ, {
        'NEPTUNE_ENDPOINT': 'test-neptune',
        'ARTIFACTS_BUCKET': 'test-artifacts-bucket',
        'AWS_REGION': 'us-east-1'
    }):
        with patch('boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_boto3.return_value = mock_s3
            
            from kg_manager import handler
            
            test_event = {
                'action': 'update_graph',
                'entities': [
                    {'Text': 'Climate change', 'Type': 'OTHER', 'Score': 0.95}
                ],
                'document_id': 'test-doc-123'
            }
            
            result = handler(test_event, {})
            
            assert result['statusCode'] == 200
            print("✅ Knowledge Graph Manager test passed")

def test_bulk_processor():
    """Test bulk processor Lambda"""
    print("🔍 Testing Bulk Processor...")
    
    with patch.dict(os.environ, {
        'DOCUMENTS_BUCKET': 'test-docs-bucket',
        'ARTIFACTS_BUCKET': 'test-artifacts-bucket',
        'AWS_REGION': 'us-east-1'
    }):
        with patch('boto3.client') as mock_boto3:
            mock_s3 = Mock()
            mock_stepfunctions = Mock()
            mock_lambda = Mock()
            
            mock_boto3.side_effect = lambda service: {
                's3': mock_s3,
                'stepfunctions': mock_stepfunctions,
                'lambda': mock_lambda
            }[service]
            
            # Mock S3 responses
            mock_s3.get_paginator.return_value.paginate.return_value = [
                {'Contents': [{'Key': 'test.pdf', 'Size': 1000, 'LastModified': '2024-01-01'}]}
            ]
            mock_s3.head_object.side_effect = Exception("Not found")  # Simulate unprocessed
            
            from bulk_processor import handler
            
            test_event = {
                'action': 'health_check'
            }
            
            result = handler(test_event, {})
            
            assert result['statusCode'] == 200
            print("✅ Bulk Processor test passed")

def main():
    """Run all tests"""
    print("🧪 Testing Lambda Functions")
    print("=" * 40)
    
    try:
        test_document_processor()
        test_query_handler()
        test_kg_manager()
        test_bulk_processor()
        
        print("\n🎉 All tests passed!")
        print("\n📋 Next steps:")
        print("1. Deploy infrastructure: ./deploy.sh")
        print("2. Enable Bedrock models in AWS Console")
        print("3. Upload test documents to S3")
        print("4. Test the deployed system")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
