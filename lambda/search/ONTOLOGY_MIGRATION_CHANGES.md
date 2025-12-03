# Ontology Migration Changes to solution_searcher.py

**Date**: 2025-12-02  
**Purpose**: Migrate from old harvester predicates to new ontology predicates  
**Status**: Code updated, NOT YET DEPLOYED

## Summary of Changes

### 1. Filter Mappings (Lines ~24-40)
**OLD**:
```python
'solution_category': {
    'natural-catastrophe': 'sg:RiskType_natural_catastrophe',
    'cyber': 'sg:RiskType_cyber',
    ...
}
'solution_type': {
    'risk-reduction': 'sg:SolutionType_risk_reduction',
    ...
}
```

**NEW**:
```python
'solution_category': {
    'natural-catastrophe': 'sg:NaturalCatastropheRisk',
    'cyber': 'sg:CyberRisk',
    ...
}
'solution_type': {
    'risk-reduction': 'sg:RiskReduction',
    ...
}
```

### 2. Filter Construction (Lines ~147-180)
**OLD**: Simple FILTER with IN clause
```sparql
?solution sg:riskType ?risk_type .
FILTER(?risk_type IN (sg:RiskType_natural_catastrophe))
```

**NEW**: UNION pattern for exact + hierarchical matching
```sparql
?solution sg:addressesRisk ?risk .
{
  FILTER(?risk IN (sg:NaturalCatastropheRisk))
}
UNION
{
  ?risk rdfs:subClassOf+ ?filterRisk .
  FILTER(?filterRisk IN (sg:NaturalCatastropheRisk))
}
```

### 3. Main Query (Lines ~680-765)
**OLD**:
- Required `sg:riskType` and `sg:solutionType` predicates
- Returned `?riskType`, `?solutionTypes`, `?risk_type_labels`, `?solution_type_labels`
- GROUP BY included `?riskType ?solutionTypes`

**NEW**:
- No longer requires old predicates
- Returns `?risk_labels`, `?mechanism_labels` (aggregated)
- GROUP BY only `?solution ?doc_id ?title`
- Uses `sg:addressesRisk` and `sg:providesMechanism`

### 4. Field Name Changes Throughout
**OLD** → **NEW**:
- `risk_type_labels` → `risk_labels`
- `solution_type_labels` → `mechanism_labels`
- `riskType` (URI) → removed
- `solutionType` (URI) → removed

### 5. get_solution_content Query (Lines ~255-295)
**OLD**:
```sparql
OPTIONAL { ?solution sg:riskType ?riskType }
OPTIONAL { ?solution sg:solutionType ?solutionType }
OPTIONAL { 
  ?solution sg:riskType ?riskType .
  ?riskType rdfs:label ?risk_type_label 
}
```

**NEW**:
```sparql
OPTIONAL { 
  ?solution sg:addressesRisk ?risk .
  ?risk rdfs:label ?risk_label 
}
OPTIONAL { 
  ?solution sg:providesMechanism ?mechanism .
  ?mechanism rdfs:label ?mechanism_label 
}
```

### 6. Count Queries (Lines ~940-975)
**OLD**: Required `sg:riskType` and `sg:solutionType` in WHERE clause

**NEW**: Only requires `sgd:Solution` type - filters handle the rest

### 7. Removed Fallback Logic (Lines ~442-453)
**OLD**: Had fallback to extract labels from URI strings if labels missing

**NEW**: Removed - new ontology always has `rdfs:label` properties

## Testing Validation

Tested in Jupyter notebook with these queries:
1. ✅ Natural catastrophe filter (hierarchical) - 10 results
2. ✅ Natural catastrophe + risk reduction - 55 results  
3. ✅ Coverage check - 559/567 solutions have new predicates

## Deployment Strategy

### Phase 1: Deploy Lambda (READY)
- Updated code in `/Users/chris/climate-risk-rag-aws/lambda/search/src/search/solution_searcher.py`
- Create deployment.zip
- Update Lambda function
- **CRITICAL**: Test immediately after deployment

### Phase 2: Verify Search Works
- Test webapp search with natural-catastrophe filter
- Test multiple filters (natural-catastrophe + risk-reduction)
- Verify API responses have correct field names
- Check CloudWatch logs for errors

### Phase 3: Delete Old Predicates (AFTER VERIFICATION)
```sparql
PREFIX sg: <http://solve.global/knowledge-commons/>
PREFIX sgm: <http://solve.global/knowledge-commons/process-metadata#>

DELETE {
  ?solution sg:riskType ?oldRisk .
  ?solution sg:solutionType ?oldSolution .
}
WHERE {
  ?solution sgm:hasAlignment ?alignment .
  ?solution sg:riskType ?oldRisk .
  ?solution sg:solutionType ?oldSolution .
}
```

## Rollback Plan

If search breaks after Lambda deployment:

1. **Immediate**: Revert Lambda to previous version
   ```bash
   aws lambda update-function-code \
     --function-name gaip-search-lambda \
     --s3-bucket <backup-bucket> \
     --s3-key previous-deployment.zip
   ```

2. **Verify**: Test search works again

3. **Debug**: Check CloudWatch logs for specific errors

## Risk Assessment

**LOW RISK** because:
- Old predicates still in Neptune (not deleted yet)
- Can rollback Lambda immediately if issues
- Tested queries work in Jupyter notebook
- No data changes, only code changes

**MEDIUM DOWNTIME** if issues:
- 5-10 minutes to identify problem
- 2-3 minutes to rollback Lambda
- Total: ~15 minutes max

## Files Modified

1. `/Users/chris/climate-risk-rag-aws/lambda/search/src/search/solution_searcher.py`
   - Filter mappings
   - Filter construction with UNION pattern
   - Main query structure
   - Field name changes
   - Count queries
   - Removed fallback logic

## Next Steps

1. Review this document
2. Create Lambda deployment package
3. Deploy to Lambda (but don't delete old predicates yet)
4. Test search functionality thoroughly
5. If all tests pass, proceed with Neptune cleanup
6. If tests fail, rollback Lambda immediately

## Notes

- The 8 solutions with `cannot_be_determined` will be preserved (they don't have alignments)
- Hierarchical filtering enables both broad (NaturalCatastropheRisk) and specific (FloodRisk) queries
- New ontology provides richer semantic relationships for future enhancements
