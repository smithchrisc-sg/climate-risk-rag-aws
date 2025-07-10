# NLP Entity to RDF Schema Mapping Analysis
## AWS Comprehend Entities → Established Ontologies for Climate Risk KG

**Date**: 2025-07-10  
**Purpose**: Map AWS Comprehend entity types to established RDF ontologies for Knowledge Graph integration  
**Status**: Analysis Complete - Ready for Implementation  

---

## 📊 COMPREHEND ENTITY ANALYSIS RESULTS

### **Entity Types Found in Climate Risk Text**
Based on analysis of sample climate risk content:

| Entity Type | Count | Confidence Range | Examples |
|-------------|-------|------------------|----------|
| **ORGANIZATION** | 11 | 0.801-0.999 | IPCC, ExxonMobil, EPA, World Bank |
| **LOCATION** | 11 | 0.555-0.999 | Miami, London, Brazil, Amazon rainforest |
| **PERSON** | 7 | 0.830-0.999 | Greta Thunberg, Dr. Sarah Johnson |
| **DATE** | 5 | 0.995-1.000 | December 15, 2023; 2050; 2030 |
| **QUANTITY** | 5 | 0.992-0.999 | $50 billion, 2.5°C, 55%, 12% |
| **TITLE** | 1 | 0.820 | Green Deal |

**Total Entities**: 40 across 6 types  
**Coverage**: Excellent for climate risk domain  

---

## 🎯 RDF ONTOLOGY MAPPING STRATEGY

### **1. PERSON Entities** 👥
**AWS Type**: `PERSON`  
**Primary Ontology**: **FOAF (Friend of a Friend)**  
**Climate Relevance**: Medium

```turtle
# RDF Mapping
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix schema: <https://schema.org/> .

:person_greta_thunberg a foaf:Person ;
    foaf:name "Greta Thunberg" ;
    foaf:givenName "Greta" ;
    foaf:familyName "Thunberg" ;
    schema:jobTitle "Climate Activist" ;
    :extractedFrom :chunk_123 ;
    :confidence 0.999 .
```

**Alternative Ontologies**:
- `schema:Person` (Schema.org)
- `vcard:Individual` (vCard)
- `dbo:Person` (DBpedia)

**Climate Extensions**:
- Climate expertise/role
- Organizational affiliations
- Publication authorship

### **2. ORGANIZATION Entities** 🏢
**AWS Type**: `ORGANIZATION`  
**Primary Ontology**: **FOAF + Schema.org**  
**Climate Relevance**: High

```turtle
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix schema: <https://schema.org/> .
@prefix climate: <http://climate-risk.org/ontology/> .

:org_ipcc a foaf:Organization, schema:Organization ;
    foaf:name "Intergovernmental Panel on Climate Change" ;
    schema:alternateName "IPCC" ;
    schema:organizationType "International Scientific Body" ;
    climate:organizationRole "Climate Science Authority" ;
    climate:carbonFootprint :ipcc_footprint ;
    :extractedFrom :chunk_456 ;
    :confidence 0.997 .
```

**Alternative Ontologies**:
- `org:Organization` (W3C Organization Ontology)
- `dbo:Organisation` (DBpedia)

**Climate Extensions**:
- Carbon footprint data
- Sustainability commitments
- Climate risk exposure
- Regulatory compliance

### **3. LOCATION Entities** 🌍
**AWS Type**: `LOCATION`  
**Primary Ontology**: **Schema.org + GeoNames**  
**Climate Relevance**: Very High

```turtle
@prefix schema: <https://schema.org/> .
@prefix geo: <http://www.w3.org/2003/01/geo/wgs84_pos#> .
@prefix climate: <http://climate-risk.org/ontology/> .

:location_miami a schema:Place ;
    schema:name "Miami" ;
    schema:addressCountry "United States" ;
    geo:lat "25.7617" ;
    geo:long "-80.1918" ;
    climate:seaLevelRisk "High" ;
    climate:temperatureProjection :miami_temp_projection ;
    climate:vulnerabilityScore 8.5 ;
    :extractedFrom :chunk_789 ;
    :confidence 0.999 .
```

