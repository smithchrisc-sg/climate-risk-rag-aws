#!/usr/bin/env python3
"""
Deployment validation script for the search Lambda function.
Validates dependencies and configuration before deployment.
"""

import sys
import importlib
import os

def validate_dependencies():
    """Validate all required dependencies are available"""
    required_packages = [
        'numpy',
        'scipy', 
        'opensearchpy',
        'boto3',
        'botocore',
        'requests',
        'psycopg2'
    ]
    
    missing = []
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} - MISSING")
    
    return len(missing) == 0, missing

def validate_modules():
    """Validate our custom modules can be imported"""
    sys.path.insert(0, 'src')
    
    modules = [
        'models.search_models',
        'search.config',
        'search.score_stats',
        'search.score_normalizer', 
        'search.result_combiner',
        'search.coordinator'
    ]
    
    missing = []
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            missing.append(module)
            print(f"✗ {module} - {e}")
    
    return len(missing) == 0, missing

def validate_configuration():
    """Validate configuration is accessible"""
    try:
        from search.config import get_scoring_config, is_lambda_environment
        config = get_scoring_config()
        print(f"✓ Configuration loaded")
        print(f"  Lambda environment: {is_lambda_environment()}")
        print(f"  Weights: {config['weights']}")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def main():
    """Run all validation checks"""
    print("=== Search Lambda Deployment Validation ===\n")
    
    print("1. Checking dependencies...")
    deps_ok, missing_deps = validate_dependencies()
    
    print("\n2. Checking modules...")
    modules_ok, missing_modules = validate_modules()
    
    print("\n3. Checking configuration...")
    config_ok = validate_configuration()
    
    print("\n=== Summary ===")
    if deps_ok and modules_ok and config_ok:
        print("✓ All validation checks passed - ready for deployment!")
        return 0
    else:
        print("✗ Validation failed:")
        if missing_deps:
            print(f"  Missing dependencies: {missing_deps}")
        if missing_modules:
            print(f"  Missing modules: {missing_modules}")
        if not config_ok:
            print("  Configuration issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())
