# GOLD STANDARD LAYERS - DEFINITIVE REFERENCE

## 🔒 CURRENT GOLD STANDARD (CORRECTED)

### Primary Layers:
- **climate-risk-core-utilities:16** - CORRECTED with proper DatabaseManager (secrets manager integration)
- **database-dependencies-pipeline:9** - PostgreSQL drivers and dependencies
- **opensearch-dependencies:4** - OpenSearch/Elasticsearch libraries

### Function Assignments:
```
Text Extraction Processor:
- climate-risk-core-utilities:16
- database-dependencies-pipeline:9

Keyword Indexer Worker:
- climate-risk-core-utilities:16
- database-dependencies-pipeline:9
- opensearch-dependencies:4

Text Chunker Functions:
- climate-risk-core-utilities:16
- database-dependencies-pipeline:9
```

## 🔄 CRITICAL CORRECTION MADE:
- **ISSUE**: We had deprecated the CORRECT DatabaseManager and kept the wrong one as "authoritative"
- **FIXED**: Swapped files to restore the working DatabaseManager with secrets manager integration
- **STATUS**: Layer v16 contains the corrected DatabaseManager

## 📋 Authoritative Source Code:
- **DatabaseManager**: `/layers/app-source/utils/DatabaseManager.py` (NOW CORRECT - uses secrets manager)
- **Deprecated wrong version**: `DEPRECATED_DatabaseManager_wrong_version.py`

## 🚫 ANTI-PATTERNS ELIMINATED:
- ❌ NO try/catch blocks around required imports
- ❌ NO DATABASE_URL environment variable dependency
- ✅ USES secrets manager and standard environment variables

## 🔒 CHANGE CONTROL:
- Layer v16 is the CORRECTED gold standard
- Contains proper DatabaseManager with secrets manager integration
- All functions updated to use corrected layer