**Alternative Ontologies**:
- `gn:Feature` (GeoNames)
- `dbo:Place` (DBpedia)
- `wgs84:SpatialThing`

**Climate Extensions**:
- Sea level rise projections
- Temperature change data
- Extreme weather risk
- Adaptation measures

### **4. DATE Entities** 📅
**AWS Type**: `DATE`  
**Primary Ontology**: **Time Ontology + Schema.org**  
**Climate Relevance**: High

```turtle
@prefix time: <http://www.w3.org/2006/time#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

:date_2050 a time:Instant ;
    time:inXSDDateTime "2050-01-01T00:00:00Z"^^xsd:dateTime ;
    schema:description "Climate projection target year" ;
    :temporalScope "Climate Projection" ;
    :extractedFrom :chunk_101 ;
    :confidence 0.997 .
```

**Alternative Ontologies**:
- `schema:Date`
- `dcterms:date` (Dublin Core)
- `time:TemporalEntity`

**Climate Extensions**:
- Projection timeframes
- Historical climate events
- Policy implementation dates
- Scientific publication dates

### **5. QUANTITY Entities** 📊
**AWS Type**: `QUANTITY`  
**Primary Ontology**: **QUDT (Quantities, Units, Dimensions and Types)**  
**Climate Relevance**: Very High

```turtle
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix unit: <http://qudt.org/vocab/unit/> .
@prefix schema: <https://schema.org/> .

:quantity_temperature_rise a qudt:Quantity ;
    qudt:numericValue 2.5 ;
    qudt:unit unit:DEG_C ;
    qudt:quantityKind :TemperatureChange ;
    schema:description "Global temperature rise projection" ;
    :measurementContext "Climate Projection" ;
    :extractedFrom :chunk_202 ;
    :confidence 0.992 .

:quantity_investment a qudt:Quantity ;
    qudt:numericValue 50000000000 ;
    qudt:unit unit:USD ;
    qudt:quantityKind :MonetaryAmount ;
    schema:description "Renewable energy investment" ;
    :extractedFrom :chunk_303 ;
    :confidence 0.999 .
```

**Alternative Ontologies**:
- `schema:QuantitativeValue`
- `om:Quantity` (Ontology of units of Measure)
- `uo:UO` (Units Ontology)

**Climate Extensions**:
- Temperature measurements
- Emission quantities
- Financial investments
- Percentage changes

### **6. TITLE/OTHER Entities** 📋
**AWS Type**: `TITLE`, `OTHER`  
**Primary Ontology**: **SKOS (Simple Knowledge Organization System)**  
**Climate Relevance**: Medium

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix climate: <http://climate-risk.org/ontology/> .

:concept_green_deal a skos:Concept ;
    skos:prefLabel "Green Deal" ;
    skos:altLabel "European Green Deal" ;
    skos:definition "EU policy framework for climate neutrality" ;
    skos:broader :climate_policy ;
    skos:inScheme :climate_concepts ;
    :extractedFrom :chunk_404 ;
    :confidence 0.820 .
