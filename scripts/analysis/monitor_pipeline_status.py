#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Pipeline Status Monitor
Monitor the Climate Risk RAG pipeline processing status
"""

import boto3
import json
from datetime import datetime, timedelta

def check_s3_bucket_contents():
    """Check contents of key S3 buckets to see processing progress"""
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    buckets_to_check = {
        'source': 'solve-global-kr-dl-source-documents-861276078413-us-east-1',
        'text': 'solve-global-kr-dl-text-861276078413-us-east-1', 
        'chunks': 'solve-global-kr-dl-chunks-861276078413-us-east-1',
        'nlp': 'solve-global-kr-dl-ner-results-861276078413-us-east-1'
    }
    
    print("PIPELINE STATUS MONITORING")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    for stage, bucket_name in buckets_to_check.items():
        print(f"{stage.upper()} BUCKET: {bucket_name}")
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
            
            if response.get('KeyCount', 0) > 0:
                print(f"  Total objects: {response['KeyCount']}")
                
                # Check for recent files (last 24 hours)
                recent_files = []
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                for obj in response.get('Contents', []):
                    if obj['LastModified'].replace(tzinfo=None) > cutoff_time:
                        recent_files.append(obj)
                
                if recent_files:
                    print(f"  Recent files (24h): {len(recent_files)}")
                    # Show most recent files
                    recent_files.sort(key=lambda x: x['LastModified'], reverse=True)
                    for file in recent_files[:5]:
                        print(f"    - {file['Key']} ({file['LastModified'].strftime('%Y-%m-%d %H:%M:%S')})")
                else:
                    print(f"  Recent files (24h): 0")
            else:
                print(f"  Total objects: 0")
                
        except Exception as e:
            print(f"  ERROR: {e}")
        print()

def check_lambda_recent_activity():
    """Check recent Lambda function activity"""
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    # Key Lambda functions to monitor
    functions = [
        'solve-global-kr-pipeline-test-function',
        'solve-global-kr-textextractor-processor',
        'text-chunker-pipeline',
        'nlp-processor'
    ]
    
    print("LAMBDA FUNCTION ACTIVITY (Last 2 hours)")
    print("=" * 50)
    
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (2 * 60 * 60 * 1000)  # 2 hours ago
    
    for function_name in functions:
        print(f"\n{function_name}:")
        try:
            log_group = f"/aws/lambda/{function_name}"
            
            # Get recent log events
            response = logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                limit=10
            )
            
            events = response.get('events', [])
            if events:
                print(f"  Recent events: {len(events)}")
                # Show key events
                for event in events[-3:]:  # Last 3 events
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].strip()[:100]  # Truncate long messages
                    print(f"    [{timestamp.strftime('%H:%M:%S')}] {message}")
            else:
                print(f"  Recent events: 0")
                
        except Exception as e:
            print(f"  ERROR: {e}")

def check_recent_costs():
    """Check recent AWS costs"""
    ce_client = boto3.client('ce', region_name='us-east-1')
    
    print("\nRECENT COST ANALYSIS")
    print("=" * 50)
    
    try:
        # Get costs for last 3 days
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        print(f"Cost period: {start_date} to {end_date}")
        
        # Aggregate costs by service
        service_costs = {}
        for result in response['ResultsByTime']:
            date = result['TimePeriod']['Start']
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                if service not in service_costs:
                    service_costs[service] = 0
                service_costs[service] += cost
        
        # Show top services by cost
        sorted_costs = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
        print("\nTop services by cost:")
        for service, cost in sorted_costs[:10]:
            if cost > 0.01:  # Only show costs > $0.01
                print(f"  {service}: ${cost:.4f}")
                
    except Exception as e:
        print(f"ERROR checking costs: {e}")

def main():
    """Main monitoring function"""
    print("CLIMATE RISK RAG PIPELINE MONITORING")
    print("=" * 60)
    print()
    
    # Check S3 bucket contents
    check_s3_bucket_contents()
    
    # Check Lambda activity
    check_lambda_recent_activity()
    
    # Check recent costs
    check_recent_costs()
    
    print("\nMONITORING COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
