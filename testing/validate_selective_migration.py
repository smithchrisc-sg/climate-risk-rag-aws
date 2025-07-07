#!/usr/bin/env python3
"""
Validate Selective Migration Results
Checks that the selective migration completed successfully and data is accessible
"""

import boto3
import json
import argparse
import logging
from typing import Dict, List, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SelectiveMigrationValidator:
    """Validates selective migration results in AWS"""
    
    def __init__(self, region: str, profile: str = None):
        self.region = region
        self.profile = profile
        
        # Initialize AWS clients with profile if provided
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.s3_client = session.client('s3', region_name=region)
        
        # Get bucket names
        sts_client = session.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        self.documents_bucket = f"solve-global-kr-documents-{account_id}-{region}"
        self.chunks_bucket = f"solve-global-kr-chunks-{account_id}-{region}"
        self.embeddings_bucket = f"solve-global-kr-embeddings-{account_id}-{region}"
        self.ner_bucket = f"solve-global-kr-ner-{account_id}-{region}"
        self.text_bucket = f"solve-global-kr-text-{account_id}-{region}"
    
    def validate_migration(self, sample_file: str) -> Dict[str, Any]:
        """Validate the selective migration results"""
        logger.info("Validating selective migration results...")
        
        # Load sample selection
        with open(sample_file, 'r') as f:
            sample_data = json.load(f)
        
        sample_docs = sample_data.get('sample_documents', [])
        expected_count = len(sample_docs)
        
        logger.info(f"Validating migration of {expected_count} documents...")
        
        validation_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'expected_documents': expected_count,
            'validation_results': {
                'documents': self._validate_documents(sample_docs),
                'chunks': self._validate_chunks(sample_docs),
                'embeddings': self._validate_embeddings(sample_docs),
                'text_files': self._validate_text_files(sample_docs),
                'ner_results': self._validate_ner_results(sample_docs),
                'metadata': self._validate_metadata()
            }
        }
        
        # Calculate overall success
        all_validations = validation_results['validation_results']
        success_rates = [v.get('success_rate', 0) for v in all_validations.values()]
        overall_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        
        validation_results['overall_success_rate'] = overall_success_rate
        validation_results['migration_successful'] = overall_success_rate > 0.8
        
        return validation_results
    
    def _validate_documents(self, sample_docs: List[Dict]) -> Dict[str, Any]:
        """Validate document migration"""
        logger.info("Validating document migration...")
        
        found_count = 0
        missing_docs = []
        
        for doc in sample_docs:
            doc_id = doc['doc_id']
            s3_key = f"documents/{doc_id}.pdf"
            
            try:
                self.s3_client.head_object(Bucket=self.documents_bucket, Key=s3_key)
                found_count += 1
            except Exception as e:
                missing_docs.append(doc_id)
        
        return {
            'expected': len(sample_docs),
            'found': found_count,
            'missing': len(missing_docs),
            'missing_docs': missing_docs[:10],  # First 10 missing
            'success_rate': found_count / len(sample_docs) if sample_docs else 0
        }
    
    def _validate_chunks(self, sample_docs: List[Dict]) -> Dict[str, Any]:
        """Validate chunks migration"""
        logger.info("Validating chunks migration...")
        
        docs_with_chunks = 0
        total_chunks = 0
        
        for doc in sample_docs[:10]:  # Check first 10 documents
            doc_id = doc['doc_id']
            prefix = f"chunks/{doc_id}/"
            
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.chunks_bucket,
                    Prefix=prefix,
                    MaxKeys=1000
                )
                
                chunk_count = response.get('KeyCount', 0)
                if chunk_count > 0:
                    docs_with_chunks += 1
                    total_chunks += chunk_count
                    
            except Exception as e:
                logger.debug(f"Error checking chunks for {doc_id}: {e}")
        
        return {
            'docs_checked': min(10, len(sample_docs)),
            'docs_with_chunks': docs_with_chunks,
            'total_chunks_found': total_chunks,
            'avg_chunks_per_doc': total_chunks / docs_with_chunks if docs_with_chunks > 0 else 0,
            'success_rate': docs_with_chunks / min(10, len(sample_docs)) if sample_docs else 0
        }
    
    def _validate_embeddings(self, sample_docs: List[Dict]) -> Dict[str, Any]:
        """Validate embeddings migration"""
        logger.info("Validating embeddings migration...")
        
        docs_with_embeddings = 0
        total_embeddings = 0
        
        for doc in sample_docs[:10]:  # Check first 10 documents
            doc_id = doc['doc_id']
            prefix = f"embeddings/{doc_id}/"
            
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.embeddings_bucket,
                    Prefix=prefix,
                    MaxKeys=1000
                )
                
                embedding_count = response.get('KeyCount', 0)
                if embedding_count > 0:
                    docs_with_embeddings += 1
                    total_embeddings += embedding_count
                    
            except Exception as e:
                logger.debug(f"Error checking embeddings for {doc_id}: {e}")
        
        return {
            'docs_checked': min(10, len(sample_docs)),
            'docs_with_embeddings': docs_with_embeddings,
            'total_embeddings_found': total_embeddings,
            'avg_embeddings_per_doc': total_embeddings / docs_with_embeddings if docs_with_embeddings > 0 else 0,
            'success_rate': docs_with_embeddings / min(10, len(sample_docs)) if sample_docs else 0
        }
    
    def _validate_text_files(self, sample_docs: List[Dict]) -> Dict[str, Any]:
        """Validate text files migration"""
        logger.info("Validating text files migration...")
        
        found_count = 0
        
        for doc in sample_docs[:20]:  # Check first 20 documents
            doc_id = doc['doc_id']
            s3_key = f"extracted_text/{doc_id}.txt"
            
            try:
                self.s3_client.head_object(Bucket=self.text_bucket, Key=s3_key)
                found_count += 1
            except Exception as e:
                pass  # Text files might not exist for all documents
        
        return {
            'docs_checked': min(20, len(sample_docs)),
            'text_files_found': found_count,
            'success_rate': found_count / min(20, len(sample_docs)) if sample_docs else 0
        }
    
    def _validate_ner_results(self, sample_docs: List[Dict]) -> Dict[str, Any]:
        """Validate NER results migration"""
        logger.info("Validating NER results migration...")
        
        found_count = 0
        
        for doc in sample_docs[:20]:  # Check first 20 documents
            doc_id = doc['doc_id']
            s3_key = f"ner_results/{doc_id}_ner_results.json"
            
            try:
                self.s3_client.head_object(Bucket=self.ner_bucket, Key=s3_key)
                found_count += 1
            except Exception as e:
                pass  # NER results might not exist for all documents
        
        return {
            'docs_checked': min(20, len(sample_docs)),
            'ner_files_found': found_count,
            'success_rate': found_count / min(20, len(sample_docs)) if sample_docs else 0
        }
    
    def _validate_metadata(self) -> Dict[str, Any]:
        """Validate migration metadata"""
        logger.info("Validating migration metadata...")
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.chunks_bucket,
                Key='metadata/selective_migration_metadata.json'
            )
            
            metadata = json.loads(response['Body'].read())
            
            return {
                'metadata_exists': True,
                'migration_type': metadata.get('migration_info', {}).get('type'),
                'sample_size': metadata.get('migration_info', {}).get('sample_size'),
                'migration_timestamp': metadata.get('migration_info', {}).get('timestamp'),
                'success_rate': 1.0
            }
            
        except Exception as e:
            logger.warning(f"Could not validate metadata: {e}")
            return {
                'metadata_exists': False,
                'error': str(e),
                'success_rate': 0.0
            }


