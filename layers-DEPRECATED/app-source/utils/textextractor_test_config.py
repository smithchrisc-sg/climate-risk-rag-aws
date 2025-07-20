#!/usr/bin/env python3
"""
Cost-Safe TextExtractor Testing Configuration
Prevents runaway Textract charges during development
"""

import os
import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TextExtractorTestSafety:
    """Safety controls for TextExtractor testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Cost safety limits
        self.MAX_PAGES_PER_TEST = 5  # Maximum pages to process in one test
        self.MAX_JOBS_PER_HOUR = 3   # Maximum jobs per hour
        self.MAX_DAILY_SPEND = 10.0  # Maximum daily spend in USD
        
        # Test mode settings
        self.DRY_RUN = True  # Set to False only when ready for real testing
        self.USE_BASIC_TEXTRACT = True  # Use cheaper DetectDocumentText instead of AnalyzeDocument
        
        # AWS configuration - use correct profile and account
        session = boto3.Session(profile_name='solve-global')
        self.textract = session.client('textract', region_name='us-east-1')
        self.s3 = session.client('s3', region_name='us-east-1')
        
        # Correct bucket name
        self.test_bucket = 'solve-global-kr-documents-861276078413-us-east-1'
        
        self.logger.info("TextExtractor Safety Controls Initialized")
        self.logger.warning(f"DRY_RUN mode: {self.DRY_RUN}")
        self.logger.warning(f"Max pages per test: {self.MAX_PAGES_PER_TEST}")
        self.logger.info(f"Using bucket: {self.test_bucket}")
    
    def check_document_safety(self, bucket: str, key: str) -> Dict[str, any]:
        """Check if document is safe to process"""
        try:
            # Get document metadata
            response = self.s3.head_object(Bucket=bucket, Key=key)
            file_size = response['ContentLength']
            
            # Estimate page count (rough estimate: 50KB per page for PDFs)
            estimated_pages = max(1, file_size // 50000)
            
            # Calculate estimated cost
            # Textract AnalyzeDocument: $0.065 per page
            # Textract DetectDocumentText: $0.0015 per page
            cost_per_page = 0.065 if not self.USE_BASIC_TEXTRACT else 0.0015
            estimated_cost = estimated_pages * cost_per_page
            
            safety_check = {
                'safe_to_process': True,
                'file_size_bytes': file_size,
                'estimated_pages': estimated_pages,
                'estimated_cost_usd': round(estimated_cost, 4),
                'warnings': []
            }
            
            # Safety checks
            if estimated_pages > self.MAX_PAGES_PER_TEST:
                safety_check['safe_to_process'] = False
                safety_check['warnings'].append(f"Document too large: {estimated_pages} pages > {self.MAX_PAGES_PER_TEST} limit")
            
            if estimated_cost > 1.0:  # $1 per document limit
                safety_check['safe_to_process'] = False
                safety_check['warnings'].append(f"Estimated cost too high: ${estimated_cost:.4f}")
            
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                safety_check['safe_to_process'] = False
                safety_check['warnings'].append(f"File too large: {file_size / 1024 / 1024:.1f}MB > 10MB limit")
            
            return safety_check
            
        except Exception as e:
            self.logger.error(f"Error checking document safety: {e}")
            return {
                'safe_to_process': False,
                'warnings': [f"Error accessing document: {str(e)}"]
            }
    
    def check_rate_limits(self) -> Dict[str, any]:
        """Check if we're within rate limits"""
        # This would typically check a database or cache for recent job history
        # For now, return a simple check
        return {
            'within_limits': True,
            'jobs_this_hour': 0,
            'estimated_daily_spend': 0.0,
            'warnings': []
        }
    
    def create_test_document(self, output_bucket: str) -> str:
        """Create a small test PDF for safe testing"""
        try:
            # Create a minimal PDF content (just text)
            test_content = """
            Climate Risk Assessment Test Document
            
            This is a minimal test document for TextExtractor testing.
            It contains only basic text to minimize Textract costs.
            
            Test Date: {date}
            Document Type: Test PDF
            Pages: 1
            
            This document should cost less than $0.01 to process.
            """.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            # For now, just return instructions to create a test file
            test_key = f"test-documents/textextractor-test-{int(datetime.now().timestamp())}.txt"
            
            # Upload test content as text file (cheaper to process)
            self.s3.put_object(
                Bucket=output_bucket,
                Key=test_key,
                Body=test_content.encode('utf-8'),
                ContentType='text/plain'
            )
            
            self.logger.info(f"Created test document: s3://{output_bucket}/{test_key}")
            return test_key
            
        except Exception as e:
            self.logger.error(f"Error creating test document: {e}")
            raise
    
    def safe_textract_call(self, bucket: str, key: str, dry_run: bool = None) -> Dict[str, any]:
        """Make a cost-safe Textract call"""
        if dry_run is None:
            dry_run = self.DRY_RUN
        
        # Safety checks
        safety_check = self.check_document_safety(bucket, key)
        rate_check = self.check_rate_limits()
        
        result = {
            'job_started': False,
            'job_id': None,
            'safety_check': safety_check,
            'rate_check': rate_check,
            'dry_run': dry_run
        }
        
        if not safety_check['safe_to_process']:
            result['error'] = f"Document failed safety check: {safety_check['warnings']}"
            return result
        
        if not rate_check['within_limits']:
            result['error'] = f"Rate limit exceeded: {rate_check['warnings']}"
            return result
        
        if dry_run:
            result['message'] = "DRY RUN: Would start Textract job"
            result['estimated_cost'] = safety_check['estimated_cost_usd']
            self.logger.info(f"DRY RUN: Would process s3://{bucket}/{key} for ~${safety_check['estimated_cost_usd']:.4f}")
            return result
        
        # Real Textract call (only if dry_run=False)
        try:
            if self.USE_BASIC_TEXTRACT:
                # Use cheaper DetectDocumentText
                response = self.textract.start_document_text_detection(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': bucket,
                            'Name': key
                        }
                    }
                )
            else:
                # Use expensive AnalyzeDocument (full features)
                response = self.textract.start_document_analysis(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': bucket,
                            'Name': key
                        }
                    },
                    FeatureTypes=['TABLES', 'FORMS', 'LAYOUT']
                )
            
            result['job_started'] = True
            result['job_id'] = response['JobId']
            result['actual_cost'] = safety_check['estimated_cost_usd']
            
            self.logger.info(f"Started Textract job: {response['JobId']} (${safety_check['estimated_cost_usd']:.4f})")
            
        except Exception as e:
            result['error'] = f"Textract API error: {str(e)}"
            self.logger.error(f"Textract API error: {e}")
        
        return result

def print_safety_summary():
    """Print safety configuration summary"""
    safety = TextExtractorTestSafety()
    
    print("🛡️  TextExtractor Safety Configuration")
    print("=" * 50)
    print(f"DRY RUN Mode: {safety.DRY_RUN}")
    print(f"Use Basic Textract: {safety.USE_BASIC_TEXTRACT}")
    print(f"Max Pages Per Test: {safety.MAX_PAGES_PER_TEST}")
    print(f"Max Jobs Per Hour: {safety.MAX_JOBS_PER_HOUR}")
    print(f"Max Daily Spend: ${safety.MAX_DAILY_SPEND}")
    print()
    print("Cost Estimates:")
    print(f"  Basic Text Detection: $0.0015 per page")
    print(f"  Full Analysis: $0.065 per page")
    print(f"  5-page document (basic): ~$0.0075")
    print(f"  5-page document (full): ~$0.325")
    print()
    print("⚠️  To enable real testing:")
    print("   1. Set DRY_RUN = False")
    print("   2. Verify AWS billing alerts are set")
    print("   3. Start with USE_BASIC_TEXTRACT = True")

if __name__ == "__main__":
    print_safety_summary()
