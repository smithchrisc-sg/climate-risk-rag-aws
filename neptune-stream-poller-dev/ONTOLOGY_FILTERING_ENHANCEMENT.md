# Enhanced Ontology Filtering for Neptune Stream Poller

## Overview

This enhancement adds support for multiple ontology filtering in the Neptune Stream Poller, enabling concept alignment for NLP processing. The system now supports both geonames location alignment and climate risk concept alignment with fuzzy matching capabilities.

## Features

### Multi-Ontology Support
- **Geonames Ontology**: Location alignment via name-related predicates
- **Climate Risk Ontology**: Concept alignment via label predicates for concepts only

### Fuzzy Matching Ready
- Indexes appropriate predicates for fuzzy search capabilities
- Supports future addition of prefLabel, altLabel, and other label types
- Enables concept alignment from NLP extractions (e.g., "Manila" → geonames URI, "Mangrove Restoration" → climate risk concept URI)

### Safety Features
- **Feature flags** control each ontology independently
- **Backward compatibility** - existing geonames functionality unchanged
- **Pattern-based property detection** adapts to ontology evolution
- **Comprehensive logging** for debugging and monitoring

## Architecture

### Method Structure
```
filter_records()                    # Main orchestrator
├── _should_index_record()         # Routes to appropriate ontology filter
├── _filter_geonames_records()     # Geonames-specific filtering
├── _filter_climate_risk_records() # Climate risk-specific filtering
├── _is_climate_risk_label_predicate()  # Label predicate detection
├── _is_climate_risk_property()    # Pattern-based property detection
├── _is_geonames_filtering_enabled()    # Feature flag
└── _is_climate_risk_filtering_enabled() # Feature flag
```

### Filtering Logic

#### Geonames Ontology (Unchanged)
- Filters for name-related predicates only
- Supports: `geonames:name`, `geonames:alternateName`, `geonames:shortName`, etc.
- Used for location concept alignment

#### Climate Risk Ontology (New)
- Filters for label predicates on concepts only (excludes properties)
- Supports: `rdfs:label`, `skos:prefLabel`, `skos:altLabel`, `dc:title`, etc.
- Uses pattern-based property detection for flexibility
- Limited to named graph: `<http://solve.global/knowledge-commons/climate-risk-ontology>`

## Configuration

### Environment Variables

#### ENABLE_GEONAMES_FILTERING
- **Default**: `true`
- **Purpose**: Controls geonames ontology filtering
- **Safety**: Enabled by default for backward compatibility

#### ENABLE_CLIMATE_RISK_FILTERING  
- **Default**: `false`
- **Purpose**: Controls climate risk ontology filtering
- **Safety**: Disabled by default - must be explicitly enabled

### Example Configuration
```bash
# Production: Both ontologies enabled
export ENABLE_GEONAMES_FILTERING=true
export ENABLE_CLIMATE_RISK_FILTERING=true

# Testing: Climate risk only
export ENABLE_GEONAMES_FILTERING=false  
export ENABLE_CLIMATE_RISK_FILTERING=true

# Rollback: Geonames only (original behavior)
export ENABLE_GEONAMES_FILTERING=true
export ENABLE_CLIMATE_RISK_FILTERING=false
```

## Deployment Strategy

### Phase 1: Safe Deployment (Recommended)
```bash
# Deploy with climate risk filtering disabled
export ENABLE_CLIMATE_RISK_FILTERING=false
./build.sh && ./deploy.sh

# Verify geonames FTS still works
aws lambda invoke --function-name neptune-fts-test response.json
```

### Phase 2: Enable Climate Risk Filtering
```bash
# Enable climate risk filtering after validation
aws lambda update-function-configuration \
  --function-name SG-NeptuneFullTextSearch--NeptuneStreamPollerLambd-F6zwO5b5630f \
  --environment Variables='{
    "ENABLE_CLIMATE_RISK_FILTERING": "true",
    "ENABLE_GEONAMES_FILTERING": "true"
  }'
```

### Phase 3: Validation
```bash
# Test both ontologies
./test_ontology_filtering.py

# Check OpenSearch indices
curl -k -u "admin:veqpat-kegba2-zapbyZ" \
  "https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com/_cat/indices/amazon_neptune?v"
```

## Testing

### Unit Tests
```bash
cd /Users/chris/climate-risk-rag-aws/neptune-stream-poller-dev
python3 test_ontology_filtering.py
```

### Integration Testing
1. **Geonames Regression Test**: Verify existing FTS queries still work
2. **Climate Risk Test**: Load test climate risk data and verify filtering
3. **Mixed Processing**: Test both ontologies simultaneously
4. **Feature Flag Test**: Verify enable/disable behavior

### Test Cases Covered
- ✅ Geonames name predicate acceptance
- ✅ Geonames non-name predicate rejection  
- ✅ Climate risk label predicate detection
- ✅ Climate risk property pattern detection
- ✅ Climate risk concept vs property filtering
- ✅ Feature flag behavior
- ✅ Orchestration routing logic
- ✅ Edge cases and error conditions

