# NEXT STEPS - August 15, 2025

## 🎯 **IMMEDIATE PRIORITIES**

### **1. Configure OpenSearch Endpoint for FTS Queries**
**Status**: CRITICAL - Required for entity alignment to function
**Estimated Time**: 30 minutes

**Actions Required**:
- [ ] Add `OPENSEARCH_ENDPOINT` environment variable to `nlp_kg_processor` Lambda function
- [ ] Value: `https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com`
- [ ] Verify OpenSearch cluster is accessible from Lambda VPC subnets
- [ ] Test FTS connectivity with simple query

**Files to Update**:
- Lambda environment variables (via AWS CLI or CDK)

**Validation**:
```bash
aws lambda update-function-configuration \
  --function-name nlp_kg_processor \
  --environment Variables='{
    "OPENSEARCH_ENDPOINT":"https://vpc-solve-global-kr-search-hsacnclbjsoclui75hefj2espq.us-east-1.es.amazonaws.com",
    "ENABLE_CONTEXTUAL_ALIGNMENT":"true",
    "CONTEXTUAL_ALIGNMENT_ENTITY_TYPES":"LOCATION",
    "CONTEXTUAL_ALIGNMENT_ONTOLOGIES":"geonames",
    ...existing vars...
  }'
```

### **2. Deploy Updated Knowledge Graph Layer**
**Status**: READY - Layer code is fixed, needs deployment
**Estimated Time**: 15 minutes

**Actions Required**:
- [ ] Build and deploy `knowledge-graph-layer` with FTS query fixes
- [ ] Update `nlp_kg_processor` to use new layer version
- [ ] Update `kg-triple-loader` to use new layer version (if needed)

**Commands**:
```bash
cd /Users/chris/climate-risk-rag-aws/layers/knowledge-graph-layer
./build_layer.sh
# Deploy new layer version
# Update Lambda functions to use new version
```

### **3. End-to-End Testing with Cost Controls**
**Status**: READY - All components fixed, ready for integration testing
**Estimated Time**: 1-2 hours
**Estimated Cost**: <$5 (using existing processed documents)

**Testing Strategy**:
- [ ] **Phase 1**: Test with existing NLP results (document ID: `064762102bead7b04a39`)
- [ ] **Phase 2**: Verify FTS queries return results from GeoNames
- [ ] **Phase 3**: Validate TTL generation and S3 storage
- [ ] **Phase 4**: Test kg-triple-loader integration
- [ ] **Phase 5**: Verify triples appear in Neptune

**Test Commands**:
```bash
# Test nlp_kg_processor with existing data
aws lambda invoke --function-name nlp_kg_processor \
  --cli-binary-format raw-in-base64-out \
  --payload file:///tmp/correct_nlp_kg_test.json \
  --region us-east-1 /tmp/nlp_kg_processor_response.json

# Check results
cat /tmp/nlp_kg_processor_response.json
```

---

## 🔄 **SHORT-TERM DEVELOPMENT (1-2 weeks)**

### **4. Enhance Error Handling and Logging**
**Priority**: HIGH - Improve debugging capabilities
**Estimated Time**: 4-6 hours

**Actions Required**:
- [ ] Add detailed FTS query logging in `ContextualEntityAligner`
- [ ] Improve error messages for OpenSearch connectivity issues
- [ ] Add performance metrics logging (query time, result counts)
- [ ] Implement retry logic for transient FTS failures

**Files to Update**:
- `layers/knowledge-graph-layer/python/utils/ContextualEntityAligner.py`
- `layers/knowledge-graph-layer/python/utils/FTSSparqlQueryBuilder.py`

### **5. Implement Climate Risk Ontology Support**
**Priority**: MEDIUM - Extend beyond GeoNames
**Estimated Time**: 8-12 hours

**Actions Required**:
- [ ] Complete `build_climate_concept_query()` implementation in `FTSSparqlQueryBuilder`
- [ ] Add climate risk ontology FTS field mappings
- [ ] Update environment variable configuration to support multiple ontologies
- [ ] Test with climate-related entities (if available in test data)

**Environment Variables to Add**:
```
CONTEXTUAL_ALIGNMENT_ENTITY_TYPES=LOCATION,ORG,OTHER
CONTEXTUAL_ALIGNMENT_ONTOLOGIES=geonames,climate_risk
```

### **6. Performance Optimization**
**Priority**: MEDIUM - Improve query performance
**Estimated Time**: 6-8 hours

**Actions Required**:
- [ ] Implement query result caching in `EntityAlignmentManager`
- [ ] Add batch processing for multiple entities
- [ ] Optimize SPARQL queries for better performance
- [ ] Add query timeout configuration

---

## 🚀 **MEDIUM-TERM ENHANCEMENTS (2-4 weeks)**

### **7. Contextual Scoring Implementation**
**Priority**: HIGH - Core feature for disambiguation
**Estimated Time**: 12-16 hours

**Actions Required**:
- [ ] Implement document-level context analysis
- [ ] Add chunk-level co-occurrence scoring
- [ ] Integrate geographic context weighting
- [ ] Test with ambiguous location names (Paris, London, etc.)

**Reference**: `docs/knowledge-graph/ENTITIY_ALIGNMENT_APPROACH_2025-08-12.md`

