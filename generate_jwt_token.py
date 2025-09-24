#!/usr/bin/env python3
"""
JWT Token Generator for GAIP API
Generates bearer tokens compatible with the gaip-jwt-authorizer Lambda
"""

import jwt
import json
from datetime import datetime, timedelta
import sys

def generate_token(user_id="test-user", organization="solve-global", roles=None, hours=24):
    """Generate a JWT token for API access"""
    
    if roles is None:
        roles = ["search", "admin"]
    
    # Use the same secret as the authorizer (dev secret)
    secret = "dev-test-secret-key-change-for-production"
    
    # Create payload
    now = datetime.utcnow()
    payload = {
        'sub': user_id,                    # User ID
        'org': organization,               # Organization
        'roles': roles,                    # User roles
        'type': 'session',                 # Token type
        'iat': now,                        # Issued at
        'exp': now + timedelta(hours=hours) # Expires in X hours
    }
    
    # Generate token
    token = jwt.encode(payload, secret, algorithm='HS256')
    
    return token

def main():
    """Generate and display a JWT token"""
    
    # Parse command line arguments
    user_id = sys.argv[1] if len(sys.argv) > 1 else "test-user"
    organization = sys.argv[2] if len(sys.argv) > 2 else "solve-global"
    hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    
    # Generate token
    token = generate_token(user_id, organization, hours=hours)
    
    print("=" * 60)
    print("GAIP API JWT Token Generated")
    print("=" * 60)
    print(f"User ID: {user_id}")
    print(f"Organization: {organization}")
    print(f"Roles: ['search', 'admin']")
    print(f"Valid for: {hours} hours")
    print("=" * 60)
    print("Bearer Token:")
    print(token)
    print("=" * 60)
    print("\nUsage in API calls:")
    print(f"Authorization: Bearer {token}")
    print("=" * 60)

if __name__ == "__main__":
    main()