def main():
    parser = argparse.ArgumentParser(description='Validate selective migration results')
    parser.add_argument('--sample-file', required=True, help='Sample selection JSON file')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--output', help='Output validation results to file')
    
    args = parser.parse_args()
    
    try:
        validator = SelectiveMigrationValidator(args.region, args.profile)
        results = validator.validate_migration(args.sample_file)
        
        # Print results
        print(f"\n{'='*60}")
        print("SELECTIVE MIGRATION VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Overall Success Rate: {results['overall_success_rate']:.1%}")
        print(f"Migration Successful: {'✅ YES' if results['migration_successful'] else '❌ NO'}")
        print(f"Expected Documents: {results['expected_documents']}")
        
        print(f"\nDetailed Results:")
        for category, result in results['validation_results'].items():
            success_rate = result.get('success_rate', 0)
            print(f"  {category.title()}: {success_rate:.1%} success rate")
            
            if category == 'documents':
                print(f"    Found: {result['found']}/{result['expected']} documents")
                if result['missing'] > 0:
                    print(f"    Missing: {result['missing']} documents")
            
            elif category in ['chunks', 'embeddings']:
                print(f"    Docs with {category}: {result.get('docs_with_chunks', result.get('docs_with_embeddings', 0))}")
                print(f"    Total {category}: {result.get('total_chunks_found', result.get('total_embeddings_found', 0))}")
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nDetailed results saved to: {args.output}")
        
        return 0 if results['migration_successful'] else 1
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
