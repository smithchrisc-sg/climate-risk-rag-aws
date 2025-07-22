# DEPRECATED: Old Keyword Indexer Functions

**Date Deprecated:** July 22, 2025  
**Reason:** Consolidated into single `keyword-indexer` function

## What Was Deprecated

### keyword-indexer-initiator
- **Purpose:** Parsed SNS messages and invoked worker via direct Lambda call
- **Issues:** Tight coupling, unnecessary complexity

### keyword-indexer-worker  
- **Purpose:** Performed actual OpenSearch indexing
- **Issues:** Separate function not needed for synchronous OpenSearch operations

## Replacement

**New Function:** `lambda/keyword-indexer/`
- **Benefits:** Single function, loose coupling via SQS, simplified database writes
- **Database:** Uses `keyword_indexing` stage (2 entries instead of 4)
- **Architecture:** Proper async pattern with SQS → Lambda → OpenSearch → SNS

## Migration Completed

- ✅ Functions deleted from AWS
- ✅ Source code moved to lambda-DEPRECATED/keyword-indexer-OLD/
- ✅ Database constraint updated to use `keyword_indexing` stage
- ✅ Redundant SQS queue removed
- ✅ All functionality preserved in consolidated function

**Do not restore these functions - use the consolidated `keyword-indexer` instead.**
