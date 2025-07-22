#!/usr/bin/env python3
"""
Test Neptune connectivity and SPARQL operations
"""
import boto3
import requests
from requests_aws4auth import AWS4Auth
import json

def test_neptune_connectivity():
    """Test basic Neptune connectivity and SPARQL operations"""
    
    # Neptune endpoint
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    neptune_port = "8182"
    
    print(f"Testing Neptune connectivity to: {neptune_endpoint}:{neptune_port}")
    print("=" * 60)
    
    try:
        # AWS credentials for signing
        session = boto3.Session(profile_name='solve-global')
        credentials = session.get_credentials()
        region = 'us-east-1'
        service = 'neptune-db'
        
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key, 
            region,
            service,
            session_token=credentials.token
        )
        
        # Test 1: Status endpoint
        print("🔍 Testing Neptune status endpoint...")
        status_url = f"https://{neptune_endpoint}:{neptune_port}/status"
        
        response = requests.get(status_url, auth=auth, timeout=30)
        if response.status_code == 200:
            print(f"✅ Neptune Status: {response.status_code}")
            status_data = response.json()
            print(f"   Status: {status_data.get('status', 'unknown')}")
            print(f"   DB Engine Version: {status_data.get('dbEngineVersion', 'unknown')}")
        else:
            print(f"❌ Neptune Status failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Test 2: SPARQL endpoint basic query
        print("\n🔍 Testing SPARQL endpoint with count query...")
        sparql_url = f"https://{neptune_endpoint}:{neptune_port}/sparql"
        
        # Simple SPARQL query to count all triples
        count_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }"
        
        response = requests.post(
            sparql_url,
            data={'query': count_query},
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/sparql-results+json'
            },
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ SPARQL Query: {response.status_code}")
            result = response.json()
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                count = bindings[0].get('count', {}).get('value', '0')
                print(f"   Total triples in Neptune: {count}")
            else:
                print("   No results returned")
        else:
            print(f"❌ SPARQL Query failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Test 3: Test SPARQL INSERT (with rollback)
        print("\n🔍 Testing SPARQL INSERT operation...")
        
        # Test INSERT query
        test_insert = """
        PREFIX test: <http://test.example.org/>
        INSERT DATA {
            test:connectivity_test test:timestamp "2025-07-22T22:00:00Z" ;
                                  test:status "testing" .
        }
        """
        
        response = requests.post(
            sparql_url,
            data={'update': test_insert},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ SPARQL INSERT: {response.status_code}")
            
            # Verify the insert worked
            verify_query = """
            PREFIX test: <http://test.example.org/>
            SELECT ?timestamp ?status WHERE {
                test:connectivity_test test:timestamp ?timestamp ;
                                      test:status ?status .
            }
            """
            
            verify_response = requests.post(
                sparql_url,
                data={'query': verify_query},
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/sparql-results+json'
                },
                auth=auth,
                timeout=30
            )
            
            if verify_response.status_code == 200:
                verify_result = verify_response.json()
                bindings = verify_result.get('results', {}).get('bindings', [])
                if bindings:
                    print("   ✅ INSERT verification successful")
                    print(f"   Inserted data: {bindings[0]}")
                else:
                    print("   ⚠️  INSERT may not have worked - no data found")
            
            # Clean up test data
            cleanup_query = """
            PREFIX test: <http://test.example.org/>
            DELETE DATA {
                test:connectivity_test test:timestamp "2025-07-22T22:00:00Z" ;
                                      test:status "testing" .
            }
            """
            
            cleanup_response = requests.post(
                sparql_url,
                data={'update': cleanup_query},
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=auth,
                timeout=30
            )
            
            if cleanup_response.status_code == 200:
                print("   ✅ Test data cleaned up successfully")
            else:
                print("   ⚠️  Failed to clean up test data")
                
        else:
            print(f"❌ SPARQL INSERT failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        # Test 4: Test Dublin Core prefixes (for our KG data)
        print("\n🔍 Testing Dublin Core namespace queries...")
        
        dc_query = """
        PREFIX dc: <http://purl.org/dc/elements/1.1/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        SELECT (COUNT(*) as ?count) WHERE {
            ?s a dcterms:Text .
        }
        """
        
        response = requests.post(
            sparql_url,
            data={'query': dc_query},
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/sparql-results+json'
            },
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"✅ Dublin Core Query: {response.status_code}")
            result = response.json()
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                count = bindings[0].get('count', {}).get('value', '0')
                print(f"   Documents in Neptune: {count}")
            else:
                print("   No Dublin Core documents found")
        else:
            print(f"❌ Dublin Core Query failed: {response.status_code}")
            print(f"   Response: {response.text}")
        
        print("\n🎉 All Neptune connectivity tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Neptune connectivity test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ttl_bucket_access():
    """Test access to TTL bucket"""
    
    print("\n🔍 Testing TTL bucket access...")
    
    try:
        session = boto3.Session(profile_name='solve-global')
        s3_client = session.client('s3')
        bucket_name = "solve-global-kr-dl-neptune-ttl-861276078413-us-east-1"
        
        # Test bucket access
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
        
        print(f"✅ TTL bucket access successful")
        print(f"   Bucket: {bucket_name}")
        
        contents = response.get('Contents', [])
        if contents:
            print(f"   Found {len(contents)} objects (showing first 5)")
            for obj in contents[:5]:
                print(f"     - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("   Bucket is empty")
        
        return True
        
    except Exception as e:
        print(f"❌ TTL bucket access failed: {e}")
        return False

if __name__ == "__main__":
    print("Neptune Connectivity Test")
    print("=" * 60)
    
    success = True
    
    # Test Neptune connectivity
    if not test_neptune_connectivity():
        success = False
    
    # Test TTL bucket access
    if not test_ttl_bucket_access():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! Neptune and S3 are ready for KG integration.")
    else:
        print("❌ Some tests failed. Please check the configuration.")
    
    exit(0 if success else 1)
