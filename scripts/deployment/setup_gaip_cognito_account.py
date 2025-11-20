#!/usr/bin/env python3
"""
GAIP Cognito Service Account Setup
Creates and configures GAIP service account in Cognito User Pool
"""

import boto3
import json
import argparse
import sys
from typing import Dict, Any


def create_gaip_service_account(user_pool_id: str, client_id: str, 
                               username: str = "gaip-service-account",
                               password: str = None) -> Dict[str, Any]:
    """Create GAIP service account in Cognito User Pool"""
    
    cognito = boto3.client('cognito-idp')
    
    try:
        # Create user
        print(f"Creating user: {username}")
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {'Name': 'email', 'Value': 'gaip-service@solve.global'},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:organization', 'Value': 'GAIP'},
                {'Name': 'custom:customer_tier', 'Value': 'enterprise'},
                {'Name': 'custom:api_quota', 'Value': '10000000'}
            ],
            TemporaryPassword=password or 'TempGAIP123!@#',
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        print(f"✅ User created: {response['User']['Username']}")
        
        # Set permanent password
        if password:
            cognito.admin_set_user_password(
                UserPoolId=user_pool_id,
                Username=username,
                Password=password,
                Permanent=True
            )
            print("✅ Permanent password set")
        
        # Add user to admin group
        try:
            cognito.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=username,
                GroupName='admin'
            )
            print("✅ Added to admin group")
        except Exception as e:
            print(f"⚠️  Could not add to admin group: {e}")
        
        return {
            'username': username,
            'user_pool_id': user_pool_id,
            'client_id': client_id,
            'status': 'created'
        }
        
    except cognito.exceptions.UsernameExistsException:
        print(f"⚠️  User {username} already exists")
        return {
            'username': username,
            'user_pool_id': user_pool_id,
            'client_id': client_id,
            'status': 'exists'
        }
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return {'status': 'error', 'error': str(e)}


def test_authentication(user_pool_id: str, client_id: str, client_secret: str,
                       username: str, password: str) -> Dict[str, Any]:
    """Test authentication and get JWT tokens"""
    
    cognito = boto3.client('cognito-idp')
    
    try:
        # Calculate SECRET_HASH
        import hmac
        import hashlib
        import base64
        
        message = username + client_id
        secret_hash = base64.b64encode(
            hmac.new(
                client_secret.encode(),
                message.encode(),
                digestmod=hashlib.sha256
            ).digest()
        ).decode()
        
        # Authenticate
        response = cognito.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': secret_hash
            }
        )
        
        auth_result = response['AuthenticationResult']
        
        print("✅ Authentication successful!")
        print(f"Access Token: {auth_result['AccessToken'][:50]}...")
        print(f"ID Token: {auth_result['IdToken'][:50]}...")
        print(f"Token Type: {auth_result['TokenType']}")
        print(f"Expires In: {auth_result['ExpiresIn']} seconds")
        
        return {
            'status': 'success',
            'access_token': auth_result['AccessToken'],
            'id_token': auth_result['IdToken'],
            'refresh_token': auth_result.get('RefreshToken'),
            'expires_in': auth_result['ExpiresIn']
        }
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return {'status': 'error', 'error': str(e)}


def get_client_secret(user_pool_id: str, client_id: str) -> str:
    """Get client secret for the User Pool Client"""
    
    cognito = boto3.client('cognito-idp')
    
    try:
        response = cognito.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id
        )
        
        client_secret = response['UserPoolClient'].get('ClientSecret')
        if not client_secret:
            raise ValueError("Client secret not found - ensure client was created with generate_secret=True")
        
        return client_secret
        
    except Exception as e:
        print(f"❌ Error getting client secret: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description='Setup GAIP Cognito service account')
    parser.add_argument('--user-pool-id', required=True, help='Cognito User Pool ID')
    parser.add_argument('--client-id', required=True, help='Cognito User Pool Client ID')
    parser.add_argument('--username', default='gaip-service-account', help='Username for service account')
    parser.add_argument('--password', help='Password for service account (will prompt if not provided)')
    parser.add_argument('--test-auth', action='store_true', help='Test authentication after creation')
    
    args = parser.parse_args()
    
    # Get password if not provided
    if not args.password:
        import getpass
        args.password = getpass.getpass("Enter password for GAIP service account: ")
    
    print("=== GAIP Cognito Service Account Setup ===")
    print(f"User Pool ID: {args.user_pool_id}")
    print(f"Client ID: {args.client_id}")
    print(f"Username: {args.username}")
    print()
    
    # Create service account
    result = create_gaip_service_account(
        args.user_pool_id,
        args.client_id, 
        args.username,
        args.password
    )
    
    if result['status'] == 'error':
        sys.exit(1)
    
    # Test authentication if requested
    if args.test_auth:
        print("\n=== Testing Authentication ===")
        try:
            client_secret = get_client_secret(args.user_pool_id, args.client_id)
            test_result = test_authentication(
                args.user_pool_id,
                args.client_id,
                client_secret,
                args.username,
                args.password
            )
            
            if test_result['status'] == 'success':
                print(f"\n🎉 GAIP service account ready!")
                print(f"Use the ID token for API authentication:")
                print(f"Authorization: Bearer {test_result['id_token'][:50]}...")
            
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
    
    print(f"\n✅ Setup complete for user: {args.username}")


if __name__ == "__main__":
    main()
