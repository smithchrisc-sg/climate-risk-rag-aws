#!/usr/bin/env python3
"""
Simple structure validation for Knowledge Graph Layer
Checks that all files are present and have basic syntax
"""
import os
import sys
import ast

def validate_file_structure():
    """Validate that all required files are present"""
    print("Validating Knowledge Graph Layer structure...")
    
    required_files = [
        'python/utils/__init__.py',
        'python/utils/KnowledgeGraphManager.py',
        'python/utils/URIManager.py',
        'python/utils/SPARQLQueryBuilder.py',
        'python/utils/OntologyManager.py',
        'python/utils/TripleManager.py',
        'python/utils/BulkLoadManager.py',
        'python/utils/kg_exceptions.py',
        'requirements.txt',
        'README.md',
        'build_layer.sh'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("ERROR: Missing files:")
        for file_path in missing_files:
            print("  - {}".format(file_path))
        return False
    
    print("PASS: All required files present")
    return True

def validate_python_syntax():
    """Validate Python syntax for all Python files"""
    print("Validating Python syntax...")
    
    python_files = [
        'python/utils/__init__.py',
        'python/utils/KnowledgeGraphManager.py',
        'python/utils/URIManager.py',
        'python/utils/SPARQLQueryBuilder.py',
        'python/utils/OntologyManager.py',
        'python/utils/TripleManager.py',
        'python/utils/BulkLoadManager.py',
        'python/utils/kg_exceptions.py'
    ]
    
    syntax_errors = []
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            ast.parse(content)
        except SyntaxError as e:
            syntax_errors.append("{}:{}:{}".format(file_path, e.lineno, e.msg))
        except Exception as e:
            syntax_errors.append("{}: {}".format(file_path, str(e)))
    
    if syntax_errors:
        print("ERROR: Syntax errors found:")
        for error in syntax_errors:
            print("  - {}".format(error))
        return False
    
    print("PASS: All Python files have valid syntax")
    return True

def validate_imports():
    """Validate that imports are structured correctly"""
    print("Validating import structure...")
    
    # Check __init__.py exports
    try:
        with open('python/utils/__init__.py', 'r') as f:
            init_content = f.read()
        
        required_exports = [
            'KnowledgeGraphManager',
            'SPARQLQueryBuilder',
            'URIManager',
            'OntologyManager',
            'TripleManager',
            'BulkLoadManager'
        ]
        
        missing_exports = []
        for export in required_exports:
            if export not in init_content:
                missing_exports.append(export)
        
        if missing_exports:
            print("ERROR: Missing exports in __init__.py:")
            for export in missing_exports:
                print("  - {}".format(export))
            return False
        
        print("PASS: All required exports present in __init__.py")
        return True
        
    except Exception as e:
        print("ERROR: Failed to validate __init__.py: {}".format(e))
        return False

def validate_requirements():
    """Validate requirements.txt"""
    print("Validating requirements.txt...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        required_packages = [
            'rdflib',
            'requests',
            'requests-aws4auth',
            'boto3'
        ]
        
        missing_packages = []
        for package in required_packages:
            if package not in requirements:
                missing_packages.append(package)
        
        if missing_packages:
            print("ERROR: Missing packages in requirements.txt:")
            for package in missing_packages:
                print("  - {}".format(package))
            return False
        
        print("PASS: All required packages in requirements.txt")
        return True
        
    except Exception as e:
        print("ERROR: Failed to validate requirements.txt: {}".format(e))
        return False

def main():
    """Run all validations"""
    print("=" * 60)
    print("Knowledge Graph Layer Structure Validation")
    print("=" * 60)
    
    validations = [
        validate_file_structure,
        validate_python_syntax,
        validate_imports,
        validate_requirements
    ]
    
    all_passed = True
    for validation in validations:
        if not validation():
            all_passed = False
        print()
    
    print("=" * 60)
    if all_passed:
        print("SUCCESS: All validations passed!")
        print("Layer structure is valid and ready for building.")
    else:
        print("FAILURE: Some validations failed.")
        print("Please fix the issues before building the layer.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
