#!/usr/bin/env python3
"""
Neptune SPARQL Loader - FIXED VERSION
Load TTL data using SPARQL INSERT operations, without textContent triples
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
        
        # Remove textContent triples to avoid UTF-8 issues
        cleaned_ttl = remove_text_content_triples(ttl_content)
        operation['cleaned_size'] = len(cleaned_ttl)
        
        # Convert TTL to SPARQL INSERT statements
        insert_statements = convert_ttl_to_sparql_insert(cleaned_ttl)
        operation['insert_statements'] = len(insert_statements)
        
        # Execute each INSERT statement
        successful_inserts = 0
        failed_inserts = 0
        
        for i, insert_query in enumerate(insert_statements):
            try:
                response = http.request(
                    'POST',
                    sparql_endpoint,
                    body=insert_query.encode('utf-8'),
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
                            'response': response.data.decode('utf-8')[:300]
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

def remove_text_content_triples(ttl_content):
    """Remove kr:textContent triples to avoid UTF-8 encoding issues"""
    
    lines = ttl_content.split('\n')
    cleaned_lines = []
    skip_next_lines = False
    
    for line in lines:
        # Check if this line contains textContent
        if 'kr:textContent' in line:
            # Skip this line and any continuation lines
            skip_next_lines = True
            continue
        
        # If we're skipping continuation lines
        if skip_next_lines:
            # Check if this line ends a triple (ends with ; or .)
            stripped = line.strip()
            if stripped.endswith(';') or stripped.endswith('.'):
                skip_next_lines = False
            continue
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def convert_ttl_to_sparql_insert(ttl_content):
    """Convert TTL content to SPARQL INSERT statements"""
    
    # Split into prefix section and data section
    lines = ttl_content.split('\n')
    prefix_lines = []
    data_lines = []
    in_data_section = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('@prefix'):
            prefix_lines.append(line)
        elif stripped.startswith('#') and 'DOCUMENT' in stripped:
            in_data_section = True
            data_lines.append(line)  # Keep comment
        elif in_data_section and stripped:
            data_lines.append(line)
    
    # Combine prefixes
    prefixes = '\n'.join(prefix_lines)
    
    # Process data section to create individual INSERT statements
    data_content = '\n'.join(data_lines)
    
    # Split by subject (lines that don't start with whitespace and contain a URI or prefix)
    subjects = []
    current_subject = []
    
    for line in data_lines:
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            if current_subject:
                current_subject.append(line)
            continue
        
        # Check if this starts a new subject (doesn't start with whitespace)
        if not line.startswith(' ') and not line.startswith('\t') and ('sg:' in line or '<http' in line):
            # Save previous subject
            if current_subject:
                subjects.append('\n'.join(current_subject))
                current_subject = []
            
            # Start new subject
            current_subject = [line]
        else:
            # Continuation of current subject
            if current_subject:
                current_subject.append(line)
    
    # Don't forget the last subject
    if current_subject:
        subjects.append('\n'.join(current_subject))
    
    # Create INSERT statements
    insert_statements = []
    
    for subject_block in subjects:
        if subject_block.strip():
            # Clean up the subject block
            cleaned_block = subject_block.strip()
            
            # Make sure it ends with a period
            if not cleaned_block.endswith('.'):
                cleaned_block += ' .'
            
            # Create INSERT DATA statement
            insert_query = f"""{prefixes}

INSERT DATA {{
{cleaned_block}
}}"""
            
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
            self.function_name = "neptune-sparql-loader-fixed"
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
