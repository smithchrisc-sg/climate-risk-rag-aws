# NLP Worker Source Directory Cleanup Plan

## Current State (ARCHITECTURAL DISCIPLINE VIOLATION)
- ❌ `nlp_worker.py` (31,907 bytes, July 31) - **CURRENTLY DEPLOYED**
- ❌ `nlp_worker_corrected.py` (12,383 bytes, July 31) - Corrected version
- ❌ `nlp_worker_async.py` (22,264 bytes, July 29) - Async version  
- ❌ `nlp_worker.py.original` (3,610 bytes, July 29) - Original backup

## Analysis
1. **Handler imports**: `from nlp_worker import NLPWorker` (no suffix)
2. **Currently deployed**: `nlp_worker.py` (largest, most recent)
3. **Issue**: Entity-to-chunk mapping failing despite corrected logic

## Cleanup Actions
1. **Preserve current working version** as `nlp_worker.py`
2. **Archive other versions** to `archive/` subdirectory
3. **Identify and fix mapping issue** in the working version
4. **Deploy clean version** after debugging

## Next Steps
1. Create archive directory
2. Move variant files to archive
3. Debug entity-to-chunk mapping in current version
4. Test with existing data lake documents
