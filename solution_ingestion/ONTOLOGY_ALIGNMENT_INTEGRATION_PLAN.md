# Ontology Alignment Integration Plan
**Created**: 2025-12-02  
**Status**: Phase 1 In Progress (210/567 solutions processed)  
**Next Phase**: Search Lambda Integration

## Executive Summary

We are migrating from messy, manually-assigned risk/solution types to clean, ontology-based concepts extracted via LLM. This document outlines the current state, what's running, and the plan for integrating the new ontology-based predicates into the search lambda.

---

## Current State

### What We Have

**1. Rich Ontology Loaded in Neptune**
- Location: `/Users/chris/climate-risk-rag-aws/docs/ontology/`
- Files loaded:
  - `RISK_TAXONOMY_V1.ttl` - 50+ risk concepts with hierarchy (FloodRisk → Urban Flood, Coastal Flood, etc.)
  - `MECHANISM_IMPACT_TEMPORAL_V1.ttl` - 40+ mechanism concepts (Parametric Insurance, Microinsurance, etc.)
  - `SOLUTION_IMPACT_ONTOLOGY_V1.ttl` - Impact concepts
  - `GEOGRAPHIC_EVIDENCE_V1.ttl` - Geographic concepts
- All concepts have `rdfs:label` properties for display

**2. Ontology Alignment Batch Job**
- Location: `/Users/chris/climate-risk-rag-aws/solution_ingestion/ontology_alignment_batch.py`
- Status: **RUNNING** - Processing 567 solutions (210 completed as of 2025-12-02 10:20 PST)
- What it does:
  - Extracts risks, mechanisms, impacts from solution text using Claude 3 Haiku
  - Enhances with rule-based extraction
  - Generates RDF with direct assertions and provenance
  - Loads to Neptune via `bulk_insert_ttl()`
- Output predicates:
  - `sg:addressesRisk` - Links solution to risk concepts
  - `sg:providesMechanism` - Links solution to mechanism concepts
  - `sg:hasImpact` - Links solution to impact concepts
  - `sgm:hasAlignment` - Links to extraction metadata with confidence scores

**3. Existing Messy Data (To Be Cleaned)**
- Old predicates from harvester:
  - `sg:riskType` - 16 messy values (e.g., `RiskType_earthquakes_typhoons`, `RiskType_cannot_be_determined`)
  - `sg:solutionType` - 13 messy values (e.g., `SolutionType_risk_financing_increase_penetration`)
- Problems:
  - Compound values (multiple concepts concatenated)
  - Inconsistent naming
  - No hierarchy or structure
  - Created by external harvester without KG knowledge

---

## Architecture Details

### Knowledge Graph Structure

**Solution URIs**: `sg:Document_sol_007deb73819fda29b`
- Type: `sgd:Solution` (document-structure namespace)
- Already exist from original document processing

**New Triples Added by Alignment**:
```turtle
# Direct assertions (what queries need)
sg:Document_sol_007deb73819fda29b
    sg:addressesRisk sg:EarthquakeRisk, sg:TsunamiRisk ;
    sg:providesMechanism sg:ParametricInsurance, sg:GovernmentReinsurance ;
    sg:hasImpact sg:IncreasedResilience ;
    sgm:hasAlignment sgm:alignment_sol_007deb73819fda29b .

# Provenance metadata
sgm:alignment_sol_007deb73819fda29b
    a sgm:OntologyAlignment ;
    sgm:extractionMethod "llm+rules" ;
    sgm:overallConfidence "0.9833"^^xsd:decimal ;
    dcterms:created "2025-12-02T16:27:09Z"^^xsd:dateTime ;
    sgm:hasExtraction sgm:extraction_risk_sol_007deb73819fda29b_001, ... .

# Extraction details (for auditing)
sgm:extraction_risk_sol_007deb73819fda29b_001
    a sgm:RiskExtraction ;
    sgm:extractedConcept sg:EarthquakeRisk ;
    sgm:confidence "1.0000"^^xsd:decimal ;
    sgm:evidence "damages caused by events such as fire, destruction..." ;
    sgm:sourceChunk sg:Chunk_sol_007deb73819fda29b_0004 ;
    sgm:extractionMethod "llm" .
```

### Namespaces
```turtle
PREFIX sg: <http://solve.global/knowledge-commons/>
PREFIX sgm: <http://solve.global/knowledge-commons/process-metadata#>
PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
```

---