### **8. Multi-Field FTS Query Optimization**
**Priority**: MEDIUM - Improve search coverage
**Estimated Time**: 4-6 hours

**Actions Required**:
- [ ] Test `build_location_query_with_alternates()` performance
- [ ] Implement field-specific scoring weights
- [ ] Add fuzzy matching capabilities
- [ ] Optimize UNION query performance

### **9. Comprehensive Testing Suite**
**Priority**: HIGH - Ensure system reliability
**Estimated Time**: 8-12 hours

**Actions Required**:
- [ ] Create automated test suite for entity alignment
- [ ] Add unit tests for FTS query builders
- [ ] Implement integration tests for full pipeline
- [ ] Add performance benchmarking

---

## 🔧 **INFRASTRUCTURE & OPERATIONS**

### **10. Layer Version Consolidation**
**Priority**: LOW - Technical debt cleanup
**Estimated Time**: 2-3 hours

**Actions Required**:
- [ ] Audit all Lambda functions for layer version usage
- [ ] Consolidate to latest stable versions
- [ ] Remove unused layer versions
- [ ] Update CDK configurations

### **11. Monitoring and Alerting**
**Priority**: MEDIUM - Production readiness
**Estimated Time**: 6-8 hours

**Actions Required**:
- [ ] Add CloudWatch metrics for entity alignment success rates
- [ ] Implement alerting for FTS query failures
- [ ] Add cost monitoring for expensive operations
- [ ] Create operational dashboards

### **12. Documentation Updates**
**Priority**: LOW - Maintain documentation currency
**Estimated Time**: 2-4 hours

**Actions Required**:
- [ ] Update architecture diagrams with FTS integration
- [ ] Document new environment variable configurations
- [ ] Create troubleshooting guide for common issues
- [ ] Update deployment procedures

---

## 🎯 **SUCCESS METRICS**

### **Immediate Success (Next 1-2 days)**
- [ ] `nlp_kg_processor` successfully processes test document
- [ ] FTS queries return relevant GeoNames results
- [ ] TTL files generated and stored in Neptune bucket
- [ ] kg-triple-loader successfully processes TTL files
- [ ] Triples visible in Neptune graph database

### **Short-term Success (Next 1-2 weeks)**
- [ ] Entity alignment accuracy >80% for common location names
- [ ] Average query response time <2 seconds
- [ ] Zero authentication errors in production logs
- [ ] Cost per document processing <$0.05

### **Medium-term Success (Next 2-4 weeks)**
- [ ] Support for multiple entity types (LOCATION, ORG, OTHER)
- [ ] Contextual disambiguation working for ambiguous names
- [ ] Climate risk ontology integration functional
- [ ] Automated testing suite covering all major paths

---

## ⚠️ **RISK MITIGATION**

### **Cost Management**
- **Monitor**: AWS billing dashboard daily during testing
- **Limit**: Maximum 10 documents per test cycle
- **Use**: Existing processed data whenever possible
- **Alert**: Set up billing alerts for unexpected charges

### **Technical Risks**
- **OpenSearch Connectivity**: Verify VPC routing and security groups
- **FTS Query Performance**: Monitor query times and optimize if needed
- **Neptune Capacity**: Monitor Neptune cluster utilization
- **Layer Dependencies**: Test layer updates in isolation

### **Rollback Plans**
- **Layer Rollback**: Keep previous working layer versions available
- **Configuration Rollback**: Document all environment variable changes
- **Code Rollback**: Maintain clean git history for easy reversion

---

## 📋 **DECISION POINTS**

### **Immediate Decisions Needed**
1. **OpenSearch Endpoint**: Confirm the correct endpoint URL and access method
2. **Testing Scope**: Decide on initial test document set size
3. **Layer Deployment**: Choose deployment method (manual vs CDK)

### **Short-term Decisions Needed**
1. **Entity Types**: Which additional entity types to support first
2. **Ontology Priority**: GeoNames vs Climate Risk development order
3. **Performance Targets**: Acceptable query response times

### **Medium-term Decisions Needed**
1. **Scaling Strategy**: How to handle increased query volume
2. **Caching Strategy**: What to cache and for how long
3. **Monitoring Strategy**: Which metrics are most important

---

## 🔄 **ITERATIVE DEVELOPMENT APPROACH**

### **Sprint 1 (Days 1-3): Core Functionality**
1. Configure OpenSearch endpoint
2. Deploy updated layer
3. Test basic entity alignment
4. Verify TTL generation

### **Sprint 2 (Days 4-7): Error Handling & Logging**
1. Enhance error handling
2. Improve logging and debugging
3. Add basic performance metrics
4. Test edge cases

### **Sprint 3 (Days 8-14): Feature Enhancement**
1. Add climate risk ontology support
2. Implement contextual scoring
3. Optimize query performance
4. Expand test coverage

### **Sprint 4 (Days 15-21): Production Readiness**
1. Add monitoring and alerting
2. Implement comprehensive testing
3. Optimize costs and performance
4. Complete documentation

---

**Created**: August 15, 2025
**Priority**: Start with items 1-3 for immediate functionality
**Success Criteria**: Working end-to-end entity alignment pipeline with cost controls
**Next Review**: After completing immediate priorities (items 1-3)
