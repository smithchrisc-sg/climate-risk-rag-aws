#!/usr/bin/env python3
"""
Optimized TextExtractor Configuration for Climate Risk RAG
Balances features needed vs free tier usage
"""

import os
import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class OptimizedTextExtractorConfig:
    """Optimized TextExtractor configuration for climate risk documents"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Free tier limits (monthly)
        self.FREE_TIER_BASIC_PAGES = 1000      # DetectDocumentText
        self.FREE_TIER_ADVANCED_PAGES = 100    # AnalyzeDocument
        
        # Safety limits for testing
        self.MAX_PAGES_PER_TEST = 10           # Increased since we have 1000/month
        self.MAX_BASIC_JOBS_PER_DAY = 50       # Conservative daily limit for basic
        self.MAX_ADVANCED_JOBS_PER_DAY = 5     # Conservative daily limit for advanced
        
        # Feature configuration based on requirements
        self.EXTRACTION_MODES = {
            'basic': {
                'method': 'DetectDocumentText',
                'features': [],
                'cost_per_page': 0.0015,
                'free_tier_pages': 1000,
                'description': 'Text only - good for basic content extraction'
            },
            'structure': {
                'method': 'AnalyzeDocument', 
                'features': ['LAYOUT'],
                'cost_per_page': 0.065,
                'free_tier_pages': 100,
                'description': 'Text + document structure (paragraphs, headers, etc.)'
            },
            'structure_tables': {
                'method': 'AnalyzeDocument',
                'features': ['LAYOUT', 'TABLES'],
                'cost_per_page': 0.065,
                'free_tier_pages': 100,
                'description': 'Text + structure + tables (recommended for climate reports)'
            },
            'full': {
                'method': 'AnalyzeDocument',
                'features': ['LAYOUT', 'TABLES', 'FORMS'],
                'cost_per_page': 0.065,
                'free_tier_pages': 100,
                'description': 'All features (not needed for climate documents)'
            }
        }
        
        # Default mode for climate risk documents
        self.DEFAULT_MODE = 'structure_tables'  # Text + structure + tables, no forms
        
        # Test configuration
        self.DRY_RUN = True
        self.TEST_MODE = 'structure'  # Start with structure only for testing
        
        # AWS configuration
        session = boto3.Session(profile_name='solve-global')
        self.textract = session.client('textract', region_name='us-east-1')
        self.s3 = session.client('s3', region_name='us-east-1')
        
        self.test_bucket = 'solve-global-kr-documents-861276078413-us-east-1'
        
        self.logger.info("Optimized TextExtractor Config initialized")
        self.logger.info(f"Default mode: {self.DEFAULT_MODE}")
        self.logger.info(f"Test mode: {self.TEST_MODE}")
    
    def get_extraction_config(self, mode: str = None) -> Dict:
        """Get extraction configuration for specified mode"""
        mode = mode or self.DEFAULT_MODE
        
        if mode not in self.EXTRACTION_MODES:
            raise ValueError(f"Unknown extraction mode: {mode}. Available: {list(self.EXTRACTION_MODES.keys())}")
        
        return self.EXTRACTION_MODES[mode]
    
    def estimate_monthly_usage(self, documents: List[Dict]) -> Dict:
        """Estimate monthly Textract usage and costs"""
        basic_pages = 0
        advanced_pages = 0
        
        for doc in documents:
            pages = doc.get('estimated_pages', 1)
            mode = doc.get('extraction_mode', self.DEFAULT_MODE)
            
            if self.EXTRACTION_MODES[mode]['method'] == 'DetectDocumentText':
                basic_pages += pages
            else:
                advanced_pages += pages
        
        # Calculate costs
        basic_free = min(basic_pages, self.FREE_TIER_BASIC_PAGES)
        basic_paid = max(0, basic_pages - self.FREE_TIER_BASIC_PAGES)
        
        advanced_free = min(advanced_pages, self.FREE_TIER_ADVANCED_PAGES)
        advanced_paid = max(0, advanced_pages - self.FREE_TIER_ADVANCED_PAGES)
        
        basic_cost = basic_paid * 0.0015
        advanced_cost = advanced_paid * 0.065
        
        return {
            'basic_pages': basic_pages,
            'advanced_pages': advanced_pages,
            'basic_free_pages': basic_free,
            'basic_paid_pages': basic_paid,
            'advanced_free_pages': advanced_free,
            'advanced_paid_pages': advanced_paid,
            'total_cost': basic_cost + advanced_cost,
            'within_free_tier': (basic_pages <= self.FREE_TIER_BASIC_PAGES and 
                               advanced_pages <= self.FREE_TIER_ADVANCED_PAGES)
        }
    
    def check_document_for_extraction(self, bucket: str, key: str, mode: str = None) -> Dict:
        """Check if document is suitable for extraction with specified mode"""
        mode = mode or self.TEST_MODE
        config = self.get_extraction_config(mode)
        
        try:
            # Get document metadata
            response = self.s3.head_object(Bucket=bucket, Key=key)
            file_size = response['ContentLength']
            
            # Estimate pages (more conservative for PDFs)
            estimated_pages = max(1, file_size // 40000)  # ~40KB per page
            
            # Calculate cost
            cost_per_page = 0 if estimated_pages <= config['free_tier_pages'] else config['cost_per_page']
            estimated_cost = estimated_pages * cost_per_page
            
            # Safety checks
            warnings = []
            safe_to_process = True
            
            if estimated_pages > self.MAX_PAGES_PER_TEST:
                safe_to_process = False
                warnings.append(f"Document too large: {estimated_pages} pages > {self.MAX_PAGES_PER_TEST} limit")
            
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                safe_to_process = False
                warnings.append(f"File too large: {file_size / 1024 / 1024:.1f}MB > 10MB limit")
            
            # Check if we should use free tier
            use_free_tier = estimated_pages <= config['free_tier_pages']
            
            return {
                'safe_to_process': safe_to_process,
                'extraction_mode': mode,
                'method': config['method'],
                'features': config['features'],
                'file_size_bytes': file_size,
                'estimated_pages': estimated_pages,
                'estimated_cost': estimated_cost,
                'use_free_tier': use_free_tier,
                'free_tier_remaining': config['free_tier_pages'] - estimated_pages if use_free_tier else 0,
                'warnings': warnings,
                'description': config['description']
            }
            
        except Exception as e:
            return {
                'safe_to_process': False,
                'error': str(e),
                'warnings': [f"Error accessing document: {str(e)}"]
            }
    
    def make_textract_call(self, bucket: str, key: str, mode: str = None, dry_run: bool = None) -> Dict:
        """Make optimized Textract API call"""
        if dry_run is None:
            dry_run = self.DRY_RUN
        
        mode = mode or self.TEST_MODE
        config = self.get_extraction_config(mode)
        
        # Safety check
        safety_check = self.check_document_for_extraction(bucket, key, mode)
        
        if not safety_check['safe_to_process']:
            return {
                'success': False,
                'error': 'Document failed safety check',
                'safety_check': safety_check
            }
        
        if dry_run:
            return {
                'success': True,
                'dry_run': True,
                'job_id': f"dry-run-{int(datetime.now().timestamp())}",
                'mode': mode,
                'method': config['method'],
                'features': config['features'],
                'safety_check': safety_check,
                'message': f"DRY RUN: Would use {config['method']} with features {config['features']}"
            }
        
        # Real API call
        try:
            if config['method'] == 'DetectDocumentText':
                # Basic text extraction
                response = self.textract.start_document_text_detection(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': bucket,
                            'Name': key
                        }
                    }
                )
            else:
                # Advanced analysis with specified features
                response = self.textract.start_document_analysis(
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': bucket,
                            'Name': key
                        }
                    },
                    FeatureTypes=config['features']
                )
            
            return {
                'success': True,
                'job_id': response['JobId'],
                'mode': mode,
                'method': config['method'],
                'features': config['features'],
                'safety_check': safety_check
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Textract API error: {str(e)}",
                'safety_check': safety_check
            }
    
    def find_suitable_test_documents(self, max_docs: int = 5) -> List[Dict]:
        """Find documents suitable for testing"""
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.test_bucket,
                Prefix='documents/',
                MaxKeys=20
            )
            
            suitable_docs = []
            
            for obj in response.get('Contents', []):
                key = obj['Key']
                size = obj['Size']
                
                # Quick size filter (under 500KB for testing)
                if size < 500000:  # ~12 pages max
                    check = self.check_document_for_extraction(self.test_bucket, key)
                    if check['safe_to_process']:
                        suitable_docs.append({
                            'key': key,
                            'size': size,
                            'check': check
                        })
                
                if len(suitable_docs) >= max_docs:
                    break
            
            return suitable_docs
            
        except Exception as e:
            self.logger.error(f"Error finding test documents: {e}")
            return []

def print_configuration_summary():
    """Print configuration summary"""
    config = OptimizedTextExtractorConfig()
    
    print("🎯 Optimized TextExtractor Configuration")
    print("=" * 50)
    print("Free Tier Limits:")
    print(f"  Basic Text: {config.FREE_TIER_BASIC_PAGES:,} pages/month")
    print(f"  Advanced: {config.FREE_TIER_ADVANCED_PAGES} pages/month")
    print()
    
    print("Extraction Modes:")
    for mode, details in config.EXTRACTION_MODES.items():
        marker = "👑" if mode == config.DEFAULT_MODE else "🧪" if mode == config.TEST_MODE else "  "
        print(f"{marker} {mode}:")
        print(f"    Method: {details['method']}")
        print(f"    Features: {details['features'] or ['None']}")
        print(f"    Cost: ${details['cost_per_page']:.4f}/page")
        print(f"    Free tier: {details['free_tier_pages']} pages/month")
        print(f"    Use case: {details['description']}")
        print()
    
    print("Recommendations for Climate Risk Documents:")
    print("  🎯 Production: 'structure_tables' (text + layout + tables)")
    print("  🧪 Testing: 'structure' (text + layout only)")
    print("  💰 Budget: 'basic' (text only)")
    print()
    
    # Find test documents
    print("🔍 Finding suitable test documents...")
    docs = config.find_suitable_test_documents(3)
    
    if docs:
        print(f"Found {len(docs)} suitable test documents:")
        for i, doc in enumerate(docs, 1):
            check = doc['check']
            print(f"  {i}. {doc['key']}")
            print(f"     Size: {doc['size']:,} bytes")
            print(f"     Pages: ~{check['estimated_pages']}")
            print(f"     Cost: ${check['estimated_cost']:.4f} ({check['extraction_mode']} mode)")
            print(f"     Free tier: {'✅' if check['use_free_tier'] else '❌'}")
    else:
        print("  No suitable test documents found")

if __name__ == "__main__":
    print_configuration_summary()