```

---

## 🏗️ RECOMMENDED ONTOLOGY STACK

### **Core Foundation Ontologies** (High Priority)

#### **1. FOAF (Friend of a Friend)**
```turtle
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
```
- **Purpose**: People and organizations
- **Key Classes**: `foaf:Person`, `foaf:Organization`, `foaf:Agent`
- **Use Cases**: Authors, researchers, institutions, companies
- **Priority**: **High** - Essential for entity relationships

#### **2. Schema.org**
```turtle
@prefix schema: <https://schema.org/> .
```
- **Purpose**: General structured data vocabulary
- **Key Classes**: `schema:Person`, `schema:Organization`, `schema:Place`, `schema:Event`
- **Use Cases**: Rich metadata, search engine optimization
- **Priority**: **High** - Broad compatibility and adoption

#### **3. Dublin Core Terms**
```turtle
@prefix dcterms: <http://purl.org/dc/terms/> .
```
- **Purpose**: Document and resource metadata
- **Key Classes**: `dcterms:BibliographicResource`, `dcterms:Agent`
- **Use Cases**: Document provenance, authorship, publication info
- **Priority**: **High** - Critical for document refactoring

#### **4. SKOS (Simple Knowledge Organization System)**
```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
```
- **Purpose**: Concept hierarchies and taxonomies
- **Key Classes**: `skos:Concept`, `skos:ConceptScheme`
- **Use Cases**: Climate terminology, policy concepts
- **Priority**: **Medium** - Important for concept organization

### **Climate-Specific Ontologies** (Domain Extensions)

#### **1. QUDT (Quantities, Units, Dimensions and Types)**
```turtle
@prefix qudt: <http://qudt.org/schema/qudt/> .
@prefix unit: <http://qudt.org/vocab/unit/> .
```
- **Purpose**: Measurements and scientific quantities
- **Key Classes**: `qudt:Quantity`, `qudt:Unit`, `qudt:QuantityKind`
- **Use Cases**: Temperature, emissions, financial amounts
- **Priority**: **High** - Essential for climate data

#### **2. Time Ontology**
```turtle
@prefix time: <http://www.w3.org/2006/time#> .
```
- **Purpose**: Temporal relationships and intervals
- **Key Classes**: `time:Instant`, `time:Interval`, `time:TemporalEntity`
- **Use Cases**: Climate projections, historical events
- **Priority**: **Medium** - Important for temporal data

#### **3. GeoSPARQL**
```turtle
@prefix geo: <http://www.opengis.net/ont/geosparql#> .
@prefix wgs84: <http://www.w3.org/2003/01/geo/wgs84_pos#> .
```
- **Purpose**: Spatial relationships and geographic data
- **Key Classes**: `geo:Feature`, `geo:Geometry`, `wgs84:SpatialThing`
- **Use Cases**: Location-based climate risks, spatial analysis
- **Priority**: **Medium** - Valuable for geographic analysis

---

## 📋 DOCUMENT SCHEMA REFACTORING

### **Current vs. Recommended Document Properties**

| Current Property | Dublin Core Term | RDF Property | Benefits |
|------------------|------------------|--------------|----------|
| `title` | Title | `dcterms:title` | Standardized metadata |
| `author` | Creator | `dcterms:creator` | Linked to foaf:Person |
| `date` | Created | `dcterms:created` | Temporal relationships |
| `source` | Source | `dcterms:source` | Provenance tracking |
| `description` | Description | `dcterms:description` | Rich text descriptions |
| `subject` | Subject | `dcterms:subject` | Topic classification |
| `publisher` | Publisher | `dcterms:publisher` | Publication info |
| `type` | Type | `dcterms:type` | Resource categorization |

### **Enhanced Document Schema Example**
```turtle
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix schema: <https://schema.org/> .

:document_ipcc_report_2023 a dcterms:BibliographicResource ;
    dcterms:title "Climate Change 2023: Synthesis Report" ;
    dcterms:creator :person_sarah_johnson ;
    dcterms:created "2023-12-15"^^xsd:date ;
    dcterms:publisher :org_ipcc ;
    dcterms:subject :climate_change, :global_warming ;
    dcterms:description "Comprehensive assessment of climate science" ;
    dcterms:source <https://ipcc.ch/report/ar6/syr/> ;
    dcterms:type "Scientific Report" ;
    schema:inLanguage "en" ;
    :hasChunk :chunk_001, :chunk_002, :chunk_003 .
```

---

## 🔗 ENTITY LINKING STRATEGY

### **NLP Results → KG Integration Pipeline**

#### **1. Entity Extraction & Normalization**
```python
# From NLP Worker
nlp_entity = {
    'text': 'Intergovernmental Panel on Climate Change',
    'type': 'ORGANIZATION',
    'confidence': 0.997,
    'begin_offset': 4,
    'end_offset': 43,
    'chunk_id': 'chunk_456'
}

# Normalized Entity
normalized_entity = {
    'canonical_name': 'IPCC',
    'full_name': 'Intergovernmental Panel on Climate Change',
    'entity_type': 'ORGANIZATION',
    'rdf_type': 'foaf:Organization',
    'confidence': 0.997,
    'source_chunk': 'chunk_456'
}
```

#### **2. Entity Resolution & Linking**
```python
# Entity Resolution Process
def resolve_entity(nlp_entity):
    # 1. Check existing KG nodes
    existing_node = query_kg_for_entity(nlp_entity['text'])
    
    if existing_node:
        # Link to existing node
        return link_to_existing(nlp_entity, existing_node)
    else:
        # Create new node with proper ontology
        return create_new_kg_node(nlp_entity)

