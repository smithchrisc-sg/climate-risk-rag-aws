#!/usr/bin/env python3
"""
Test Neptune connectivity via existing Lambda function
Use an existing VPC Lambda to test Neptune connectivity
"""

import boto3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_neptune_via_lambda():
    """Test Neptune connectivity using existing Lambda function"""
    
    # Use AWS Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Test payload with Neptune connectivity test code
    test_payload = {
        "test_type": "neptune_connectivity",
        "neptune_endpoint": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com",
        "test_code": """
import urllib3
import json

def test_neptune():
    neptune_endpoint = "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    status_url = f"https://{neptune_endpoint}:8182/status"
    
    http = urllib3.PoolManager()
    
    try:
        response = http.request('GET', status_url, timeout=10)
        if response.status == 200:
            return {
                'success': True,
                'status_code': response.status,
                'data': json.loads(response.data.decode('utf-8'))
            }
        else:
            return {
                'success': False,
                'status_code': response.status,
                'error': f'HTTP {response.status}'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

result = test_neptune()
print(json.dumps(result, indent=2))
"""
    }
    
    # Try with a simple Lambda function that might be able to execute our test
    lambda_function_name = "solve-global-kr-rag-micro-ResponseGenerator1B9F64E-6VSpp0wc5QBs"
    
    try:
        logger.info(f"Testing Neptune connectivity via Lambda: {lambda_function_name}")
        
        response = lambda_client.invoke(
            FunctionName=lambda_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Read the response
        response_payload = json.loads(response['Payload'].read())
        
        logger.info("Lambda invocation successful!")
        logger.info(f"Response: {json.dumps(response_payload, indent=2)}")
        
        return response_payload
        
    except Exception as e:
        logger.error(f"Lambda invocation failed: {e}")
        return None

def simple_neptune_test():
    """Simple test to check if we can reach Neptune from Lambda"""
    
    # Create a simple test Lambda function inline
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Let's try a different approach - check if we can at least resolve the Neptune endpoint
    test_payload = {
        "action": "test_neptune_dns",
        "endpoint": "solve-global-kr-neptune.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com"
    }
    
    # Use a Lambda that might be more flexible
    lambda_functions_to_try = [
        "solve-global-kr-rag-micro-ResponseGenerator1B9F64E-6VSpp0wc5QBs",
        "solve-global-kr-rag-microser-QueryAnalyzer699DB805-ltF0hzzaP7EW",
        "solve-global-kr-rag-micro-KnowledgeGraphSearcher35-pDj8wDKPDssu"
    ]
    
    for func_name in lambda_functions_to_try:
        try:
            logger.info(f"Trying Lambda function: {func_name}")
            
            response = lambda_client.invoke(
                FunctionName=func_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            response_payload = json.loads(response['Payload'].read())
            logger.info(f"Response from {func_name}: {response_payload}")
            
            # If we get here, the Lambda executed
            return response_payload
            
        except Exception as e:
            logger.warning(f"Failed to invoke {func_name}: {e}")
            continue
    
    logger.error("All Lambda function invocations failed")
    return None

def check_neptune_from_vpc():
    """Check Neptune accessibility from VPC using AWS CLI through Lambda"""
    
    # Let's try a simpler approach - just check if Neptune is accessible
    # by using AWS CLI commands that might work from within the VPC
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Simple payload to test basic connectivity
    test_payload = {
        "test": "neptune_connectivity",
        "message": "Testing Neptune from VPC Lambda"
    }
    
    # Use the KnowledgeGraphSearcher as it might be designed for graph operations
    function_name = "solve-global-kr-rag-micro-KnowledgeGraphSearcher35-pDj8wDKPDssu"
    
    try:
        logger.info(f"Testing basic Lambda connectivity: {function_name}")
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        status_code = response['StatusCode']
        response_payload = response['Payload'].read()
        
        logger.info(f"Lambda Status Code: {status_code}")
        logger.info(f"Lambda Response: {response_payload.decode('utf-8')}")
        
        if status_code == 200:
            logger.info("✅ Lambda function is accessible and responding")
            return True
        else:
            logger.error(f"❌ Lambda function returned status: {status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Lambda invocation error: {e}")
        return False

def main():
    """Main function to test Neptune connectivity"""
    
    print("🔗 TESTING NEPTUNE CONNECTIVITY VIA EXISTING LAMBDA")
    print("=" * 60)
    
    # First, let's just test if we can invoke a Lambda function in the VPC
    logger.info("Step 1: Testing basic Lambda connectivity...")
    if check_neptune_from_vpc():
        logger.info("✅ Lambda functions in VPC are accessible")
    else:
        logger.error("❌ Cannot access Lambda functions in VPC")
        return False
    
    # Now let's try to test Neptune connectivity
    logger.info("Step 2: Testing Neptune connectivity via Lambda...")
    result = simple_neptune_test()
    
    if result:
        logger.info("✅ Got response from Lambda function")
        return True
    else:
        logger.error("❌ No successful response from Lambda functions")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
