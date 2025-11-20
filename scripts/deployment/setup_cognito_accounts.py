#!/usr/bin/env python3
"""
Cognito Service Accounts Setup
Creates service accounts for GAIP and SolveGlobal in Cognito User Pool
"""

import boto3
import json
import argparse
import sys
from typing import Dict, Any, List


def create_service_account(user_pool_id: str, client_id: str, 
                          username: str, organization: str, 
                          customer_tier: str, password: str) -> Dict[str, Any]:
    """Create service account in Cognito User Pool"""
    
    cognito = boto3.client('cognito-idp')
    
    try:
        # Create user
        print(f"Creating user: {username} ({organization})")
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {'Name': 'email', 'Value': username},  # Use username as email since it's already an email
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:organization', 'Value': organization},
                {'Name': 'custom:customer_tier', 'Value': customer_tier},
                {'Name': 'custom:api_quota', 'Value': '10000000'}
            ],
            TemporaryPassword=password,
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        print(f"✅ User created: {response['User']['Username']}")
        
        # Set permanent password
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
            'organization': organization,
            'user_pool_id': user_pool_id,
            'client_id': client_id,
            'status': 'created'
        }
        
    except cognito.exceptions.UsernameExistsException:
        print(f"⚠️  User {username} already exists")
        return {
            'username': username,
            'organization': organization,
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
        
        print(f"✅ Authentication successful for {username}!")
        print(f"ID Token: {auth_result['IdToken'][:50]}...")
        print(f"Expires In: {auth_result['ExpiresIn']} seconds")
        
        return {
            'status': 'success',
            'username': username,
            'access_token': auth_result['AccessToken'],
            'id_token': auth_result['IdToken'],
            'refresh_token': auth_result.get('RefreshToken'),
            'expires_in': auth_result['ExpiresIn']
        }
        
    except Exception as e:
        print(f"❌ Authentication failed for {username}: {e}")
        return {'status': 'error', 'username': username, 'error': str(e)}


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


def setup_default_accounts(user_pool_id: str, client_id: str, 
                          gaip_password: str, solveglobal_password: str) -> List[Dict[str, Any]]:
    """Set up both GAIP and SolveGlobal service accounts"""
    
    accounts = [
        {
            'username': 'gaip-service@gaip.com',
            'organization': 'GAIP',
            'customer_tier': 'enterprise',
            'password': gaip_password
        },
        {
            'username': 'solveglobal-service@solveglobal.com', 
            'organization': 'SolveGlobal',
            'customer_tier': 'internal',
            'password': solveglobal_password
        }
    ]
    
    results = []
    
    for account in accounts:
        print(f"\n=== Creating {account['organization']} Account ===")
        result = create_service_account(
            user_pool_id,
            client_id,
            account['username'],
            account['organization'],
            account['customer_tier'],
            account['password']
        )
        results.append(result)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Setup Cognito service accounts for GAIP and SolveGlobal')
    parser.add_argument('--user-pool-id', required=True, help='Cognito User Pool ID')
    parser.add_argument('--client-id', required=True, help='Cognito User Pool Client ID')
    parser.add_argument('--gaip-password', help='Password for GAIP service account')
    parser.add_argument('--solveglobal-password', help='Password for SolveGlobal service account')
    parser.add_argument('--test-auth', action='store_true', help='Test authentication after creation')
    parser.add_argument('--single-account', choices=['gaip', 'solveglobal'], help='Create only one account')
    
    args = parser.parse_args()
    
    # Get passwords if not provided
    if not args.gaip_password and (not args.single_account or args.single_account == 'gaip'):
        import getpass
        args.gaip_password = getpass.getpass("Enter password for GAIP service account: ")
    
    if not args.solveglobal_password and (not args.single_account or args.single_account == 'solveglobal'):
        import getpass
        args.solveglobal_password = getpass.getpass("Enter password for SolveGlobal service account: ")
    
    print("=== Cognito Service Accounts Setup ===")
    print(f"User Pool ID: {args.user_pool_id}")
    print(f"Client ID: {args.client_id}")
    print()
    
    # Create accounts
    if args.single_account == 'gaip':
        result = create_service_account(
            args.user_pool_id, args.client_id,
            'gaip-service@gaip.com', 'GAIP', 'enterprise', args.gaip_password
        )
        results = [result]
    elif args.single_account == 'solveglobal':
        result = create_service_account(
            args.user_pool_id, args.client_id,
            'solveglobal-service@solveglobal.com', 'SolveGlobal', 'internal', args.solveglobal_password
        )
        results = [result]
    else:
        results = setup_default_accounts(
            args.user_pool_id, args.client_id,
            args.gaip_password, args.solveglobal_password
        )
    
    # Check for errors
    if any(r['status'] == 'error' for r in results):
        print("❌ Some accounts failed to create")
        sys.exit(1)
    
    # Test authentication if requested
    if args.test_auth:
        print("\n=== Testing Authentication ===")
        try:
            client_secret = get_client_secret(args.user_pool_id, args.client_id)
            
            test_accounts = []
            if args.single_account == 'gaip' or not args.single_account:
                test_accounts.append(('gaip-service@gaip.com', args.gaip_password))
            if args.single_account == 'solveglobal' or not args.single_account:
                test_accounts.append(('solveglobal-service@solveglobal.com', args.solveglobal_password))
            
            for username, password in test_accounts:
                print(f"\nTesting {username}...")
                test_result = test_authentication(
                    args.user_pool_id,
                    args.client_id,
                    client_secret,
                    username,
                    password
                )
                
                if test_result['status'] == 'success':
                    print(f"🎉 {username} ready for API access!")
                    print(f"Authorization: Bearer {test_result['id_token'][:50]}...")
            
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
    
    print(f"\n✅ Setup complete!")
    print("Both GAIP and SolveGlobal can now authenticate to the API using their respective service accounts.")


if __name__ == "__main__":
    main()
