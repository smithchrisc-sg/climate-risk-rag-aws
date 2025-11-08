#!/usr/bin/env python3
"""
Simple database connectivity test using Environment defaults.
"""

import sys
import os
from pathlib import Path
import psycopg2

# Setup paths
sys.path.append(str(Path(__file__).parent))

def test_direct_database_connection():
    """Test direct database connection using Environment defaults."""
    print("Testing direct database connection...")
    
    try:
        from config.environment import Environment
        
        # Initialize environment
        env = Environment()
        print(f"[OK] Environment loaded")
        print(f"Database URL: {env._mask_url(env.database_url)}")
        
        # Parse database URL for psycopg2
        import urllib.parse
        parsed = urllib.parse.urlparse(env.database_url)
        
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove leading slash
            'user': parsed.username,
            'password': parsed.password
        }
        
        # Add SSL mode if in URL
        if 'sslmode' in parsed.query:
            conn_params['sslmode'] = 'require'
        
        print(f"[OK] Connection params parsed")
        print(f"Host: {conn_params['host']}")
        print(f"Database: {conn_params['database']}")
        print(f"User: {conn_params['user']}")
        
        # Test connection
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"[OK] Database connected: {version}")
        
        # Test basic query
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"[OK] Connected to database: {db_info[0]} as user: {db_info[1]}")
        
        cursor.close()
        conn.close()
        
        print("\n✓ DATABASE CONNECTION TEST PASSED!")
        return True
        
    except Exception as e:
        print(f"\n✗ DATABASE CONNECTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_solution_model():
    """Test solution model creation."""
    print("\nTesting solution model...")
    
    try:
        from models.solution import Solution
        
        # Create minimal test solution
        solution = Solution(
            id="test_001",
            source_file="test.csv", 
            row_number=1,
            number="001",
            name="Test Solution",
            country="Test Country",
            public_organisations="Test Org",
            international_organisations="",
            private_organisations="",
            type_of_risk="Climate Risk",
            type_of_solution="Adaptation", 
            ppp="Public",
            theme="Water Management",
            year_of_implementation="2024",
            description="Test description",
            implementation_details="Test implementation",
            results="Test results",
            lessons_learned="Test lessons",
            contact_information="test@example.com",
            website="https://example.com",
            additional_information=""
        )
        
        print(f"[OK] Solution created: {solution.name}")
        print(f"[OK] Document ID: {solution.doc_id}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ SOLUTION MODEL TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Simple EC2 Database Test ===\n")
    
    db_success = test_direct_database_connection()
    model_success = test_solution_model()
    
    if db_success and model_success:
        print("\n🎉 All tests passed! Ready for full pipeline testing.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check configuration.")
        sys.exit(1)
