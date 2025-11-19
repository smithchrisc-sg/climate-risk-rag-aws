#!/usr/bin/env python3
"""
Check pipeline processing status for documents loaded today
Verifies if documents from source bucket have been processed through all pipeline stages
"""

import boto3
from datetime import datetime, timezone
import json

# Configuration
SOURCE_BUCKET = "solve-global-kr-dl-source-documents-861276078413-us-east-1"
BUCKET_PREFIX = "solve-global-kr-dl-"
REGION = "us-east-1"

def get_todays_documents(s3_client, bucket):
    """Get doc_ids from PDFs added today in source bucket"""
    today = datetime.now(timezone.utc).date()
    doc_ids = []
    
    print(f"Checking {bucket} for documents added today ({today})...")
    
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix="data-lake/")
    
    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            key = obj['Key']
            last_modified = obj['LastModified'].date()
            
            # Check if PDF added today
            if key.endswith('.pdf') and last_modified == today:
                # Extract doc_id from filename (remove data-lake/ and .pdf)
                doc_id = key.replace('data-lake/', '').replace('.pdf', '')
                doc_ids.append({
                    'doc_id': doc_id,
                    'key': key,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
    
    return doc_ids

def get_all_data_lake_buckets(s3_client):
    """Get all buckets with solve-global-kr-dl- prefix"""
    response = s3_client.list_buckets()
    
    data_lake_buckets = []
    for bucket in response['Buckets']:
        name = bucket['Name']
        if name.startswith(BUCKET_PREFIX):
            data_lake_buckets.append(name)
    
    return sorted(data_lake_buckets)

def check_doc_in_bucket(s3_client, bucket, doc_id):
    """Check if doc_id exists in bucket's data-lake/ structure"""
    try:
        # List objects with doc_id prefix
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=f"data-lake/{doc_id}",
            MaxKeys=10
        )
        
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
            return {
                'present': True,
                'file_count': len(files),
                'files': files
            }
        else:
            return {'present': False, 'file_count': 0, 'files': []}
            
    except Exception as e:
        return {'present': False, 'error': str(e), 'file_count': 0, 'files': []}

def main():
    s3_client = boto3.client('s3', region_name=REGION)
    
    print("=" * 80)
    print("PIPELINE PROCESSING STATUS CHECK")
    print("=" * 80)
    
    # Get documents added today
    todays_docs = get_todays_documents(s3_client, SOURCE_BUCKET)
    
    if not todays_docs:
        print("\n❌ No documents found added today in source bucket")
        return
    
    print(f"\n✅ Found {len(todays_docs)} documents added today")
    print("\nSample documents:")
    for doc in todays_docs[:5]:
        print(f"  - {doc['doc_id']} ({doc['size']:,} bytes)")
    if len(todays_docs) > 5:
        print(f"  ... and {len(todays_docs) - 5} more")
    
    # Get all data-lake buckets
    print(f"\n🔍 Finding all {BUCKET_PREFIX}* buckets...")
    buckets = get_all_data_lake_buckets(s3_client)
    
    print(f"\nFound {len(buckets)} data-lake buckets:")
    for bucket in buckets:
        print(f"  - {bucket}")
    
    # Check each document in each bucket
    print(f"\n📊 Checking processing status for {len(todays_docs)} documents across {len(buckets)} buckets...")
    print()
    
    # Build status matrix
    doc_ids = [doc['doc_id'] for doc in todays_docs]
    status_matrix = {}
    
    for bucket in buckets:
        print(f"Checking {bucket}...")
        bucket_status = {}
        
        for doc_id in doc_ids:
            result = check_doc_in_bucket(s3_client, bucket, doc_id)
            bucket_status[doc_id] = result
        
        status_matrix[bucket] = bucket_status
        
        # Count present docs
        present_count = sum(1 for status in bucket_status.values() if status['present'])
        print(f"  ✓ {present_count}/{len(doc_ids)} documents present")
    
    # Summary report
    print("\n" + "=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)
    
    # Per-bucket summary
    print(f"\nProcessing completion by bucket:")
    for bucket in buckets:
        present_count = sum(1 for status in status_matrix[bucket].values() if status['present'])
        percentage = (present_count / len(doc_ids) * 100) if doc_ids else 0
        print(f"  {bucket}: {present_count}/{len(doc_ids)} ({percentage:.1f}%)")
    
    # Per-document summary
    print(f"\nProcessing completion by document:")
    for doc_id in doc_ids[:10]:  # Show first 10
        bucket_count = sum(1 for bucket in buckets if status_matrix[bucket][doc_id]['present'])
        percentage = (bucket_count / len(buckets) * 100) if buckets else 0
        status = "✅" if bucket_count == len(buckets) else "⏳"
        print(f"  {status} {doc_id}: {bucket_count}/{len(buckets)} buckets ({percentage:.1f}%)")
    
    if len(doc_ids) > 10:
        print(f"  ... and {len(doc_ids) - 10} more documents")
    
    # Identify fully processed documents
    fully_processed = []
    partially_processed = []
    not_processed = []
    
    for doc_id in doc_ids:
        bucket_count = sum(1 for bucket in buckets if status_matrix[bucket][doc_id]['present'])
        if bucket_count == len(buckets):
            fully_processed.append(doc_id)
        elif bucket_count > 0:
            partially_processed.append(doc_id)
        else:
            not_processed.append(doc_id)
    
    print(f"\n📈 Overall Status:")
    print(f"  ✅ Fully processed: {len(fully_processed)}/{len(doc_ids)} ({len(fully_processed)/len(doc_ids)*100:.1f}%)")
    print(f"  ⏳ Partially processed: {len(partially_processed)}/{len(doc_ids)} ({len(partially_processed)/len(doc_ids)*100:.1f}%)")
    print(f"  ❌ Not processed: {len(not_processed)}/{len(doc_ids)} ({len(not_processed)/len(doc_ids)*100:.1f}%)")
    
    # Save detailed report
    report_file = f"pipeline_status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'source_bucket': SOURCE_BUCKET,
        'documents_checked': len(doc_ids),
        'buckets_checked': len(buckets),
        'documents': todays_docs,
        'buckets': buckets,
        'status_matrix': status_matrix,
        'summary': {
            'fully_processed': fully_processed,
            'partially_processed': partially_processed,
            'not_processed': not_processed
        }
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Detailed report saved to: {report_file}")

if __name__ == "__main__":
    main()
