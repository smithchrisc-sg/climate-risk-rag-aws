#!/usr/bin/env python3
"""
Create OpenSearch managed domain for climate risk RAG system
"""
import boto3
import json
import time

def create_opensearch_domain():
    """Create the OpenSearch managed domain"""
    client = boto3.client('opensearch', region_name='us-east-1')
    
    domain_config = {
        'DomainName': 'climate-risk-opensearch',
        'EngineVersion': 'OpenSearch_2.11',
        
        # Cluster configuration
        'ClusterConfig': {
            'InstanceType': 't3.small.search',
            'InstanceCount': 2,
            'DedicatedMasterEnabled': True,
            'MasterInstanceType': 't3.small.search',
            'MasterInstanceCount': 3,
            'ZoneAwarenessEnabled': True,
            'ZoneAwarenessConfig': {
                'AvailabilityZoneCount': 2
            }
        },
        
        # Storage configuration
        'EBSOptions': {
            'EBSEnabled': True,
            'VolumeType': 'gp3',
            'VolumeSize': 20,
            'Iops': 3000,
            'Throughput': 125
        },
        
        # Network configuration
        'VPCOptions': {
            'SubnetIds': [
                'subnet-03d8bd6cf3491f38c',  # Private subnet 1
                'subnet-0c0be1dd59f70f70e'   # Private subnet 2
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
        
        # Access policy
        'AccessPolicies': json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::861276078413:role/document-processing-lambda-role"
                    },
                    "Action": "es:*",
                    "Resource": "arn:aws:es:us-east-1:861276078413:domain/climate-risk-opensearch/*"
                }
            ]
        }),
        
        # Advanced options
        'AdvancedOptions': {
            'rest.action.multi.allow_explicit_index': 'true',
            'indices.fielddata.cache.size': '20%',
            'indices.query.bool.max_clause_count': '1024'
        },
        
        # Auto-tune
        'AutoTuneOptions': {
            'DesiredState': 'ENABLED'
        }
    }
    
    try:
        print("Creating OpenSearch domain: climate-risk-opensearch")
        response = client.create_domain(**domain_config)
        
        print(f"Domain creation initiated:")
        print(f"  Domain ARN: {response['DomainStatus']['ARN']}")
        print(f"  Status: {response['DomainStatus']['Processing']}")
        print(f"  Endpoint: {response['DomainStatus'].get('Endpoint', 'Not yet available')}")
        
        print("\nDomain creation will take 15-20 minutes...")
        print("Monitor progress with: aws opensearch describe-domain --domain-name climate-risk-opensearch")
        
        return response
        
    except Exception as e:
        print(f"Error creating domain: {e}")
        return None

def check_domain_status():
    """Check the status of domain creation"""
    client = boto3.client('opensearch', region_name='us-east-1')
    
    try:
        response = client.describe_domain(DomainName='climate-risk-opensearch')
        status = response['DomainStatus']
        
        print(f"Domain Status: {status['Processing']}")
        print(f"Created: {status['Created']}")
        print(f"Endpoint: {status.get('Endpoint', 'Not available')}")
        
        if status.get('Endpoint'):
            print(f"\n✅ Domain is ready!")
            print(f"Endpoint: https://{status['Endpoint']}")
        else:
            print(f"\n⏳ Domain still creating... check again in 5 minutes")
            
    except Exception as e:
        print(f"Error checking domain status: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        check_domain_status()
    else:
        create_opensearch_domain()
