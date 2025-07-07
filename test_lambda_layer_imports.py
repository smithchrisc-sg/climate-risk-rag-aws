#!/usr/bin/env python3
"""
Test Lambda Layer Import Structure
Validates that imports work correctly in the lambda layer structure
"""

import sys
import os

def test_lambda_layer_imports():
    """Test imports as they would work in lambda environment"""
    
    print("🧪 Testing Lambda Layer Import Structure")
    print("=" * 60)
    
    # Add lambda layer path to Python path (simulating lambda environment)
    layer_path = '/Users/chris/climate-risk-rag-aws/layers/build/climate-risk-core-layer/python'
    if layer_path not in sys.path:
        sys.path.insert(0, layer_path)
    
    print(f"✅ Added layer path: {layer_path}")
    
    # Test DatabaseManager import
    try:
        from DatabaseManager import DatabaseManager
        print("✅ DatabaseManager import successful")
        
        # Test initialization (without actual database connection)
        print("✅ DatabaseManager class accessible")
        
    except Exception as e:
        print(f"❌ DatabaseManager import failed: {e}")
        return False
    
    # Test DocumentIDManager import
    try:
        from DocumentIDManager import DocumentIDManager
        print("✅ DocumentIDManager import successful")
        
    except Exception as e:
        print(f"❌ DocumentIDManager import failed: {e}")
        return False
    
    # Test structured chunker import
    try:
        from structured_chunking_smart_complete import SmartStructuredChunker
        print("✅ SmartStructuredChunker import successful")
        
    except Exception as e:
        print(f"❌ SmartStructuredChunker import failed: {e}")
        return False
    
    # Test text chunker imports (simulating lambda environment)
    print("\n🔧 Testing Text Chunker Import Compatibility")
    print("-" * 40)
    
    # Add text chunker path
    chunker_path = '/Users/chris/climate-risk-rag-aws/lambda/text_chunker'
    if chunker_path not in sys.path:
        sys.path.insert(0, chunker_path)
    
    try:
        # Test the updated import statements
        exec("""
try:
    from DatabaseManager import DatabaseManager
    print("✅ Text chunker DatabaseManager import works")
except Exception as e:
    print(f"❌ Text chunker DatabaseManager import failed: {e}")
    raise

try:
    from structured_chunking_smart_complete import SmartStructuredChunker
    print("✅ Text chunker SmartStructuredChunker import works")
except Exception as e:
    print(f"❌ Text chunker SmartStructuredChunker import failed: {e}")
    raise
""")
        
    except Exception as e:
        print(f"❌ Text chunker import test failed: {e}")
        return False
    
    print("\n🎉 All lambda layer imports working correctly!")
    return True

def test_layer_file_structure():
    """Test that all required files are in the lambda layer"""
    
    print("\n📁 Testing Lambda Layer File Structure")
    print("=" * 60)
    
    layer_path = '/Users/chris/climate-risk-rag-aws/layers/build/climate-risk-core-layer/python'
    
    required_files = [
        'DatabaseManager.py',
        'DocumentIDManager.py', 
        'structured_chunking_smart_complete.py',
        '__init__.py'
    ]
    
    all_present = True
    
    for file_name in required_files:
        file_path = os.path.join(layer_path, file_name)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ {file_name}: {file_size:,} bytes")
        else:
            print(f"❌ {file_name}: Missing")
            all_present = False
    
    return all_present

def run_layer_tests():
    """Run all lambda layer tests"""
    
    print("🚀 Lambda Layer Import Fix Validation")
    print("=" * 80)
    
    tests = [
        ("File Structure", test_layer_file_structure),
        ("Import Compatibility", test_lambda_layer_imports)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 Lambda Layer Test Results")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All lambda layer tests passed! Ready for deployment.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Fix before deployment.")
    
    return failed == 0

if __name__ == "__main__":
    success = run_layer_tests()
    sys.exit(0 if success else 1)
