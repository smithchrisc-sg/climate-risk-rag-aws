#!/usr/bin/env python3
"""
Test script for Climate Risk RAG Cleanup Service
Tests the cleanup service with various payload configurations
"""

import json
import boto3
import time
from typing import Dict, Any

def test_cleanup_service():
    """Test the cleanup service with different configurations"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    function_name = 'solve-global-kr-cleanup-service'
    
    print("🧹 Testing Climate Risk RAG Cleanup Service")
    print("=" * 50)
    
    # Test 1: Dry run full cleanup
    print("\n📋 Test 1: Dry Run Full Cleanup")
    print("-" * 30)
    
    dry_run_payload = {
        "cleanup_scope": {
            "databases": {
                "postgresql": {
                    "enabled": True,
                    "tables": ["document_processing_status", "nlp_processing_status"],
                    "document_ids": []
                },
                "opensearch": {
                    "enabled": True,
                    "collections": ["climate-risk-vectorsearch", "climate-risk-keyword-index"],
                    "document_ids": []
                },
                "neptune": {
                    "enabled": True,
                    "clear_all_triples": False,
                    "document_ids": []
                }
            },
            "s3_data_lake": {
                "enabled": True,
                "buckets": ["solve-global-kr-dl-*"],
                "document_ids": [],
                "preserve_structure": True
            }
        },
        "safety_checks": {
            "require_confirmation": False,
            "dry_run": True,
            "max_documents_to_delete": 1000
        }
    }
    
    result1 = invoke_cleanup_service(lambda_client, function_name, dry_run_payload)
    print_test_result("Dry Run Full Cleanup", result1)
    
    # Test 2: S3 only cleanup (dry run)
    print("\n📋 Test 2: S3 Only Cleanup (Dry Run)")
    print("-" * 30)
    
    s3_only_payload = {
        "cleanup_scope": {
            "databases": {
                "postgresql": {"enabled": False},
                "opensearch": {"enabled": False},
                "neptune": {"enabled": False}
            },
            "s3_data_lake": {
                "enabled": True,
                "buckets": ["solve-global-kr-dl-source-documents-*"],
                "document_ids": [],
                "preserve_structure": True
            }
        },
        "safety_checks": {
            "require_confirmation": False,
            "dry_run": True,
            "max_documents_to_delete": 100
        }
    }
    
    result2 = invoke_cleanup_service(lambda_client, function_name, s3_only_payload)
    print_test_result("S3 Only Cleanup", result2)
    
    # Test 3: Invalid payload (should fail validation)
    print("\n📋 Test 3: Invalid Payload (Should Fail)")
    print("-" * 30)
    
    invalid_payload = {
        "cleanup_scope": {
            "databases": {
                "postgresql": {
                    "enabled": "not_a_boolean",  # Invalid type
                    "tables": "not_a_list"       # Invalid type
                }
            }
        },
        "safety_checks": {
            "dry_run": "not_a_boolean"  # Invalid type
        }
    }
    
    result3 = invoke_cleanup_service(lambda_client, function_name, invalid_payload)
    print_test_result("Invalid Payload", result3, expect_failure=True)
    
    # Test 4: Status check (minimal payload)
    print("\n📋 Test 4: Minimal Status Check")
    print("-" * 30)
    
    minimal_payload = {
        "cleanup_scope": {
            "databases": {
                "postgresql": {"enabled": False},
                "opensearch": {"enabled": False},
                "neptune": {"enabled": False}
            },
            "s3_data_lake": {"enabled": False}
        },
        "safety_checks": {
            "dry_run": True,
            "require_confirmation": False
        }
    }
    
    result4 = invoke_cleanup_service(lambda_client, function_name, minimal_payload)
    print_test_result("Minimal Status Check", result4)
    
    print("\n" + "=" * 50)
    print("🏁 Cleanup Service Testing Complete")

def invoke_cleanup_service(lambda_client, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke the cleanup service with given payload"""
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        return {
            'success': True,
            'status_code': response.get('StatusCode', 200),
            'response': response_payload
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'response': None
        }

def print_test_result(test_name: str, result: Dict[str, Any], expect_failure: bool = False):
    """Print formatted test result"""
    if result['success']:
        response_body = result['response'].get('body', {})
        if isinstance(response_body, str):
            try:
                response_body = json.loads(response_body)
            except:
                pass
        
        success = response_body.get('success', False) if isinstance(response_body, dict) else False
        
        if success and not expect_failure:
            print(f"✅ {test_name}: PASSED")
            if isinstance(response_body, dict) and 'results' in response_body:
                summary = response_body['results'].get('summary', {})
                print(f"   Operations: {summary.get('total_operations', 0)}")
                print(f"   Successful: {summary.get('successful_operations', 0)}")
                print(f"   Failed: {summary.get('failed_operations', 0)}")
        elif not success and expect_failure:
            print(f"✅ {test_name}: PASSED (Expected failure)")
            if isinstance(response_body, dict) and 'error' in response_body:
                print(f"   Error: {response_body['error']}")
        else:
            print(f"❌ {test_name}: UNEXPECTED RESULT")
            print(f"   Expected failure: {expect_failure}")
            print(f"   Actual success: {success}")
            if isinstance(response_body, dict) and 'error' in response_body:
                print(f"   Error: {response_body['error']}")
    else:
        if expect_failure:
            print(f"✅ {test_name}: PASSED (Expected failure)")
        else:
            print(f"❌ {test_name}: FAILED")
        print(f"   Error: {result['error']}")

if __name__ == "__main__":
    test_cleanup_service()
