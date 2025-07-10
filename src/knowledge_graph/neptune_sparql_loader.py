#!/usr/bin/env python3
"""
Neptune SPARQL Loader
Alternative to bulk loading - uses SPARQL INSERT to load TTL data
"""

import json
import urllib3
import boto3
from datetime import datetime
import re

def lambda_handler(event, context):
    """Load TTL data using SPARQL INSERT operations"""
    
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    sparql_endpoint = f"https://{neptune_endpoint}:8182/sparql"
    
    ttl_bucket = "solve-global-kr-neptune-ttl-861276078413-us-east-1"
    
    doc_id = event.get('doc_id', '0032f6cb_f0caef34')
    load_type = event.get('load_type', 'document')  # 'schema' or 'document'
    
    http = urllib3.PoolManager()
    s3 = boto3.client('s3', region_name='us-east-1')
    
    result = {
        'doc_id': doc_id,
        'load_type': load_type,
        'timestamp': datetime.now().isoformat(),
        'operations': []
    }
    
    try:
        # Determine which TTL files to load
        if load_type == 'schema':
            ttl_files = ['ontology/document_structure_schema.ttl']
        else:
            ttl_files = [
                f'documents/{doc_id}/document.ttl',
                f'documents/{doc_id}/chunks.ttl'
            ]
        
        # Load each TTL file
        for ttl_file in ttl_files:
            operation_result = load_ttl_file_via_sparql(
                s3, http, ttl_bucket, ttl_file, sparql_endpoint
            )
            result['operations'].append(operation_result)
        
        # Calculate success
        successful_ops = sum(1 for op in result['operations'] if op.get('success', False))
        result['summary'] = {
            'successful_operations': successful_ops,
            'total_operations': len(result['operations']),
            'overall_success': successful_ops == len(result['operations'])
        }
        
        # Test loaded data
        if result['summary']['overall_success']:
            validation_result = validate_loaded_data(http, sparql_endpoint)
            result['validation'] = validation_result
        
    except Exception as e:
        result['error'] = str(e)
        result['summary'] = {'overall_success': False}
    
    return {
        'statusCode': 200 if result['summary']['overall_success'] else 500,
        'body': json.dumps(result, indent=2)
    }

def load_ttl_file_via_sparql(s3, http, bucket, key, sparql_endpoint):
    """Load a single TTL file using SPARQL INSERT"""
    
    operation = {
        'file': key,
        'started_at': datetime.now().isoformat()
    }
    
    try:
        # Download TTL file from S3
        response = s3.get_object(Bucket=bucket, Key=key)
        ttl_content = response['Body'].read().decode('utf-8')
        
        operation['file_size'] = len(ttl_content)
        
        # Convert TTL to SPARQL INSERT statements
        insert_statements = convert_ttl_to_sparql_insert(ttl_content)
        operation['insert_statements'] = len(insert_statements)
        
        # Execute each INSERT statement
        successful_inserts = 0
        failed_inserts = 0
        
        for i, insert_query in enumerate(insert_statements):
            try:
                response = http.request(
                    'POST',
                    sparql_endpoint,
                    body=insert_query,
                    headers={'Content-Type': 'application/sparql-update'},
                    timeout=60
                )
                
                if response.status == 200:
                    successful_inserts += 1
                else:
                    failed_inserts += 1
                    if failed_inserts == 1:  # Log first failure
                        operation['first_failure'] = {
                            'statement_index': i,
                            'status_code': response.status,
                            'response': response.data.decode('utf-8')[:200]
                        }
                        
            except Exception as e:
                failed_inserts += 1
                if failed_inserts == 1:  # Log first failure
                    operation['first_failure'] = {
                        'statement_index': i,
                        'error': str(e)
                    }
        
        operation.update({
            'success': failed_inserts == 0,
            'successful_inserts': successful_inserts,
            'failed_inserts': failed_inserts,
            'completed_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        operation.update({
            'success': False,
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })
    
    return operation

def convert_ttl_to_sparql_insert(ttl_content):
    """Convert TTL content to SPARQL INSERT statements"""
    
    # Extract prefixes
    prefix_lines = []
    data_lines = []
    
    for line in ttl_content.split('\n'):
        line = line.strip()
        if line.startswith('@prefix'):
            prefix_lines.append(line)
        elif line and not line.startswith('#'):
            data_lines.append(line)
    
    # Combine prefixes
    prefixes = '\n'.join(prefix_lines)
    
    # Split into individual triple blocks (subjects)
    ttl_data = '\n'.join(data_lines)
    
    # Simple approach: split by lines ending with ' .'
    # This is a basic parser - for production, use a proper TTL parser
    triple_blocks = []
    current_block = []
    
    for line in ttl_data.split('\n'):
        line = line.strip()
        if line:
            current_block.append(line)
            if line.endswith(' .'):
                if current_block:
                    triple_blocks.append('\n'.join(current_block))
                    current_block = []
    
    # Convert each block to INSERT statement
    insert_statements = []
    
    for block in triple_blocks:
        if block.strip():
            # Create INSERT DATA statement
            insert_query = f"""
{prefixes}

INSERT DATA {{
{block}
}}
"""
            insert_statements.append(insert_query)
    
    return insert_statements

def validate_loaded_data(http, sparql_endpoint):
    """Validate that data was loaded correctly"""
    
    validation = {
        'tests': {},
        'timestamp': datetime.now().isoformat()
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
            validation['tests']['triple_count'] = {
                'success': True,
                'count': count,
                'valid': count > 0
            }
        else:
            validation['tests']['triple_count'] = {
                'success': False,
                'status_code': response.status
            }
            
    except Exception as e:
        validation['tests']['triple_count'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 2: Check for documents
    try:
        doc_query = """
        PREFIX kr: <http://solve.global/knowledge-commons/schema#>
        SELECT (COUNT(?doc) as ?docCount) WHERE {
            ?doc a kr:Document .
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
            validation['tests']['document_count'] = {
                'success': True,
                'count': doc_count,
                'valid': doc_count > 0
            }
        else:
            validation['tests']['document_count'] = {
                'success': False,
                'status_code': response.status
            }
            
    except Exception as e:
        validation['tests']['document_count'] = {
            'success': False,
            'error': str(e)
        }
    
    # Test 3: Check for chunks
    try:
        chunk_query = """
        PREFIX kr: <http://solve.global/knowledge-commons/schema#>
        SELECT (COUNT(?chunk) as ?chunkCount) WHERE {
            ?chunk a kr:DocumentChunk .
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
            validation['tests']['chunk_count'] = {
                'success': True,
                'count': chunk_count,
                'valid': chunk_count > 0
            }
        else:
            validation['tests']['chunk_count'] = {
                'success': False,
                'status_code': response.status
            }
            
    except Exception as e:
        validation['tests']['chunk_count'] = {
            'success': False,
            'error': str(e)
        }
    
    # Calculate overall validation success
    successful_tests = sum(1 for test in validation['tests'].values() 
                          if test.get('success', False) and test.get('valid', False))
    total_tests = len(validation['tests'])
    
    validation['summary'] = {
        'successful_tests': successful_tests,
        'total_tests': total_tests,
        'overall_success': successful_tests == total_tests
    }
    
    return validation

# For testing locally
if __name__ == "__main__":
    test_event = {
        'doc_id': '0032f6cb_f0caef34',
        'load_type': 'document'
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "neptune-sparql-loader"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
