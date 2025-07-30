#!/usr/bin/env python3
"""
Check database for recent Textract jobs and processing status
"""

import psycopg2
import os
from datetime import datetime, timedelta

def check_recent_textract_jobs():
    """Check database for recent Textract jobs"""
    
    # Database connection
    db_url = "postgresql://postgres:-VroWHWQBS5!V)yAcsDC3(3)NHJ5@solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com:5432/climate_risk_rag?sslmode=require"
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check recent document processing status
        print("📊 Recent Document Processing Status:")
        cursor.execute("""
            SELECT doc_id, status, created_at, updated_at, textract_job_id
            FROM document_processing_status 
            WHERE created_at > NOW() - INTERVAL '2 hours'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        if results:
            print(f"Found {len(results)} recent documents:")
            for row in results:
                doc_id, status, created_at, updated_at, textract_job_id = row
                print(f"  📄 {doc_id}")
                print(f"     Status: {status}")
                print(f"     Created: {created_at}")
                print(f"     Updated: {updated_at}")
                print(f"     Textract Job: {textract_job_id}")
                print()
        else:
            print("No recent documents found")
        
        # Check for any pending Textract jobs
        print("\n🔄 Pending Textract Jobs:")
        cursor.execute("""
            SELECT doc_id, textract_job_id, created_at
            FROM document_processing_status 
            WHERE status = 'TEXTRACT_INITIATED' OR status = 'TEXTRACT_IN_PROGRESS'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        pending = cursor.fetchall()
        
        if pending:
            print(f"Found {len(pending)} pending jobs:")
            for row in pending:
                doc_id, textract_job_id, created_at = row
                print(f"  ⏳ {doc_id}: {textract_job_id} (since {created_at})")
        else:
            print("No pending Textract jobs")
        
        # Check for recent errors
        print("\n❌ Recent Processing Errors:")
        cursor.execute("""
            SELECT doc_id, status, error_message, updated_at
            FROM document_processing_status 
            WHERE status LIKE '%ERROR%' OR status LIKE '%FAILED%'
            AND updated_at > NOW() - INTERVAL '2 hours'
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        
        errors = cursor.fetchall()
        
        if errors:
            print(f"Found {len(errors)} recent errors:")
            for row in errors:
                doc_id, status, error_message, updated_at = row
                print(f"  ❌ {doc_id}: {status}")
                print(f"     Error: {error_message}")
                print(f"     Time: {updated_at}")
                print()
        else:
            print("No recent errors")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_recent_textract_jobs()
