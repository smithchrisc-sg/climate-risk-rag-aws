#!/usr/bin/env python3
"""
Cleanup OpenSearch Serverless collections after migration to managed service
"""
import boto3
import time

def list_serverless_collections():
    """List current serverless collections"""
    client = boto3.client('opensearchserverless', region_name='us-east-1')
    
    try:
        response = client.list_collections()
        collections = response.get('collectionSummaries', [])
        
        if not collections:
            print("✅ No serverless collections found")
            return []
        
        print(f"Found {len(collections)} serverless collections:")
        for collection in collections:
            print(f"  - {collection['name']} ({collection['id']}) - Status: {collection['status']}")
        
        return collections
        
    except Exception as e:
        print(f"❌ Error listing collections: {e}")
        return []

def delete_serverless_collection(collection_id, collection_name):
    """Delete a serverless collection"""
    client = boto3.client('opensearchserverless', region_name='us-east-1')
    
    try:
        print(f"🗑️  Deleting collection: {collection_name} ({collection_id})")
        
        response = client.delete_collection(id=collection_id)
        
        print(f"✅ Deletion initiated for {collection_name}")
        print("   Deletion may take a few minutes to complete...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting {collection_name}: {e}")
        return False

def cleanup_all_serverless_collections(confirm=False):
    """Delete all serverless collections"""
    
    collections = list_serverless_collections()
    
    if not collections:
        return True
    
    if not confirm:
        print("\n⚠️  WARNING: This will delete ALL serverless collections!")
        print("   This action cannot be undone.")
        print("   Make sure migration to managed service is complete and tested.")
        print("\nCollections to be deleted:")
        for collection in collections:
            print(f"  - {collection['name']}")
        
        response = input("\nAre you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled")
            return False
    
    success_count = 0
    
    for collection in collections:
        if delete_serverless_collection(collection['id'], collection['name']):
            success_count += 1
            time.sleep(2)  # Brief pause between deletions
    
    print(f"\n✅ Initiated deletion of {success_count}/{len(collections)} collections")
    
    if success_count < len(collections):
        print("⚠️  Some collections could not be deleted. Check the logs above.")
    
    return success_count == len(collections)

def estimate_cost_savings():
    """Estimate monthly cost savings from migration"""
    
    # Current serverless costs (estimated)
    serverless_cost = 2100  # $2,100/month for 2 collections with standby replicas
    
    # Managed service costs
    managed_cost = 268  # $268/month for t3.medium cluster
    
    monthly_savings = serverless_cost - managed_cost
    annual_savings = monthly_savings * 12
    
    print("💰 Cost Savings Estimate")
    print("=" * 30)
    print(f"Current Serverless Cost: ${serverless_cost:,}/month")
    print(f"New Managed Cost:        ${managed_cost:,}/month")
    print(f"Monthly Savings:         ${monthly_savings:,}/month")
    print(f"Annual Savings:          ${annual_savings:,}/year")
    print(f"Savings Percentage:      {(monthly_savings/serverless_cost)*100:.1f}%")

def verify_managed_service_ready():
    """Verify that managed service is ready before cleanup"""
    opensearch_client = boto3.client('opensearch', region_name='us-east-1')
    
    try:
        response = opensearch_client.describe_domain(DomainName='climate-risk-opensearch')
        status = response['DomainStatus']
        
        if not status.get('Created') or status.get('Processing'):
            print("❌ Managed OpenSearch domain is not ready yet")
            print("   Wait for domain creation to complete before cleanup")
            return False
        
        if not status.get('Endpoint'):
            print("❌ Managed OpenSearch domain has no endpoint")
            return False
        
        print(f"✅ Managed OpenSearch domain is ready")
        print(f"   Endpoint: https://{status['Endpoint']}")
        return True
        
    except opensearch_client.exceptions.ResourceNotFoundException:
        print("❌ Managed OpenSearch domain 'climate-risk-opensearch' not found")
        print("   Create the managed domain before cleanup")
        return False
    except Exception as e:
        print(f"❌ Error checking managed domain: {e}")
        return False

def show_cleanup_status():
    """Show current cleanup status"""
    print("OpenSearch Cleanup Status")
    print("=" * 30)
    
    # Check managed service
    if verify_managed_service_ready():
        print("🟢 Managed Service: Ready")
    else:
        print("🔴 Managed Service: Not Ready")
        return
    
    # Check serverless collections
    collections = list_serverless_collections()
    if collections:
        print(f"🟡 Serverless Collections: {len(collections)} remaining")
        print("   Ready for cleanup")
    else:
        print("🟢 Serverless Collections: All cleaned up")
    
    # Show cost savings
    print()
    estimate_cost_savings()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'status':
            show_cleanup_status()
        elif command == 'list':
            list_serverless_collections()
        elif command == 'cleanup':
            if verify_managed_service_ready():
                cleanup_all_serverless_collections()
            else:
                print("❌ Cannot cleanup - managed service not ready")
        elif command == 'force-cleanup':
            cleanup_all_serverless_collections(confirm=True)
        elif command == 'savings':
            estimate_cost_savings()
        else:
            print("Usage: python script.py [status|list|cleanup|force-cleanup|savings]")
    else:
        show_cleanup_status()
