#!/usr/bin/env python3
"""
Neptune Bulk Loader
Load TTL files from S3 into Neptune using the bulk loading API
"""

import boto3
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeptuneBulkLoader:
    """Neptune bulk loading operations"""
    
    def __init__(self, aws_profile: str = 'solve-global'):
        self.session = boto3.Session(profile_name=aws_profile)
        self.neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
        self.loader_endpoint = f"https://{self.neptune_endpoint}:8182/loader"
        self.ttl_bucket = "solve-global-kr-neptune-ttl-861276078413-us-east-1"
        
        # Create IAM role ARN for Neptune loading (we'll need to create this)
        self.account_id = "861276078413"
        self.neptune_load_role = f"arn:aws:iam::{self.account_id}:role/NeptuneLoadFromS3Role"
    
    def create_load_job(self, s3_path: str, format: str = "turtle", 
                       job_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a Neptune bulk load job"""
        
        if not job_name:
            job_name = f"load-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        load_request = {
            "source": s3_path,
            "format": format,
            "iamRoleArn": self.neptune_load_role,
            "region": "us-east-1",
            "failOnError": "FALSE",
            "parallelism": "MEDIUM",
            "updateSingleCardinalityProperties": "FALSE",
            "queueRequest": "TRUE"
        }
        
        logger.info(f"Creating Neptune load job: {job_name}")
        logger.info(f"Source: {s3_path}")
        
        try:
            response = requests.post(
                self.loader_endpoint,
                json=load_request,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Load job created successfully: {result['payload']['loadId']}")
                return result
            else:
                logger.error(f"❌ Failed to create load job: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating load job: {e}")
            return None
    
    def check_load_status(self, load_id: str) -> Dict[str, Any]:
        """Check the status of a Neptune load job"""
        
        try:
            response = requests.get(
                f"{self.loader_endpoint}/{load_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to check load status: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking load status: {e}")
            return None
    
    def wait_for_load_completion(self, load_id: str, timeout_minutes: int = 10) -> bool:
        """Wait for a load job to complete"""
        
        logger.info(f"Waiting for load job {load_id} to complete...")
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            status = self.check_load_status(load_id)
            
            if not status:
                logger.error("Failed to check load status")
                return False
            
            overall_status = status['payload']['overallStatus']['status']
            logger.info(f"Load status: {overall_status}")
            
            if overall_status == "LOAD_COMPLETED":
                logger.info("✅ Load completed successfully!")
                return True
            elif overall_status in ["LOAD_FAILED", "LOAD_CANCELLED"]:
                logger.error(f"❌ Load failed with status: {overall_status}")
                return False
            
            # Wait before checking again
            time.sleep(10)
        
        logger.error(f"❌ Load job timed out after {timeout_minutes} minutes")
        return False
    
    def load_document_ttl(self, doc_id: str) -> bool:
        """Load TTL files for a specific document"""
        
        logger.info(f"Loading TTL data for document: {doc_id}")
        
        # Load schema first
        schema_path = f"s3://{self.ttl_bucket}/ontology/"
        schema_job = self.create_load_job(schema_path, job_name=f"schema-{doc_id}")
        
        if not schema_job:
            logger.error("Failed to create schema load job")
            return False
        
        schema_load_id = schema_job['payload']['loadId']
        
        # Wait for schema to load
        if not self.wait_for_load_completion(schema_load_id, timeout_minutes=5):
            logger.error("Schema loading failed")
            return False
        
        # Load document data
        document_path = f"s3://{self.ttl_bucket}/documents/{doc_id}/"
        doc_job = self.create_load_job(document_path, job_name=f"document-{doc_id}")
        
        if not doc_job:
            logger.error("Failed to create document load job")
            return False
        
        doc_load_id = doc_job['payload']['loadId']
        
        # Wait for document to load
        if not self.wait_for_load_completion(doc_load_id, timeout_minutes=10):
            logger.error("Document loading failed")
            return False
        
        logger.info(f"✅ Successfully loaded all TTL data for document {doc_id}")
        return True
    
    def test_loaded_data(self) -> bool:
        """Test that data was loaded correctly"""
        
        logger.info("Testing loaded data with SPARQL queries...")
        
        sparql_endpoint = f"https://{self.neptune_endpoint}:8182/sparql"
        
        # Test 1: Count total triples
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        try:
            response = requests.post(
                sparql_endpoint,
                data=count_query,
                headers={
                    'Content-Type': 'application/sparql-query',
                    'Accept': 'application/sparql-results+json'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                count = result['results']['bindings'][0]['count']['value']
                logger.info(f"✅ Total triples loaded: {count}")
            else:
                logger.error(f"Failed to count triples: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error counting triples: {e}")
            return False
        
        # Test 2: Query document structure
        doc_query = """
        SELECT ?doc ?title ?wordCount WHERE {
            ?doc a <http://solve.global/knowledge-commons/schema#Document> .
            ?doc <http://purl.org/dc/terms/title> ?title .
            ?doc <http://solve.global/knowledge-commons/schema#wordCount> ?wordCount .
        }
        """
        
        try:
            response = requests.post(
                sparql_endpoint,
                data=doc_query,
                headers={
                    'Content-Type': 'application/sparql-query',
                    'Accept': 'application/sparql-results+json'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                docs = result['results']['bindings']
                logger.info(f"✅ Found {len(docs)} documents:")
                for doc in docs:
                    title = doc['title']['value']
                    word_count = doc['wordCount']['value']
                    logger.info(f"   - {title} ({word_count} words)")
                return True
            else:
                logger.error(f"Failed to query documents: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error querying documents: {e}")
            return False

def create_neptune_load_role():
    """Create IAM role for Neptune loading (helper function)"""
    
    print("🔧 CREATING NEPTUNE LOAD ROLE")
    print("=" * 50)
    print("You need to create an IAM role for Neptune to access S3.")
    print("Run these AWS CLI commands:")
    print()
    print("1. Create trust policy file:")
    print("cat > /tmp/neptune-trust-policy.json << 'EOF'")
    print("""{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "rds.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF""")
    print()
    print("2. Create the role:")
    print("aws iam create-role --role-name NeptuneLoadFromS3Role --assume-role-policy-document file:///tmp/neptune-trust-policy.json --profile solve-global")
    print()
    print("3. Attach S3 read policy:")
    print("aws iam attach-role-policy --role-name NeptuneLoadFromS3Role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess --profile solve-global")
    print()
    print("4. Add Neptune cluster to the role (replace cluster-id):")
    print("aws neptune add-role-to-db-cluster --db-cluster-identifier solve-global-kr-neptune --role-arn arn:aws:iam::861276078413:role/NeptuneLoadFromS3Role --profile solve-global")

def main():
    """Main function to load TTL data into Neptune"""
    
    print("🚀 NEPTUNE BULK LOADER")
    print("=" * 50)
    
    # Check if we need to create the IAM role first
    loader = NeptuneBulkLoader()
    
    # Test document
    doc_id = "0032f6cb_f0caef34"
    
    try:
        # Try to load the document
        success = loader.load_document_ttl(doc_id)
        
        if success:
            # Test the loaded data
            if loader.test_loaded_data():
                print("🎉 Neptune bulk loading completed successfully!")
                return True
            else:
                print("⚠️ Data loaded but testing failed")
                return False
        else:
            print("❌ Neptune bulk loading failed")
            print()
            create_neptune_load_role()
            return False
            
    except Exception as e:
        print(f"❌ Error during bulk loading: {e}")
        print()
        create_neptune_load_role()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