## Phase 1: Data Cleanup (In Progress)

### Step 1: Complete Batch Processing ✅ (In Progress)
- **Status**: 210/567 solutions processed
- **ETA**: ~2-3 hours remaining
- **Command**: `python3 ontology_alignment_batch.py --load-to-neptune`
- **Location**: Running on ec2-dev in VPC

### Step 2: Find Missing Concepts (Next)
After batch completes, find LLM-invented concepts without labels:

```sparql
PREFIX sg: <http://solve.global/knowledge-commons/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?concept WHERE {
  {
    ?solution sg:addressesRisk ?concept .
  } UNION {
    ?solution sg:providesMechanism ?concept .
  } UNION {
    ?solution sg:hasImpact ?concept .
  }
  FILTER NOT EXISTS { ?concept rdfs:label ?label }
}
ORDER BY ?concept
```

**Action**: Review list, add valid concepts to ontology files, reload ontology

### Step 3: Migrate Old Predicates to New (Next)

**Risk Type Migration**:
```sparql
# Clean mappings
DELETE { ?s sg:riskType sg:RiskType_natural_catastrophe }
INSERT { ?s sg:addressesRisk sg:NaturalCatastropheRisk }
WHERE { ?s sg:riskType sg:RiskType_natural_catastrophe }

DELETE { ?s sg:riskType sg:RiskType_health }
INSERT { ?s sg:addressesRisk sg:HealthRisk }
WHERE { ?s sg:riskType sg:RiskType_health }

DELETE { ?s sg:riskType sg:RiskType_cyber }
INSERT { ?s sg:addressesRisk sg:CyberRisk }
WHERE { ?s sg:riskType sg:RiskType_cyber }

DELETE { ?s sg:riskType sg:RiskType_mortality }
INSERT { ?s sg:addressesRisk sg:MortalityRisk }
WHERE { ?s sg:riskType sg:RiskType_mortality }

DELETE { ?s sg:riskType sg:RiskType_retirement }
INSERT { ?s sg:addressesRisk sg:RetirementRisk }
WHERE { ?s sg:riskType sg:RiskType_retirement }

# Compound values - split
DELETE { ?s sg:riskType sg:RiskType_earthquakes_typhoons }
INSERT { 
  ?s sg:addressesRisk sg:EarthquakeRisk .
  ?s sg:addressesRisk sg:TyphoonRisk 
}
WHERE { ?s sg:riskType sg:RiskType_earthquakes_typhoons }

# Keep "cannot_be_determined" as TODO flag ONLY where no LLM extraction
DELETE { ?s sg:riskType sg:RiskType_cannot_be_determined }
WHERE { 
  ?s sg:riskType sg:RiskType_cannot_be_determined .
  ?s sg:addressesRisk ?anyRisk .
}
```

**Solution Type Migration**:
```sparql
# Clean mappings
DELETE { ?s sg:solutionType sg:SolutionType_risk_financing }
INSERT { ?s sg:providesMechanism sg:RiskFinancing }
WHERE { ?s sg:solutionType sg:SolutionType_risk_financing }

DELETE { ?s sg:solutionType sg:SolutionType_risk_reduction }
INSERT { ?s sg:providesMechanism sg:RiskReduction }
WHERE { ?s sg:solutionType sg:SolutionType_risk_reduction }

DELETE { ?s sg:solutionType ?old }
INSERT { ?s sg:providesMechanism sg:IncreasePenetration }
WHERE { 
  ?s sg:solutionType ?old .
  FILTER(?old IN (sg:SolutionType_increase_penetration, sg:SolutionType_increased_penetration))
}

DELETE { ?s sg:solutionType sg:SolutionType_raising_awareness }
INSERT { ?s sg:providesMechanism sg:RaisingAwareness }
WHERE { ?s sg:solutionType sg:SolutionType_raising_awareness }

DELETE { ?s sg:solutionType sg:SolutionType_regulation }
INSERT { ?s sg:providesMechanism sg:Regulation }
WHERE { ?s sg:solutionType sg:SolutionType_regulation }

# Compound values - split
DELETE { ?s sg:solutionType ?compound }
INSERT { 
  ?s sg:providesMechanism sg:RiskFinancing .
  ?s sg:providesMechanism sg:IncreasePenetration 
}
WHERE { 
  ?s sg:solutionType ?compound .
  FILTER(CONTAINS(STR(?compound), "risk_financing") && CONTAINS(STR(?compound), "penetration"))
}

DELETE { ?s sg:solutionType ?compound }
INSERT { 
  ?s sg:providesMechanism sg:RiskReduction .
  ?s sg:providesMechanism sg:RiskFinancing 
}
WHERE { 
  ?s sg:solutionType ?compound .
  FILTER(CONTAINS(STR(?compound), "risk_reduction") && CONTAINS(STR(?compound), "risk_financing"))
}

# Keep "cannot_be_determined" as TODO flag
DELETE { ?s sg:solutionType sg:SolutionType_cannot_be_determined }
WHERE { 
  ?s sg:solutionType sg:SolutionType_cannot_be_determined .
  ?s sg:providesMechanism ?anyMechanism .
}
```

