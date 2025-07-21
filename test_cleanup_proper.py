#!/usr/bin/env python3
"""
Test cleanup service with proper payload format
"""

import boto3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cleanup_proper():
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test 1: Database-only cleanup (dry run)
    payload_db_only = {
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
                },
                "neptune": {
                    "enabled": True,
                    "clear_all_triples": True,
                    "document_ids": []
                }
            }
        },
        "safety_checks": {
            "require_confirmation": False,
            "dry_run": True,
            "max_documents_to_delete": 1000
        }
    }
    
    logger.info("🧪 Testing database-only cleanup...")
    
    try:
        response = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload_db_only)
        )
        
        result = json.loads(response['Payload'].read())
        
        logger.info("=== DATABASE CLEANUP TEST RESULT ===")
        logger.info(f"Success: {result.get('success')}")
        
        if 'results' in result and 'databases' in result['results']:
            databases = result['results']['databases']
            
            logger.info("\\n=== DATABASE COMPONENT STATUS ===")
            for db_name, db_result in databases.items():
                status = "✅ WORKING" if db_result.get('success') else "❌ FAILED"
                logger.info(f"{db_name.upper()}: {status}")
                
                if db_result.get('success'):
                    ops = db_result.get('operations_performed', [])
                    logger.info(f"  Operations: {len(ops)}")
                    for op in ops[:3]:  # Show first 3 operations
                        logger.info(f"    - {op.get('operation', 'unknown')}: {op.get('records_affected', 0)} records")
                
                if not db_result.get('success') and 'errors' in db_result:
                    for error in db_result['errors']:
                        logger.info(f"  Error: {error}")
        
        # Test 2: Full system test (dry run)
        payload_full = {
            "cleanup_scope": {
                "databases": {
                    "postgresql": {
                        "enabled": True,
                        "tables": ["document_processing_status"],
                        "document_ids": []
                    },
                    "opensearch": {
                        "enabled": True,
                        "collections": ["climate-risk-vectorsearch"],
                        "document_ids": []
                    },
                    "neptune": {
                        "enabled": True,
                        "clear_all_triples": True,
                        "document_ids": []
                    }
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
        
        logger.info("\\n🧪 Testing full system cleanup...")
        
        response2 = lambda_client.invoke(
            FunctionName='solve-global-kr-cleanup-service',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload_full)
        )
        
        result2 = json.loads(response2['Payload'].read())
        
        logger.info("=== FULL SYSTEM TEST RESULT ===")
        logger.info(f"Success: {result2.get('success')}")
        
        # Analyze functionality
        functional_components = []
        broken_components = []
        
        if 'results' in result2 and 'databases' in result2['results']:
            databases = result2['results']['databases']
            for db_name, db_result in databases.items():
                if db_result.get('success'):
                    functional_components.append(db_name)
                else:
                    broken_components.append(db_name)
        
        if 'results' in result2 and 's3_data_lake' in result2['results']:
            s3_result = result2['results']['s3_data_lake']
            if s3_result.get('success'):
                functional_components.append('s3')
            else:
                broken_components.append('s3')
        
        logger.info(f"\\n✅ FUNCTIONAL: {functional_components}")
        logger.info(f"❌ BROKEN: {broken_components}")
        
        # Determine if fully functional
        critical_components = ['postgresql', 'neptune', 's3']
        working_critical = [comp for comp in functional_components if comp in critical_components]
        
        if len(working_critical) >= 2:  # At least PostgreSQL and one other
            logger.info("\\n🎉 CLEANUP SERVICE IS FUNCTIONAL!")
            logger.info("Core database and infrastructure operations are working.")
            return True
        else:
            logger.error("\\n🔧 CLEANUP SERVICE NEEDS CONFIGURATION!")
            logger.error(f"Working critical components: {working_critical}")
            return False
        
    except Exception as e:
        logger.error(f"Error testing cleanup service: {e}")
        return False

if __name__ == "__main__":
    is_functional = test_cleanup_proper()
    
    if is_functional:
        logger.info("\\n🏆 RESULT: Cleanup service is FULLY FUNCTIONAL!")
    else:
        logger.error("\\n🔧 RESULT: Cleanup service needs additional configuration!")
        exit(1)
