#!/usr/bin/env python3
"""
Lambda Runtime Upgrade Script
Addresses Node.js 18 deprecation and Python 3.9 upgrades
"""
import boto3
import json
from datetime import datetime

def analyze_lambda_runtimes():
    """Analyze current Lambda function runtimes"""
    
    print("LAMBDA RUNTIME ANALYSIS")
    print("=" * 50)
    
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    # Get all functions
    response = lambda_client.list_functions()
    functions = response['Functions']
    
    # Categorize by runtime
    runtime_analysis = {
        'nodejs18.x': [],  # CRITICAL - needs immediate upgrade
        'python3.9': [],   # Should upgrade to python3.11
        'python3.11': [], # Good - current
        'nodejs22.x': [], # Good - current
        'other': []
    }
    
    for func in functions:
        runtime = func['Runtime']
        func_info = {
            'name': func['FunctionName'],
            'runtime': runtime,
            'handler': func['Handler'],
            'description': func.get('Description', ''),
            'last_modified': func['LastModified']
        }
        
        if runtime in runtime_analysis:
            runtime_analysis[runtime].append(func_info)
        else:
            runtime_analysis['other'].append(func_info)
    
    # Print analysis
    print("RUNTIME DISTRIBUTION:")
    for runtime, funcs in runtime_analysis.items():
        if funcs:
            print("  {}: {} functions".format(runtime, len(funcs)))
    
    print("\nCRITICAL - Node.js 18 Functions (Must upgrade by Sept 1, 2025):")
    for func in runtime_analysis['nodejs18.x']:
        print("  - {} ({})".format(func['name'], func['handler']))
    
    print("\nRECOMMENDED - Python 3.9 Functions (Should upgrade to 3.11):")
    for func in runtime_analysis['python3.9']:
        print("  - {} ({})".format(func['name'], func['handler']))
    
    print("\nGOOD - Current Runtimes:")
    print("  Python 3.11: {} functions".format(len(runtime_analysis['python3.11'])))
    print("  Node.js 22: {} functions".format(len(runtime_analysis['nodejs22.x'])))
    
    return runtime_analysis

def upgrade_nodejs18_functions(runtime_analysis):
    """Upgrade Node.js 18 functions to Node.js 22"""
    
    print("\nUPGRADING NODE.JS 18 FUNCTIONS")
    print("=" * 40)
    
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    nodejs18_functions = runtime_analysis['nodejs18.x']
    
    if not nodejs18_functions:
        print("No Node.js 18 functions found - all good!")
        return
    
    for func in nodejs18_functions:
        func_name = func['name']
        print("Upgrading {}: nodejs18.x -> nodejs22.x".format(func_name))
        
        try:
            # Update function configuration
            response = lambda_client.update_function_configuration(
                FunctionName=func_name,
                Runtime='nodejs22.x'
            )
            
            print("  SUCCESS: {} upgraded to nodejs22.x".format(func_name))
            
        except Exception as e:
            print("  ERROR upgrading {}: {}".format(func_name, str(e)))
            
            # Check if it's a CDK-managed function
            if 'LogRetention' in func_name:
                print("  NOTE: This appears to be a CDK LogRetention function")
                print("        It will be automatically upgraded when you redeploy the CDK stack")

def upgrade_python39_functions(runtime_analysis):
    """Upgrade Python 3.9 functions to Python 3.11"""
    
    print("\nUPGRADING PYTHON 3.9 FUNCTIONS")
    print("=" * 40)
    
    session = boto3.Session(profile_name='solve-global')
    lambda_client = session.client('lambda', region_name='us-east-1')
    
    python39_functions = runtime_analysis['python3.9']
    
    if not python39_functions:
        print("No Python 3.9 functions found - all good!")
        return
    
    print("Found {} Python 3.9 functions that should be upgraded:".format(len(python39_functions)))
    
    for func in python39_functions:
        func_name = func['name']
        print("\nFunction: {}".format(func_name))
        print("  Current: python3.9")
        print("  Recommended: python3.11")
        
        # Check if it's part of our main system
        if any(keyword in func_name.lower() for keyword in ['solve-global-kr', 'rag-micro']):
            print("  Status: Part of main RAG system - should be upgraded")
            print("  Action: Redeploy with updated CDK configuration")
        else:
            print("  Status: Standalone function")
            print("  Action: Manual upgrade recommended")

def create_upgrade_plan():
    """Create comprehensive upgrade plan"""
    
    print("\nLAMBDA RUNTIME UPGRADE PLAN")
    print("=" * 50)
    
    plan = {
        'immediate_actions': [
            "Upgrade Node.js 18 LogRetention function (CRITICAL - Sept 1, 2025 deadline)",
            "Test upgraded functions to ensure compatibility"
        ],
        'recommended_actions': [
            "Upgrade Python 3.9 functions to Python 3.11 for better performance",
            "Update CDK configurations to use latest runtimes",
            "Standardize on Python 3.11 for all new functions"
        ],
        'cdk_updates_needed': [
            "Update CDK runtime specifications in stack definitions",
            "Redeploy stacks to apply runtime updates",
            "Verify LogRetention functions use nodejs22.x"
        ],
        'testing_required': [
            "Test Node.js LogRetention function after upgrade",
            "Verify Python 3.11 compatibility for upgraded functions",
            "Run integration tests after upgrades"
        ]
    }
    
    for category, actions in plan.items():
        print("\n{}:".format(category.upper().replace('_', ' ')))
        for action in actions:
            print("  - {}".format(action))
    
    return plan

def main():
    """Run Lambda runtime analysis and upgrades"""
    
    print("Lambda Runtime Upgrade Tool")
    print("Addressing Node.js 18 deprecation and Python 3.9 upgrades")
    print("=" * 60)
    
    # Analyze current state
    runtime_analysis = analyze_lambda_runtimes()
    
    # Create upgrade plan
    upgrade_plan = create_upgrade_plan()
    
    # Perform upgrades
    print("\n" + "=" * 60)
    print("PERFORMING UPGRADES")
    print("=" * 60)
    
    # Upgrade Node.js 18 functions (CRITICAL)
    upgrade_nodejs18_functions(runtime_analysis)
    
    # Analyze Python 3.9 functions (RECOMMENDED)
    upgrade_python39_functions(runtime_analysis)
    
    # Save analysis results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = 'lambda_runtime_analysis_{}.json'.format(timestamp)
    
    with open(results_file, 'w') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'runtime_analysis': runtime_analysis,
            'upgrade_plan': upgrade_plan
        }, f, indent=2, default=str)
    
    print("\nAnalysis saved to: {}".format(results_file))
    
    print("\n" + "=" * 60)
    print("UPGRADE SUMMARY")
    print("=" * 60)
    print("Node.js 18 functions: {} (CRITICAL - must upgrade by Sept 1, 2025)".format(
        len(runtime_analysis['nodejs18.x'])
    ))
    print("Python 3.9 functions: {} (recommended to upgrade)".format(
        len(runtime_analysis['python3.9'])
    ))
    print("Current runtime functions: {} (no action needed)".format(
        len(runtime_analysis['python3.11']) + len(runtime_analysis['nodejs22.x'])
    ))

if __name__ == "__main__":
    main()
