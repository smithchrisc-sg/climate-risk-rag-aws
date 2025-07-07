#!/usr/bin/env python3
"""
Script to retrieve database credentials and construct DATABASE_URL
"""

import boto3
import json
import sys

def find_database_secret():
    """Find the database secret in Secrets Manager"""
    # Known secret name from CloudFormation stack
    known_secret_name = "DatabaseSecret86DBB7B3-Z8CSRvy8A8bp"
    
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        # First try the known secret name
        try:
            response = secrets_client.describe_secret(SecretId=known_secret_name)
            print(f"✅ Found known database secret: {known_secret_name}")
            return known_secret_name
        except secrets_client.exceptions.ResourceNotFoundException:
            print(f"⚠️  Known secret '{known_secret_name}' not found, searching for alternatives...")
        
        # Fallback: List all secrets and search
        response = secrets_client.list_secrets()
        
        # Look for database-related secrets
        database_secrets = []
        for secret in response['SecretList']:
            secret_name = secret['Name']
            if any(keyword in secret_name.lower() for keyword in ['database', 'db', 'postgres', 'climate', 'rag']):
                database_secrets.append(secret)
        
        if not database_secrets:
            print("❌ No database secrets found in Secrets Manager")
            print(f"💡 Expected secret name: {known_secret_name}")
            return None
        
        print(f"🔍 Found {len(database_secrets)} potential database secret(s):")
        for i, secret in enumerate(database_secrets):
            print(f"  {i+1}. {secret['Name']} - {secret.get('Description', 'No description')}")
        
        # If only one secret, use it; otherwise ask user to choose
        if len(database_secrets) == 1:
            chosen_secret = database_secrets[0]
        else:
            while True:
                try:
                    choice = int(input(f"\nChoose secret (1-{len(database_secrets)}): ")) - 1
                    if 0 <= choice < len(database_secrets):
                        chosen_secret = database_secrets[choice]
                        break
                    else:
                        print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a number.")
        
        return chosen_secret['Name']
        
    except Exception as e:
        print(f"❌ Error accessing Secrets Manager: {str(e)}")
        print(f"💡 Try using the known secret name: {known_secret_name}")
        return None

def get_secret_value(secret_name):
    """Retrieve secret value from Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_string = response['SecretString']
        
        # Parse JSON secret
        secret_data = json.loads(secret_string)
        return secret_data
        
    except Exception as e:
        print(f"❌ Error retrieving secret value: {str(e)}")
        return None

def construct_database_url(credentials):
    """Construct DATABASE_URL from credentials"""
    
    # Known database details from CDK
    host = "solve-global-kr-rag-data-postgresqldatabase03fc658-gpdrsfsllfh8.cqhsckw0edl1.us-east-1.rds.amazonaws.com"
    port = "5432"
    database = "climate_risk_rag"
    
    # Get credentials
    username = credentials.get('username', 'postgres')
    password = credentials.get('password')
    
    if not password:
        print("❌ Password not found in secret")
        return None
    
    # Construct URL
    database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    return database_url

def test_connection(database_url):
    """Test the database connection"""
    try:
        import psycopg2
        
        print("🔌 Testing database connection...")
        
        # Mask password for display
        masked_url = database_url.split(':')[0] + '://' + database_url.split('@')[0].split('//')[1].split(':')[0] + ':***@' + database_url.split('@')[1]
        print(f"   URL: {masked_url}")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Test database access
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print("✅ Connection successful!")
        print(f"📊 PostgreSQL version: {version.split(',')[0]}")
        print(f"📁 Connected to database: {current_db}")
        
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("🔑 Climate Risk RAG Database URL Generator")
    print("=" * 50)
    
    # Try to find the secret automatically first
    print("🔍 Searching for database secrets...")
    secret_name = find_database_secret()
    
    if not secret_name:
        print("\n💡 Alternative approaches:")
        print("1. Check CloudFormation stack outputs for DatabaseSecretArn")
        print("2. Look in AWS Console > Secrets Manager")
        print("3. Check your CDK deployment logs")
        print("4. Try common passwords if this is a development environment")
        
        # Offer manual password entry
        print("\n🔧 Manual password entry:")
        manual_password = input("Enter database password (or press Enter to skip): ").strip()
        
        if manual_password:
            credentials = {'username': 'postgres', 'password': manual_password}
            database_url = construct_database_url(credentials)
            
            if database_url:
                print(f"\n📋 Generated DATABASE_URL:")
                print(f"export DATABASE_URL='{database_url}'")
                
                if test_connection(database_url):
                    print(f"\n🎉 Success! Use this command:")
                    print(f"export DATABASE_URL='{database_url}'")
                    return True
        
        return False
    
    # Get secret value
    print(f"🔓 Retrieving secret: {secret_name}")
    credentials = get_secret_value(secret_name)
    
    if not credentials:
        return False
    
    # Construct DATABASE_URL
    database_url = construct_database_url(credentials)
    
    if not database_url:
        return False
    
    print(f"\n📋 Generated DATABASE_URL:")
    masked_url = database_url.split(':')[0] + '://' + database_url.split('@')[0].split('//')[1].split(':')[0] + ':***@' + database_url.split('@')[1]
    print(f"   {masked_url}")
    
    # Test connection
    if test_connection(database_url):
        print(f"\n🎉 Success! Use this command:")
        print(f"export DATABASE_URL='{database_url}'")
        
        # Save to file for easy sourcing
        with open('/tmp/database_url.sh', 'w') as f:
            f.write(f"export DATABASE_URL='{database_url}'\n")
        
        print(f"\n💾 Also saved to: /tmp/database_url.sh")
        print(f"   You can source it with: source /tmp/database_url.sh")
        
        return True
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(1)