---

## Phase 2: Search Lambda Integration (Next)

### Overview
Update `/Users/chris/climate-risk-rag-aws/lambda/search/src/search/solution_searcher.py` to use new ontology-based predicates with hierarchical filtering.

### Key Changes Required

**1. Update Filter Mappings** (lines ~27-45)

**OLD**:
```python
filter_mappings = {
    'solution_category': {
        'natural-catastrophe': 'sg:RiskType_natural_catastrophe',
        'cyber': 'sg:RiskType_cyber',
        'health': 'sg:RiskType_health',
        'retirement': 'sg:RiskType_retirement',
        'mortality': 'sg:RiskType_mortality'
    },
    'solution_type': {
        'risk-reduction': 'sg:SolutionType_risk_reduction',
        'risk-financing': 'sg:SolutionType_risk_financing',
        'increase-penetration': 'sg:SolutionType_increase_penetration',
        'raising-awareness': 'sg:SolutionType_raising_awareness',
        'leveraging-technology': 'sg:SolutionType_leveraging_technology',
        'regulation': 'sg:SolutionType_regulation'
    }
}
```

**NEW**:
```python
filter_mappings = {
    'solution_category': {
        'natural-catastrophe': 'sg:NaturalCatastropheRisk',
        'cyber': 'sg:CyberRisk',
        'health': 'sg:HealthRisk',
        'retirement': 'sg:RetirementRisk',
        'mortality': 'sg:MortalityRisk'
    },
    'solution_type': {
        'risk-reduction': 'sg:RiskReduction',
        'risk-financing': 'sg:RiskFinancing',
        'increase-penetration': 'sg:IncreasePenetration',
        'raising-awareness': 'sg:RaisingAwareness',
        'leveraging-technology': 'sg:LeveragingTechnology',
        'regulation': 'sg:Regulation'
    }
}
```

**2. Update Filter Query Building** (in `_build_solution_universe_query()`)

**OLD** (exact match):
```python
if 'solution_category' in filters:
    categories = filters['solution_category']
    mapped_categories = [filter_mappings['solution_category'][cat] for cat in categories]
    filter_conditions.append(f"  ?solution sg:riskType ?risk_type .")
    filter_conditions.append(f"  FILTER(?risk_type IN ({', '.join(mapped_categories)}))")
```

**NEW** (hierarchical match):
```python
if 'solution_category' in filters:
    categories = filters['solution_category']
    risk_uris = [filter_mappings['solution_category'][cat] for cat in categories]
    filter_conditions.append(f"""
      ?solution sg:addressesRisk ?risk .
      ?risk rdfs:subClassOf* ?riskCategory .
      FILTER(?riskCategory IN ({', '.join(risk_uris)}))
    """)

if 'solution_type' in filters:
    types = filters['solution_type']
    mechanism_uris = [filter_mappings['solution_type'][t] for t in types]
    filter_conditions.append(f"""
      ?solution sg:providesMechanism ?mechanism .
      ?mechanism rdfs:subClassOf* ?mechanismCategory .
      FILTER(?mechanismCategory IN ({', '.join(mechanism_uris)}))
    """)
```

**3. Update Solution Content Retrieval** (in `get_solution_content()` method, lines ~240-290)

**OLD**:
```sparql
OPTIONAL { ?solution sg:riskType ?riskType }
OPTIONAL { ?solution sg:solutionType ?solutionType }

# Risk type labels
OPTIONAL { 
  ?solution sg:riskType ?riskType .
  ?riskType rdfs:label ?risk_type_label 
}

# Solution type labels
OPTIONAL { 
  ?solution sg:solutionType ?solutionType .
  ?solutionType rdfs:label ?solution_type_label 
}
```

