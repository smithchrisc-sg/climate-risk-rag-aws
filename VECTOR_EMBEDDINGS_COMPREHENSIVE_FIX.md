# Vector Embeddings Comprehensive Fix Plan

## Current Status
- ✅ Updated Lambda layers to latest versions
- ❌ Import errors persist: "No module named 'utils'"
- ❌ Functions still failing to start

## Root Cause Analysis
The issue is that the vector embeddings functions are trying to import `from utils.DatabaseManager import DatabaseManager` but the layer structure may not be compatible.

## Immediate Actions Needed

### 1. Verify Layer Structure
- Check if utils module is properly structured in the layer
- Ensure __init__.py files exist in the right places

### 2. Update Function Code
- May need to update the import statements
- Consider using absolute imports instead of relative imports

### 3. Test Import Path
- Create a simple test function to verify imports work

## Next Steps (in order)

1. **Fix Import Issues** (High Priority)
   - Update function code with correct import paths
   - Test imports work with current layer

2. **Add Missing Dependencies** (High Priority)  
   - Ensure vector embeddings dependencies are available
   - Add sentence-transformers, torch, etc.

3. **Test End-to-End** (Medium Priority)
   - Run pipeline test to verify vector embeddings work
   - Check OpenSearch integration

4. **Optimize Performance** (Low Priority)
   - Review VPC configuration
   - Optimize memory and timeout settings

## Success Criteria
- [ ] Functions can import DatabaseManager successfully
- [ ] Vector embeddings are generated without errors
- [ ] Embeddings are indexed in OpenSearch
- [ ] Pipeline test passes end-to-end
