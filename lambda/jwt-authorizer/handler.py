import json
import jwt
import os
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """JWT Token Authorizer for GAIP API - supports API keys"""
    
    try:
        # Extract token from Authorization header
        token = event['authorizationToken']
        if not token.startswith('Bearer '):
            raise ValueError('Invalid token format')
        
        token = token[7:]  # Remove 'Bearer ' prefix
        
        # Use dev secret (in prod, get from Secrets Manager)
        secret = os.environ.get('JWT_SECRET', 'dev-test-secret-key-change-for-production')
        
        # Decode and validate JWT
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        # Extract user information
        user_id = payload.get('sub')
        organization = payload.get('org')
        roles = payload.get('roles', [])
        token_type = payload.get('type', 'session')
        
        # Validate required fields
        if not user_id or not organization:
            raise ValueError('Invalid token payload')
        
        # Check if user has search permission
        if 'search' not in roles:
            raise ValueError('Insufficient permissions')
        
        # Generate policy
        policy = generate_policy(user_id, 'Allow', event['methodArn'])
        
        # Add user context
        policy['context'] = {
            'userId': user_id,
            'organization': organization,
            'roles': json.dumps(roles),
            'tokenType': token_type
        }
        
        return policy
        
    except jwt.ExpiredSignatureError:
        raise Exception('Token expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')
    except Exception as e:
        print(f"Authorization error: {str(e)}")
        raise Exception('Unauthorized')

def generate_policy(principal_id: str, effect: str, resource: str) -> Dict[str, Any]:
    """Generate IAM policy for API Gateway"""
    return {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