**NEW**:
```sparql
# New ontology-based predicates
OPTIONAL {
    ?solution sg:addressesRisk ?risk .
    ?risk rdfs:label ?risk_label .
}

OPTIONAL {
    ?solution sg:providesMechanism ?mechanism .
    ?mechanism rdfs:label ?mechanism_label .
}

OPTIONAL {
    ?solution sg:hasImpact ?impact .
    ?impact rdfs:label ?impact_label .
}

# Extraction metadata
OPTIONAL {
    ?solution sgm:hasAlignment ?alignment .
    ?alignment sgm:overallConfidence ?extraction_confidence ;
               dcterms:created ?extraction_date .
}
```

**4. Update API Response Format** (in `_convert_solution_to_api_format()`)

**OLD**:
```python
"risk_types_addressed": ["Natural Catastrophe"],  # Simple strings
"solution_types": ["Risk Reduction"]
```

**NEW**:
```python
"risks_addressed": [
    {"uri": "sg:EarthquakeRisk", "label": "Earthquake Risk"},
    {"uri": "sg:TsunamiRisk", "label": "Tsunami Risk"}
],
"mechanisms_provided": [
    {"uri": "sg:ParametricInsurance", "label": "Parametric Insurance"},
    {"uri": "sg:GovernmentReinsurance", "label": "Government Reinsurance"}
],
"impacts": [
    {"uri": "sg:IncreasedResilience", "label": "Increased Resilience"}
],
"extraction_confidence": 0.9833,
"extraction_date": "2025-12-02T16:27:09Z"
```

**5. Update Count Queries** (in `_get_solution_count()` method)

Replace `sg:riskType` and `sg:solutionType` with `sg:addressesRisk` and `sg:providesMechanism` in count queries.

### Benefits of Hierarchical Filtering

**Example**: User filters by "Natural Catastrophe"

**OLD**: Only finds solutions with exact `RiskType_natural_catastrophe`

**NEW**: Finds solutions with ANY subclass:
- FloodRisk (and Urban Flood, Coastal Flood, Riverine Flood, etc.)
- EarthquakeRisk (and Structural Earthquake, Liquefaction, etc.)
- TyphoonRisk, DroughtRisk, WildfireRisk, etc.

**Result**: Much more comprehensive and accurate results!

---

## Implementation Timeline

### Phase 1: Data Cleanup (Current)
- ✅ Ontology loaded to Neptune
- ✅ Batch job running (210/567 complete)
- ⏳ Wait for batch completion (~2-3 hours)
- ⏳ Find and add missing concepts to ontology
- ⏳ Run SPARQL migration scripts
- ⏳ Validate all solutions have new predicates

**Estimated Time**: 4-6 hours total (including batch processing)

### Phase 2: Search Lambda Integration (Next)
- Update filter mappings
- Update SPARQL queries with hierarchical filtering
- Update API response format
- Test all filter combinations
- Deploy to Lambda

**Estimated Time**: 2-3 hours coding + 1-2 hours testing

### Phase 3: Harvester Update (Q1 2025)
- Update solution harvester to output ontology concepts directly
- Next quarterly crawl produces clean data from start
- No more cleanup needed

---

## Testing & Validation

### After Phase 1 Cleanup

**1. Verify all solutions have new predicates**:
```sparql
# Count solutions with new predicates
SELECT (COUNT(DISTINCT ?solution) as ?withNew) WHERE {
  ?solution a sgd:Solution .
  ?solution sg:addressesRisk ?risk .
}

# Count solutions with old predicates still
SELECT (COUNT(DISTINCT ?solution) as ?withOld) WHERE {
  ?solution a sgd:Solution .
  ?solution sg:riskType ?oldRisk .
  FILTER(?oldRisk != sg:RiskType_cannot_be_determined)
}
```

**2. Verify concept labels exist**:
```sparql
# Should return 0
SELECT (COUNT(DISTINCT ?concept) as ?missingLabels) WHERE {
  ?solution sg:addressesRisk ?concept .
  FILTER NOT EXISTS { ?concept rdfs:label ?label }
}
```

**3. Test hierarchical queries**:
```sparql
# Should find all flood-related solutions
SELECT ?solution ?risk ?label WHERE {
  ?solution sg:addressesRisk ?risk .
  ?risk rdfs:subClassOf* sg:FloodRisk .
  ?risk rdfs:label ?label .
}
```

### After Phase 2 Lambda Update

