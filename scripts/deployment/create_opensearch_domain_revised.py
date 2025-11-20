#!/usr/bin/env python3
"""
Create OpenSearch managed domain for climate risk RAG system
Revised for chunk-based vectors (4M chunks expected)
"""
import boto3
import json

def create_opensearch_domain():
    """Create the OpenSearch managed domain with proper sizing"""
    client = boto3.client('opensearch', region_name='us-east-1')
    
    domain_config = {
        'DomainName': 'climate-risk-opensearch',
        'EngineVersion': 'OpenSearch_2.11',
        
        # Cluster configuration - sized for 4M chunks
        'ClusterConfig': {
            'InstanceType': 't3.medium.search',  # Upgraded for vector workload
            'InstanceCount': 2,
            'DedicatedMasterEnabled': True,
            'MasterInstanceType': 't3.small.search',
            'MasterInstanceCount': 3,
            'ZoneAwarenessEnabled': True,
            'ZoneAwarenessConfig': {
                'AvailabilityZoneCount': 2
            }
        },
        
        # Storage configuration - increased for vector data
        'EBSOptions': {
            'EBSEnabled': True,
            'VolumeType': 'gp3',
            'VolumeSize': 50,  # 50GB per node for 4M chunks
            'Iops': 3000,
            'Throughput': 125
        },
        
        # Network configuration
        'VPCOptions': {
            'SubnetIds': [
                'subnet-03d8bd6cf3491f38c',  # Private subnet 1a
                'subnet-0c0be1dd59f70f70e'   # Private subnet 1b
            ],
            'SecurityGroupIds': [
                'sg-0c9e10b9cfb4c9eb0'  # Same as Lambda functions
            ]
        },
        
        # Security configuration
        'EncryptionAtRestOptions': {
            'Enabled': True
        },
        'NodeToNodeEncryptionOptions': {
            'Enabled': True
        },
        'DomainEndpointOptions': {
            'EnforceHTTPS': True,
            'TLSSecurityPolicy': 'Policy-Min-TLS-1-2-2019-07'
        },
        
        # Access policy for Lambda functions
        'AccessPolicies': json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": [
                            "arn:aws:iam::861276078413:role/document-processing-lambda-role",
                            "arn:aws:iam::861276078413:role/NeptuneNotebookRole"
                        ]
                    },
                    "Action": "es:*",
                    "Resource": "arn:aws:es:us-east-1:861276078413:domain/climate-risk-opensearch/*"
                }
            ]
        }),
        
        # Advanced options optimized for vector search
        'AdvancedOptions': {
            'rest.action.multi.allow_explicit_index': 'true',
            'indices.fielddata.cache.size': '30%',  # Increased for vectors
            'indices.query.bool.max_clause_count': '2048',  # Increased
            'cluster.max_shards_per_node': '1000'
        },
        
        # Auto-tune for performance optimization
        'AutoTuneOptions': {
            'DesiredState': 'ENABLED'
        }
    }
    
    try:
        print("Creating OpenSearch domain: climate-risk-opensearch")
        print("Configuration:")
        print(f"  Instance Type: {domain_config['ClusterConfig']['InstanceType']}")
        print(f"  Instance Count: {domain_config['ClusterConfig']['InstanceCount']}")
        print(f"  Storage per Node: {domain_config['EBSOptions']['VolumeSize']}GB")
        print(f"  Expected Capacity: 4M chunks (~26GB data)")
        
        response = client.create_domain(**domain_config)
        
        print(f"\n✅ Domain creation initiated:")
        print(f"  Domain ARN: {response['DomainStatus']['ARN']}")
        print(f"  Status: Processing")
        
        print(f"\n⏳ Domain creation will take 15-20 minutes...")
        print(f"Monitor with: aws opensearch describe-domain --domain-name climate-risk-opensearch --profile solve-global")
        
        return response
        
    except client.exceptions.ResourceAlreadyExistsException:
        print("❌ Domain already exists. Use 'delete' command first if you want to recreate.")
        return None
    except Exception as e:
        print(f"❌ Error creating domain: {e}")
        return None

def delete_opensearch_domain():
    """Delete the OpenSearch domain"""
    client = boto3.client('opensearch', region_name='us-east-1')
    
    try:
        print("⚠️  Deleting OpenSearch domain: climate-risk-opensearch")
        response = client.delete_domain(DomainName='climate-risk-opensearch')
        print("✅ Domain deletion initiated")
        return response
    except Exception as e:
        print(f"❌ Error deleting domain: {e}")
        return None

def check_domain_status():
    """Check the status of domain creation"""
    client = boto3.client('opensearch', region_name='us-east-1')
    
    try:
        response = client.describe_domain(DomainName='climate-risk-opensearch')
        status = response['DomainStatus']
        
        print(f"Domain Status:")
        print(f"  Processing: {status.get('Processing', 'Unknown')}")
        print(f"  Created: {status.get('Created', False)}")
        print(f"  Deleted: {status.get('Deleted', False)}")
        
        if status.get('Endpoint'):
            print(f"  Endpoint: https://{status['Endpoint']}")
            print(f"\n✅ Domain is ready for use!")
        else:
            print(f"  Endpoint: Not yet available")
            print(f"\n⏳ Domain still creating... check again in 5 minutes")
            
        # Show configuration
        cluster_config = status.get('ClusterConfig', {})
        ebs_options = status.get('EBSOptions', {})
        
        print(f"\nConfiguration:")
        print(f"  Instance Type: {cluster_config.get('InstanceType', 'Unknown')}")
        print(f"  Instance Count: {cluster_config.get('InstanceCount', 'Unknown')}")
        print(f"  Storage: {ebs_options.get('VolumeSize', 'Unknown')}GB {ebs_options.get('VolumeType', '')}")
            
    except client.exceptions.ResourceNotFoundException:
        print("❌ Domain 'climate-risk-opensearch' not found")
    except Exception as e:
        print(f"❌ Error checking domain status: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'status':
            check_domain_status()
        elif command == 'delete':
            delete_opensearch_domain()
        elif command == 'create':
            create_opensearch_domain()
        else:
            print("Usage: python script.py [create|status|delete]")
    else:
        create_opensearch_domain()
