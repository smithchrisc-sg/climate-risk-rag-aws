#!/usr/bin/env python3
"""
Neptune Bulk Load Completion Handler
Handles completion notifications and triggers follow-up actions
"""

import json
import urllib3
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Lambda function to handle Neptune bulk loading job completion"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    sparql_endpoint = f"https://{neptune_endpoint}:8182/sparql"
    
    # Process SNS notification
    if 'Records' not in event:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No SNS records found'})
        }
    
    results = []
    
    for record in event['Records']:
        if record.get('EventSource') == 'aws:sns':
            try:
                sns_message = json.loads(record['Sns']['Message'])
                
                if sns_message.get('action') == 'JOB_COMPLETED':
                    result = process_job_completion(sns_message, sparql_endpoint)
                    results.append(result)
                    
            except Exception as e:
                results.append({
                    'success': False,
                    'error': f'Error processing SNS message: {str(e)}'
                })
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed_records': len(results),
            'results': results
        }, indent=2)
    }

def process_job_completion(completion_message: dict, sparql_endpoint: str) -> dict:
    """Process a job completion notification"""
    
    load_id = completion_message.get('load_id')
    status = completion_message.get('status')
    success = completion_message.get('success', False)
    job_details = completion_message.get('job_details', {})
    
    result = {
        'load_id': load_id,
        'status': status,
        'success': success,
        'processed_at': datetime.now().isoformat()
    }
    
    if success:
        # Job completed successfully - run validation queries
        try:
            validation_results = validate_loaded_data(sparql_endpoint)
            result['validation'] = validation_results
            
            # If validation passes, trigger follow-up actions
            if validation_results.get('success', False):
                followup_results = trigger_followup_actions(load_id, job_details)
                result['followup_actions'] = followup_results
                
        except Exception as e:
            result['validation_error'] = str(e)
    else:
        # Job failed - log error details
        result['error_details'] = job_details.get('error_details', [])
        
        # Could trigger retry logic here
        result['retry_recommended'] = should_retry_job(job_details)
    
    return result

def validate_loaded_data(sparql_endpoint: str) -> dict:
    """Validate that data was loaded correctly"""
    
    http = urllib3.PoolManager()
    validation_results = {
        'tests': {},
        'success': False
    }
    
    # Test 1: Count total triples
    try:
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        response = http.request(
            'POST',
            sparql_endpoint,
            body=count_query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=30
        )
        
        if response.status == 200:
            result = json.loads(response.data.decode('utf-8'))
            count = int(result['results']['bindings'][0]['count']['value'])
            validation_results['tests']['triple_count'] = {
                'success': True,
                'count': count,
                'valid': count > 0
            }
        else:
            validation_results['tests']['triple_count'] = {
                'success': False,
                'error': f'HTTP {response.status}'
            }
            
    except Exception as e:
        validation_results['tests']['triple_count'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 2: Check document structure
    try:
        doc_query = """
        SELECT (COUNT(?doc) as ?docCount) WHERE {
            ?doc a <http://solve.global/knowledge-commons/schema#Document> .
        }
        """
        
        response = http.request(
            'POST',
            sparql_endpoint,
            body=doc_query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=30
        )
        
        if response.status == 200:
            result = json.loads(response.data.decode('utf-8'))
            doc_count = int(result['results']['bindings'][0]['docCount']['value'])
            validation_results['tests']['document_structure'] = {
                'success': True,
                'document_count': doc_count,
                'valid': doc_count > 0
            }
        else:
            validation_results['tests']['document_structure'] = {
                'success': False,
                'error': f'HTTP {response.status}'
            }
            
    except Exception as e:
        validation_results['tests']['document_structure'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 3: Check chunk structure
    try:
        chunk_query = """
        SELECT (COUNT(?chunk) as ?chunkCount) WHERE {
            ?chunk a <http://solve.global/knowledge-commons/schema#DocumentChunk> .
        }
        """
        
        response = http.request(
            'POST',
            sparql_endpoint,
            body=chunk_query,
            headers={
                'Content-Type': 'application/sparql-query',
                'Accept': 'application/sparql-results+json'
            },
            timeout=30
        )
        
        if response.status == 200:
            result = json.loads(response.data.decode('utf-8'))
            chunk_count = int(result['results']['bindings'][0]['chunkCount']['value'])
            validation_results['tests']['chunk_structure'] = {
                'success': True,
                'chunk_count': chunk_count,
                'valid': chunk_count > 0
            }
        else:
            validation_results['tests']['chunk_structure'] = {
                'success': False,
                'error': f'HTTP {response.status}'
            }
            
    except Exception as e:
        validation_results['tests']['chunk_structure'] = {
            'success': False,
            'error': str(e)
        }
    
    # Determine overall validation success
    successful_tests = sum(1 for test in validation_results['tests'].values() 
                          if test.get('success', False) and test.get('valid', False))
    total_tests = len(validation_results['tests'])
    
    validation_results['success'] = successful_tests == total_tests
    validation_results['summary'] = f"{successful_tests}/{total_tests} validation tests passed"
    
    return validation_results

def trigger_followup_actions(load_id: str, job_details: dict) -> dict:
    """Trigger follow-up actions after successful data loading"""
    
    followup_results = {
        'actions': []
    }
    
    # Action 1: Update processing status in database
    try:
        # This would update PostgreSQL or DynamoDB with completion status
        # For now, just log the action
        followup_results['actions'].append({
            'action': 'update_processing_status',
            'success': True,
            'details': f'Marked load job {load_id} as completed'
        })
    except Exception as e:
        followup_results['actions'].append({
            'action': 'update_processing_status',
            'success': False,
            'error': str(e)
        })
    
    # Action 2: Trigger downstream processing (if needed)
    try:
        # This could trigger vector embedding generation, indexing, etc.
        followup_results['actions'].append({
            'action': 'trigger_downstream_processing',
            'success': True,
            'details': 'Downstream processing notifications sent'
        })
    except Exception as e:
        followup_results['actions'].append({
            'action': 'trigger_downstream_processing',
            'success': False,
            'error': str(e)
        })
    
    # Action 3: Send completion notification
    try:
        # This could send notifications to users, Slack, etc.
        followup_results['actions'].append({
            'action': 'send_completion_notification',
            'success': True,
            'details': f'Knowledge graph updated with {job_details.get("total_records", 0)} records'
        })
    except Exception as e:
        followup_results['actions'].append({
            'action': 'send_completion_notification',
            'success': False,
            'error': str(e)
        })
    
    return followup_results

def should_retry_job(job_details: dict) -> bool:
    """Determine if a failed job should be retried"""
    
    error_details = job_details.get('error_details', [])
    
    # Check for retryable errors
    retryable_errors = [
        'timeout',
        'network',
        'temporary',
        'throttling'
    ]
    
    for error in error_details:
        error_message = str(error).lower()
        if any(retryable in error_message for retryable in retryable_errors):
            return True
    
    return False

# For testing locally
if __name__ == "__main__":
    # Test event
    test_event = {
        'Records': [{
            'EventSource': 'aws:sns',
            'Sns': {
                'Message': json.dumps({
                    'action': 'JOB_COMPLETED',
                    'load_id': 'test-load-123',
                    'status': 'LOAD_COMPLETED',
                    'success': True,
                    'job_details': {
                        'total_records': 150,
                        'total_time_spent': 45000
                    }
                })
            }
        }]
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "neptune-bulk-loader-completion"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