**1. Test each filter category**:
- Natural Catastrophe filter returns results
- Cyber filter returns results
- Health filter returns results
- Etc.

**2. Test hierarchical filtering**:
- Natural Catastrophe filter finds flood, earthquake, typhoon solutions
- Risk Financing filter finds parametric insurance, microinsurance, etc.

**3. Validate API response**:
- New fields present: `risks_addressed`, `mechanisms_provided`, `impacts`
- Extraction metadata present: `extraction_confidence`, `extraction_date`
- Labels are human-readable

**4. Performance testing**:
- Query times acceptable with hierarchical filtering
- No timeout issues with `rdfs:subClassOf*` queries

---

## Key Files & Locations

### Ontology Files
- `/Users/chris/climate-risk-rag-aws/docs/ontology/RISK_TAXONOMY_V1.ttl`
- `/Users/chris/climate-risk-rag-aws/docs/ontology/MECHANISM_IMPACT_TEMPORAL_V1.ttl`
- `/Users/chris/climate-risk-rag-aws/docs/ontology/SOLUTION_IMPACT_ONTOLOGY_V1.ttl`
- `/Users/chris/climate-risk-rag-aws/docs/ontology/GEOGRAPHIC_EVIDENCE_V1.ttl`

### Batch Processing
- `/Users/chris/climate-risk-rag-aws/solution_ingestion/ontology_alignment_batch.py`
- `/Users/chris/climate-risk-rag-aws/solution_ingestion/extractors/llm_extractor.py`
- `/Users/chris/climate-risk-rag-aws/solution_ingestion/extractors/rule_enhancer.py`
- `/Users/chris/climate-risk-rag-aws/solution_ingestion/generators/alignment_rdf_generator.py`

### Search Lambda
- `/Users/chris/climate-risk-rag-aws/lambda/search/src/search/solution_searcher.py`
- `/Users/chris/climate-risk-rag-aws/lambda/search/src/search/coordinator.py`

### Neptune Connection
- **Endpoint**: `solve-global-kr-neptune-s3.cluster-cqhsckw0edl1.us-east-1.neptune.amazonaws.com`
- **Port**: 8182
- **Access**: VPC-only (use ec2-dev bastion)

---

## Important Notes

### Hard Cutover Strategy
- No backward compatibility needed
- Partner aware of potential downtime during active development
- Clean, simple implementation

### "Cannot Be Determined" Flags
- Keep `sg:RiskType_cannot_be_determined` and `sg:SolutionType_cannot_be_determined` ONLY for solutions where LLM found nothing
- Acts as TODO flag for manual review
- Query to find them:
  ```sparql
  SELECT ?solution WHERE {
    ?solution sg:riskType sg:RiskType_cannot_be_determined .
    FILTER NOT EXISTS { ?solution sg:addressesRisk ?risk }
  }
  ```

### LLM-Invented Concepts
- Claude may create concepts not in ontology (e.g., `sg:CappedReinsurancePayouts`)
- These won't have `rdfs:label` properties initially
- Review list after batch completes
- Add valid concepts to ontology, ignore invalid ones

### Ontology Hierarchy
- Use `rdfs:subClassOf*` for transitive hierarchy queries
- Enables powerful filtering (e.g., "Natural Catastrophe" finds all subtypes)
- Test performance with large result sets

---

## Next Steps Checklist

When resuming work:

1. ✅ Check batch job status: `ps aux | grep ontology_alignment_batch`
2. ⏳ If complete, run missing concepts query
3. ⏳ Review and add valid concepts to ontology
4. ⏳ Run SPARQL migration scripts
5. ⏳ Validate cleanup with test queries
6. ⏳ Update search lambda code
7. ⏳ Test search functionality
8. ⏳ Deploy to Lambda
9. ⏳ Validate with partner

---

## Contact & Context

**Project**: GAIP Knowledge Repository Search API  
**Customer**: Global Asia Insurance Partnership  
**Environment**: AWS us-east-1  
**Branch**: `feature/climate-risk-ontology-filtering`  
**Last Commit**: Ontology alignment batch processing implementation

**Key Decisions Made**:
- Hard cutover (no backward compatibility)
- Keep "cannot_be_determined" as TODO flags
- Use hierarchical filtering with `rdfs:subClassOf*`
- LLM-invented concepts reviewed and added to ontology
- Quarterly harvester updates (next: Q1 2025)

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-02 10:20 PST  
**Status**: Phase 1 in progress, Phase 2 ready to implement