# KG Node Creation
def create_kg_node(entity):
    if entity['type'] == 'ORGANIZATION':
        return create_organization_node(entity)
    elif entity['type'] == 'PERSON':
        return create_person_node(entity)
    # ... etc
```

#### **3. Chunk-Entity Relationships**
```turtle
# Link entities to content chunks
:chunk_456 a :TextChunk ;
    :containsEntity :org_ipcc ;
    :entityMention [
        :mentionText "Intergovernmental Panel on Climate Change" ;
        :startOffset 4 ;
        :endOffset 43 ;
        :confidence 0.997
    ] .

:org_ipcc a foaf:Organization ;
    foaf:name "Intergovernmental Panel on Climate Change" ;
    :mentionedIn :chunk_456 .
```

---

## 🛠️ IMPLEMENTATION ROADMAP

### **Phase 1: Core Ontology Setup** (Week 1-2)
- [ ] **Namespace Configuration**
  - Set up FOAF, Schema.org, Dublin Core prefixes
  - Configure Neptune/RDF store with ontology imports
  - Create base entity classes and properties

- [ ] **Document Schema Migration**
  - Refactor document properties to Dublin Core terms
  - Update database schema and Lambda functions
  - Migrate existing document metadata

### **Phase 2: Entity Mapping Implementation** (Week 3-4)
- [ ] **NLP-to-RDF Mapper**
  - Create entity type mapping service
  - Implement confidence thresholding
  - Add entity normalization and deduplication

- [ ] **KG Integration Service**
  - Build entity resolution pipeline
  - Implement chunk-entity linking
  - Create entity relationship inference

### **Phase 3: Climate Extensions** (Week 5-6)
- [ ] **QUDT Integration**
  - Add quantity and measurement support
  - Implement unit conversion and normalization
  - Create climate-specific quantity types

- [ ] **Temporal and Spatial Data**
  - Integrate Time Ontology for dates
  - Add GeoSPARQL for location data
  - Implement climate risk spatial relationships

### **Phase 4: SKOS Concept Hierarchy** (Week 7-8)
- [ ] **Climate Terminology**
  - Create SKOS concept scheme for climate terms
  - Build hierarchical relationships
  - Implement concept-entity linking

- [ ] **Quality Assurance**
  - Entity linking accuracy validation
  - Performance optimization
  - Documentation and testing

---

## 📊 EXPECTED BENEFITS

### **Knowledge Graph Enhancement**
- **Rich Semantic Relationships**: Entities linked with standardized properties
- **Interoperability**: Compatible with external knowledge bases
- **Query Capabilities**: Complex SPARQL queries across entity types
- **Inference**: Automatic relationship discovery

### **Search and Discovery**
- **Entity-Based Search**: Find documents by people, organizations, locations
- **Temporal Queries**: Search by time periods and date ranges
- **Quantitative Analysis**: Query by measurements and quantities
- **Concept Navigation**: Browse related climate concepts

### **Data Quality**
- **Standardized Metadata**: Consistent document properties
- **Entity Deduplication**: Unified entity representations
- **Provenance Tracking**: Clear data lineage and sources
- **Confidence Scoring**: Quality metrics for entity extraction

---

## 🎯 SUCCESS METRICS

### **Technical Metrics**
- **Entity Linking Accuracy**: >85% correct entity resolution
- **Coverage**: >90% of NLP entities successfully mapped
- **Performance**: <500ms entity resolution latency
- **Data Quality**: <5% duplicate entities in KG

### **Functional Metrics**
- **Query Richness**: Support for complex multi-entity queries
- **Relationship Discovery**: Automatic inference of entity relationships
- **Search Relevance**: Improved search results through entity understanding
- **User Experience**: Intuitive entity-based navigation

This comprehensive mapping provides the foundation for transforming your NLP results into a rich, semantically-aware Knowledge Graph using established RDF ontologies and best practices.
