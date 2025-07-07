#!/usr/bin/env python3
"""
Integration Testing Setup for Text Chunker Pipeline
Bridges the gap between existing S3 documents and DocumentIDManager
"""

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

class IntegrationTestingSetup:
    def __init__(self):
        self.session = boto3.Session(profile_name='solve-global')
        self.s3_client = self.session.client('s3', region_name='us-east-1')
        
        self.db_params = {
            'host': 'solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com',
            'port': 5432,
            'database': 'climate_risk_rag',
            'user': 'postgres',
            'password': '-VroWHWQBS5!V)yAcsDC3(3)NHJ5',
            'sslmode': 'require'
        }
        
        self.documents_bucket = 'solve-global-kr-documents-861276078413-us-east-1'
        self.text_bucket = 'solve-global-kr-text-new-861276078413-us-east-1'
        self.chunks_bucket = 'solve-global-kr-chunks-861276078413-us-east-1'

    def analyze_current_state(self):
        """Analyze current state of documents and database"""
        
        print("🔍 Analyzing Current Integration State")
        print("=" * 60)
        
        # Get S3 documents
        s3_docs = self._get_s3_documents()
        print(f"S3 Documents: {len(s3_docs)} PDFs found")
        
        # Get text extractions
        text_files = self._get_text_extractions()
        print(f"Text Extractions: {len(text_files)} files found")
        
        # Get database state
        db_docs, db_status = self._get_database_state()
        print(f"Database Documents: {len(db_docs)} records")
        print(f"Processing Status: {len(db_status)} records")
        
        # Find matches and gaps
        matches, gaps = self._find_integration_gaps(s3_docs, text_files, db_docs, db_status)
        
        print(f"\n📊 Integration Analysis:")
        print(f"   Complete matches: {len(matches['complete'])}")
        print(f"   Partial matches: {len(matches['partial'])}")
        print(f"   Missing database entries: {len(gaps['missing_db'])}")
        print(f"   Missing text extractions: {len(gaps['missing_text'])}")
        
        return {
            's3_docs': s3_docs,
            'text_files': text_files,
            'db_docs': db_docs,
            'db_status': db_status,
            'matches': matches,
            'gaps': gaps
        }

    def _get_s3_documents(self) -> List[Dict]:
        """Get list of documents in S3"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.documents_bucket,
                Prefix='documents/',
                MaxKeys=1000
            )
            
            docs = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.pdf'):
                    doc_id = key.split('/')[-1].replace('.pdf', '')
                    docs.append({
                        'doc_id': doc_id,
                        'key': key,
                        'size': obj['Size'],
                        'modified': obj['LastModified']
                    })
            
            return docs
        except Exception as e:
            print(f"Error getting S3 documents: {e}")
            return []

    def _get_text_extractions(self) -> List[Dict]:
        """Get list of text extractions"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.text_bucket,
                Prefix='extracted_text/',
                MaxKeys=1000
            )
            
            texts = []
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.txt'):
                    doc_id = key.split('/')[-1].replace('.txt', '')
                    texts.append({
                        'doc_id': doc_id,
                        'key': key,
                        'size': obj['Size'],
                        'modified': obj['LastModified']
                    })
            
            return texts
        except Exception as e:
            print(f"Error getting text extractions: {e}")
            return []

    def _get_database_state(self) -> tuple:
        """Get current database state"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get documents
            cursor.execute('SELECT * FROM documents')
            db_docs = cursor.fetchall()
            
            # Get processing status
            cursor.execute('SELECT * FROM document_processing_status')
            db_status = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return db_docs, db_status
            
        except Exception as e:
            print(f"Error getting database state: {e}")
            return [], []

    def _find_integration_gaps(self, s3_docs, text_files, db_docs, db_status):
        """Find integration gaps between S3, text files, and database"""
        
        # Create lookup sets
        s3_doc_ids = {doc['doc_id'] for doc in s3_docs}
        text_doc_ids = {text['doc_id'] for text in text_files}
        db_doc_ids = {doc['doc_id'] for doc in db_docs}
        status_doc_ids = {status['doc_hash'] for status in db_status}
        
        # Find matches
        complete_matches = []
        partial_matches = []
        
        for doc_id in s3_doc_ids:
            has_text = doc_id in text_doc_ids
            has_db = doc_id in db_doc_ids
            has_status = doc_id in status_doc_ids
            
            if has_text and has_db and has_status:
                complete_matches.append(doc_id)
            elif has_text or has_db or has_status:
                partial_matches.append({
                    'doc_id': doc_id,
                    'has_text': has_text,
                    'has_db': has_db,
                    'has_status': has_status
                })
        
        # Find gaps
        missing_db = s3_doc_ids - db_doc_ids
        missing_text = s3_doc_ids - text_doc_ids
        
        return {
            'complete': complete_matches,
            'partial': partial_matches
        }, {
            'missing_db': missing_db,
            'missing_text': missing_text
        }

    def create_integration_test_data(self, analysis_result: Dict):
        """Create proper integration test data"""
        
        print("\n🛠️ Creating Integration Test Data")
        print("=" * 60)
        
        s3_docs = analysis_result['s3_docs']
        text_files = analysis_result['text_files']
        gaps = analysis_result['gaps']
        
        # Select best candidates for integration testing
        test_candidates = self._select_test_candidates(s3_docs, text_files)
        
        print(f"Selected {len(test_candidates)} candidates for integration testing:")
        for candidate in test_candidates:
            print(f"  {candidate['doc_id']}: {candidate['size']:,} bytes")
        
        # Create/update database entries
        created_entries = self._create_database_entries(test_candidates)
        
        # Create processing status entries
        status_entries = self._create_processing_status_entries(test_candidates)
        
        return {
            'test_candidates': test_candidates,
            'database_entries': created_entries,
            'status_entries': status_entries
        }

    def _select_test_candidates(self, s3_docs: List[Dict], text_files: List[Dict]) -> List[Dict]:
        """Select best candidates for integration testing"""
        
        # Find documents that have both PDF and text extraction
        text_doc_ids = {text['doc_id'] for text in text_files}
        
        candidates = []
        for doc in s3_docs:
            if doc['doc_id'] in text_doc_ids:
                # Find corresponding text file
                text_file = next((t for t in text_files if t['doc_id'] == doc['doc_id']), None)
                if text_file:
                    candidates.append({
                        'doc_id': doc['doc_id'],
                        'pdf_key': doc['key'],
                        'pdf_size': doc['size'],
                        'text_key': text_file['key'],
                        'text_size': text_file['size'],
                        'priority': self._calculate_priority(doc, text_file)
                    })
        
        # Sort by priority (smaller files first for cost efficiency)
        candidates.sort(key=lambda x: x['priority'])
        
        # Return top 3 candidates
        return candidates[:3]

    def _calculate_priority(self, pdf_doc: Dict, text_file: Dict) -> int:
        """Calculate priority for test candidates (lower = higher priority)"""
        # Prioritize smaller files for cost efficiency
        return pdf_doc['size'] + text_file['size']

    def _create_database_entries(self, candidates: List[Dict]) -> List[Dict]:
        """Create proper database entries for test candidates"""
        
        print("\n📝 Creating Database Entries")
        print("-" * 40)
        
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            created_entries = []
            
            for candidate in candidates:
                doc_id = candidate['doc_id']
                
                # Check if entry already exists
                cursor.execute('SELECT doc_id FROM documents WHERE doc_id = %s', (doc_id,))
                existing = cursor.fetchone()
                
                if not existing:
                    # Create new entry
                    original_url = f"s3://{self.documents_bucket}/{candidate['pdf_key']}"
                    
                    cursor.execute('''
                        INSERT INTO documents (
                            doc_id, url, original_filename, pdf_path, text_path, 
                            status, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        doc_id,
                        original_url,
                        f"{doc_id}.pdf",
                        candidate['pdf_key'],
                        candidate['text_key'],
                        'extracted',
                        datetime.utcnow(),
                        datetime.utcnow()
                    ))
                    
                    print(f"✅ Created database entry for {doc_id}")
                    created_entries.append(doc_id)
                else:
                    # Update existing entry
                    cursor.execute('''
                        UPDATE documents 
                        SET pdf_path = %s, text_path = %s, status = %s, updated_at = %s
                        WHERE doc_id = %s
                    ''', (
                        candidate['pdf_key'],
                        candidate['text_key'],
                        'extracted',
                        datetime.utcnow(),
                        doc_id
                    ))
                    
                    print(f"✅ Updated database entry for {doc_id}")
                    created_entries.append(doc_id)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return created_entries
            
        except Exception as e:
            print(f"❌ Error creating database entries: {e}")
            return []

    def _create_processing_status_entries(self, candidates: List[Dict]) -> List[Dict]:
        """Create processing status entries for test candidates"""
        
        print("\n📊 Creating Processing Status Entries")
        print("-" * 40)
        
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            status_entries = []
            
            for candidate in candidates:
                doc_id = candidate['doc_id']
                
                # Check if status entry already exists
                cursor.execute('SELECT doc_hash FROM document_processing_status WHERE doc_hash = %s', (doc_id,))
                existing = cursor.fetchone()
                
                if not existing:
                    # Create new status entry
                    cursor.execute('''
                        INSERT INTO document_processing_status (
                            doc_hash, filename, source_bucket, source_key,
                            text_extraction_status, text_extraction_completed_at,
                            chunking_status, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        doc_id,
                        f"{doc_id}.pdf",
                        self.documents_bucket,
                        candidate['pdf_key'],
                        'COMPLETED',
                        datetime.utcnow(),
                        'PENDING',
                        datetime.utcnow(),
                        datetime.utcnow()
                    ))
                    
                    print(f"✅ Created status entry for {doc_id}")
                    status_entries.append(doc_id)
                else:
                    # Update existing status entry
                    cursor.execute('''
                        UPDATE document_processing_status 
                        SET text_extraction_status = %s, 
                            text_extraction_completed_at = %s,
                            chunking_status = %s,
                            updated_at = %s
                        WHERE doc_hash = %s
                    ''', (
                        'COMPLETED',
                        datetime.utcnow(),
                        'PENDING',
                        datetime.utcnow(),
                        doc_id
                    ))
                    
                    print(f"✅ Updated status entry for {doc_id}")
                    status_entries.append(doc_id)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return status_entries
            
        except Exception as e:
            print(f"❌ Error creating status entries: {e}")
            return []

    def run_integration_setup(self):
        """Run complete integration testing setup"""
        
        print("🚀 Integration Testing Setup")
        print("=" * 80)
        print(f"Started at: {datetime.utcnow().isoformat()}")
        print()
        
        # Step 1: Analyze current state
        analysis = self.analyze_current_state()
        
        # Step 2: Create integration test data
        test_data = self.create_integration_test_data(analysis)
        
        # Step 3: Validate setup
        validation = self._validate_integration_setup(test_data)
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 Integration Setup Results")
        print("=" * 80)
        
        candidates = test_data.get('test_candidates', [])
        db_entries = test_data.get('database_entries', [])
        status_entries = test_data.get('status_entries', [])
        
        print(f"✅ Test Candidates Selected: {len(candidates)}")
        print(f"✅ Database Entries Created: {len(db_entries)}")
        print(f"✅ Status Entries Created: {len(status_entries)}")
        
        if candidates:
            print(f"\n📋 Ready for Integration Testing:")
            for candidate in candidates:
                print(f"   {candidate['doc_id']}: {candidate['text_size']:,} bytes text")
        
        return test_data

    def _validate_integration_setup(self, test_data: Dict) -> bool:
        """Validate that integration setup is correct"""
        
        print("\n🔍 Validating Integration Setup")
        print("-" * 40)
        
        candidates = test_data.get('test_candidates', [])
        
        try:
            conn = psycopg2.connect(**self.db_params)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            for candidate in candidates:
                doc_id = candidate['doc_id']
                
                # Check documents table
                cursor.execute('SELECT * FROM documents WHERE doc_id = %s', (doc_id,))
                doc_record = cursor.fetchone()
                
                # Check processing status table
                cursor.execute('SELECT * FROM document_processing_status WHERE doc_hash = %s', (doc_id,))
                status_record = cursor.fetchone()
                
                if doc_record and status_record:
                    print(f"✅ {doc_id}: Complete integration setup")
                else:
                    print(f"❌ {doc_id}: Missing records")
                    return False
            
            cursor.close()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False

if __name__ == "__main__":
    setup = IntegrationTestingSetup()
    result = setup.run_integration_setup()
    
    if result and result.get('test_candidates'):
        print("\n🎉 Integration testing setup complete!")
        print("Ready to proceed with pipeline integration testing.")
    else:
        print("\n❌ Integration setup failed.")
        exit(1)
