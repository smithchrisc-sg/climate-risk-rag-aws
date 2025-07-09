#!/usr/bin/env python3
"""
Deploy Updated Vector Embeddings Functions with Standardized Messaging
"""

import boto3
import zipfile
import os
import json
from datetime import datetime

def create_deployment_package(source_dir, zip_path, handler_file):
    """Create deployment package for Lambda function"""
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all Python files from source directory
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    print(f"Added {arcname} to deployment package")
        
        # Ensure the handler file is the main one
        if handler_file and os.path.exists(os.path.join(source_dir, handler_file)):
            # Copy updated handler as main handler
            zipf.write(
                os.path.join(source_dir, handler_file), 
                handler_file.replace('_updated', '')
            )
            print(f"Set {handler_file} as main handler")

def deploy_vector_embeddings_processor():
    """Deploy updated vector embeddings processor"""
    
    print("🚀 Deploying Vector Embeddings Processor with Standardized Messaging")
    print("=" * 70)
    
    # Use correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    source_dir = 'lambda/vector_embeddings_processor'
    zip_path = '/tmp/vector_embeddings_processor_updated.zip'
    
    create_deployment_package(source_dir, zip_path, 'vector_embeddings_processor_updated.py')
    
    # Get function name
    function_name = 'vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA'
    
    try:
        # Update function code
        with open(zip_path, 'rb') as zip_file:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
        
        print(f"✅ Updated function code: {response['LastModified']}")
        
        # Update handler to use the updated version
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Handler='vector_embeddings_processor_updated.lambda_handler',
            Environment={
                'Variables': {
                    'VECTOR_WORKER_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:vector-embeddings-worker',
                    'DATABASE_URL': 'postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require',
                    'STANDARDIZED_MESSAGING_ENABLED': 'true',
                    'COST_THRESHOLD_PER_DOC': '0.50'
                }
            }
        )
        
        print("✅ Updated function configuration with standardized messaging")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying vector embeddings processor: {str(e)}")
        return False
    
    finally:
        # Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)

def deploy_vector_embeddings_worker():
    """Deploy updated vector embeddings worker"""
    
    print("\n🚀 Deploying Vector Embeddings Worker with Standardized Messaging")
    print("=" * 65)
    
    # Use correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Create deployment package
    source_dir = 'lambda/vector_embeddings_worker'
    zip_path = '/tmp/vector_embeddings_worker_updated.zip'
    
    create_deployment_package(source_dir, zip_path, 'vector_embeddings_worker_updated.py')
    
    # Get function name
    function_name = 'vector-embeddings-pipelin-VectorEmbeddingsWorker5F-nCQL6EhDMuyi'
    
    try:
        # Update function code
        with open(zip_path, 'rb') as zip_file:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file.read()
            )
        
        print(f"✅ Updated function code: {response['LastModified']}")
        
        # Update handler to use the updated version
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Handler='vector_embeddings_worker_updated.lambda_handler'
        )
        
        print("✅ Updated function configuration with standardized messaging")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying vector embeddings worker: {str(e)}")
        return False
    
    finally:
        # Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)

def test_vector_embeddings_integration():
    """Test vector embeddings with standardized messaging"""
    
    print("\n🧪 Testing Vector Embeddings Integration")
    print("=" * 40)
    
    # Use correct AWS profile
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Create test message in standardized format
    test_message = {
        "version": "1.0",
        "timestamp": datetime.now().isoformat() + "Z",
        "source": "climate-risk-rag-system",
        "stage": "chunks_ready",
        "doc_id": "test-vector-embeddings",
        "doc_hash": "test-hash-vector",
        "document_metadata": {
            "original_filename": "test-document.pdf",
            "file_size": 50000,
            "page_count": 2,
            "processing_started": datetime.now().isoformat() + "Z"
        },
        "data_locations": {
            "text_location": "s3://solve-global-kr-text-new-861276078413-us-east-1/test-vector-embeddings.txt",
            "chunks_location": "s3://solve-global-kr-chunks-861276078413-us-east-1/test-vector-embeddings/"
        },
        "processing_metadata": {
            "chunks_count": 5,
            "total_characters": 2500,
            "processing_duration_ms": 3000,
            "cost_estimate": 0.01
        },
        "integration_flags": {
            "documentid_manager_integration": True,
            "selective_migration_used": False,
            "database_tracking_enabled": True
        }
    }
    
    # Test vector embeddings processor
    sns_event = {
        "Records": [{
            "Sns": {
                "Message": json.dumps(test_message)
            }
        }]
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='vector-embeddings-pipelin-VectorEmbeddingsProcesso-YU1t1iUbDEkA',
            InvocationType='RequestResponse',
            Payload=json.dumps(sns_event)
        )
        
        result = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200 and 'errorMessage' not in result:
            print("✅ Vector embeddings processor handles standardized messages!")
            print(f"   Response: {result.get('body', 'Success')}")
            return True
        else:
            print(f"❌ Vector embeddings processor error: {result.get('errorMessage', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Vector Embeddings Standardized Messaging Deployment")
    print("=" * 55)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    success_count = 0
    
    # Deploy processor
    if deploy_vector_embeddings_processor():
        success_count += 1
    
    # Deploy worker
    if deploy_vector_embeddings_worker():
        success_count += 1
    
    # Test integration
    if test_vector_embeddings_integration():
        success_count += 1
    
    print(f"\n📊 Deployment Summary: {success_count}/3 components successful")
    
    if success_count == 3:
        print("🎉 Vector embeddings standardized messaging deployment complete!")
        print("   The vector embeddings pipeline should now work with the standardized messaging format.")
    else:
        print("⚠️  Some components failed - check logs and retry failed components.")
