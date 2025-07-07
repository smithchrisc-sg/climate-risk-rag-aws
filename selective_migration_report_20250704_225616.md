
# Selective POC to PostgreSQL Migration Report
## Date: 2025-07-04T22:56:16.528300

## Migration Strategy
- **Approach**: Selective migration of documents that exist in both POC database and S3 bucket
- **S3 Bucket**: solve-global-kr-documents-861276078413-us-east-1
- **AWS Profile**: solve-global

## Document Analysis
- **Total POC Documents**: 15171
- **Total S3 Documents**: 1000
- **Matching Documents**: 1000
- **Documents Migrated**: 1000
- **Migration Errors**: 0

## Document Distribution
- **S3 Only**: 0 documents
- **POC Only**: 14171 documents
- **Both S3 and POC**: 1000 documents ✅

## Status Distribution (Migrated Documents)
- **pending**: 1000 documents

## URL Patterns (Migrated Documents)
- **documents.worldbank.org**: 1000 documents

## S3 Integration
- **S3 Mappings Created**: 1000
- **S3 Key Format**: `documents/{doc_id}.pdf`
- **Verified in S3**: All migrated documents confirmed to exist in S3

## Migration Mode
- **Dry Run**: False
- **Database**: Full selective migration

## Benefits of Selective Migration
1. **Focused Dataset**: Only migrate documents we actually have in S3
2. **Reduced Complexity**: ~1000 documents vs 15,000+ full dataset
3. **Verified Availability**: All migrated documents confirmed to exist in S3
4. **Cost Efficiency**: No wasted processing on unavailable documents

## Next Steps
1. Review selective migration results
2. Test TextExtractor integration with migrated subset
3. Validate S3 key mappings work correctly
4. Update downstream processors to use migrated doc_ids
5. Consider expanding to full dataset later if needed