## Usage Examples

### NLP Concept Alignment Queries

#### Location Alignment (Geonames)
```sparql
PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
SELECT ?location ?score WHERE {
  SERVICE neptune-fts:search {
    neptune-fts:config neptune-fts:endpoint "https://your-opensearch-endpoint" .
    neptune-fts:config neptune-fts:queryType "fuzzy" .
    neptune-fts:config neptune-fts:fuzziness "AUTO" .
    neptune-fts:config neptune-fts:field "predicates.http://www.geonames.org/ontology#name.value" .
    neptune-fts:config neptune-fts:query "Manila" .
    neptune-fts:config neptune-fts:return ?location .
    neptune-fts:config neptune-fts:returnScore ?score .
  }
}
ORDER BY DESC(?score)
LIMIT 5
```

#### Climate Risk Concept Alignment
```sparql
PREFIX neptune-fts: <http://aws.amazon.com/neptune/vocab/v01/services/fts#>
SELECT ?concept ?score WHERE {
  SERVICE neptune-fts:search {
    neptune-fts:config neptune-fts:endpoint "https://your-opensearch-endpoint" .
    neptune-fts:config neptune-fts:queryType "fuzzy" .
    neptune-fts:config neptune-fts:fuzziness "AUTO" .
    neptune-fts:config neptune-fts:field "predicates.http://www.w3.org/2000/01/rdf-schema#label.value" .
    neptune-fts:config neptune-fts:query "Mangrove Restoration" .
    neptune-fts:config neptune-fts:return ?concept .
    neptune-fts:config neptune-fts:returnScore ?score .
  }
}
ORDER BY DESC(?score)
LIMIT 5
```

## Monitoring and Troubleshooting

### Key Metrics to Monitor
- **Processing Rate**: Records processed per minute
- **Filter Ratios**: Percentage of records indexed vs dropped by ontology
- **Error Rates**: Failed filtering operations
- **OpenSearch Index Size**: Growth in document count

### Log Messages to Watch
```
# Normal operation
"Dropping Record : Geonames ontology - predicate not in name-related filter"
"Dropping Record : Climate risk ontology - not a label predicate"
"Dropping Record : Climate risk ontology - property subject excluded"

# Feature flag status
"Geonames filtering disabled - skipping record"
"Climate risk filtering disabled - skipping record"
```

### Troubleshooting Common Issues

#### No Climate Risk Records Indexed
1. Check feature flag: `ENABLE_CLIMATE_RISK_FILTERING=true`
2. Verify named graph in data: `<http://solve.global/knowledge-commons/climate-risk-ontology>`
3. Check predicate types: Only `rdfs:label` and similar are indexed

#### Geonames FTS Broken
1. Check feature flag: `ENABLE_GEONAMES_FILTERING=true`
2. Verify no code changes to geonames logic
3. Check CloudWatch logs for filtering decisions

#### Performance Issues
1. Monitor pattern matching overhead in `_is_climate_risk_property()`
2. Check if too many records are being processed
3. Consider optimizing property pattern list

## Future Enhancements

### Planned Features
- **Multi-language support**: Enhanced language tag handling
- **Additional label predicates**: `skos:prefLabel`, `skos:altLabel` when added to ontology
- **Direct Lucene queries**: Advanced query syntax support
- **Performance optimization**: Caching and batch processing improvements

### Extensibility
- **New ontologies**: Easy to add via new filter methods
- **Custom patterns**: Configurable property detection patterns
- **Dynamic configuration**: Runtime configuration updates

## Risk Assessment

### Low Risk
- ✅ **Backward compatibility**: Existing geonames functionality unchanged
- ✅ **Feature flags**: Safe enable/disable without code changes
- ✅ **Method isolation**: Each ontology filter is independent
- ✅ **Comprehensive testing**: Unit and integration tests included

### Mitigation Strategies
- **Gradual rollout**: Deploy with climate risk disabled first
- **Monitoring**: CloudWatch logs and metrics for early issue detection
- **Quick rollback**: Environment variable change for immediate disable
- **Isolated testing**: Each filter method can be tested independently

## Implementation Details

### Files Modified
- `neptune_to_es/neptune_sparql_es_handler.py`: Enhanced filtering logic
- `test_ontology_filtering.py`: Comprehensive test suite (new)
- `ONTOLOGY_FILTERING_ENHANCEMENT.md`: This documentation (new)

### Git Workflow
- **Feature Branch**: `feature/climate-risk-ontology-filtering`
- **Commit Strategy**: Incremental commits with clear messages
- **Testing**: All tests pass before merge
- **Documentation**: Complete documentation included

### Code Quality
- **Method extraction**: Clean separation of concerns
- **Comprehensive comments**: Self-documenting code
- **Error handling**: Proper logging and graceful failures
- **Performance**: Minimal overhead for new functionality

---

**Status**: ✅ Implementation Complete - Ready for Testing and Deployment
**Next Steps**: Deploy with climate risk filtering disabled, validate geonames functionality, then enable climate risk filtering
