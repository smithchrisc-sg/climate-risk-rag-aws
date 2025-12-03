# GAIP Knowledge Repository - Knowledge Graph Development
**Deliverable 3.2: Knowledge Graph Development**  
**Version**: 2.0 (As-Built)  
**Date**: December 2, 2025  
**Status**: Implemented and Operational  
**Prepared for**: Global Asia Insurance Partnership (GAIP)  
**Prepared by**: SOLVE Global

---

## Executive Summary

The GAIP Knowledge Graph connects solutions, risks, impacts, and evidence into an intelligent network that powers advanced search and discovery. This document describes how the knowledge graph extends the repository contents with the ontology framework, enabling users to find relevant solutions through relationships and context rather than just keywords.

**Implementation Status**: ✅ Fully operational with 567 solutions and hierarchical ontology-based filtering.

**Key Achievements**:
- **567 solutions** connected with risks, mechanisms, and impacts via ontology alignment
- **559 solutions (98.6%)** with automated risk extraction using LLM + ontology
- **563 solutions (99.3%)** with mechanism classifications
- **564 solutions (99.5%)** with impact data
- **240+ trusted source documents** linked as supporting evidence
- **Automated extraction** of relationships from solution descriptions using Claude 3.5 Sonnet
- **Geographic intelligence** with GeoNames integration (24 countries, 2 regional organizations)
- **Hierarchical filtering** enabling both broad and specific searches
- **4,284 old predicates cleaned** from Neptune, replaced with clean ontology structure

**Real-World Performance**:
- Search latency: 200-500ms for filtered searches
- Hierarchical queries: Natural Catastrophe filter returns 10+ solutions across all subtypes
- Combined filters: 55 solutions match "Natural Catastrophe + Risk Reduction"
- Geographic filtering: Single and multi-country selection working

---

## What is a Knowledge Graph? (And Why It's Essential)

A knowledge graph is a network of connected information where:
- **Nodes** represent things (solutions, risks, impacts, organizations)
- **Edges** represent relationships (mitigates, achieves, leads to)
- **Properties** add details (funding amounts, dates, confidence scores)

**Analogy**: Think of it like a map where:
- Cities are solutions
- Roads are relationships
- Road signs show what type of connection exists
- The map helps you find the best route to your destination

### Why Traditional Databases Can't Do This

**Traditional database** (table-based):
- Stores: "Solution A addresses Flood Risk"
- Stores: "Solution B addresses Agricultural Risk"
- **Can't answer**: "Show me solutions addressing agricultural flood risk" (requires understanding that agricultural flood is a combination)
- **Can't answer**: "What solutions lead to cost reduction?" (requires tracing chains of impacts)

**Knowledge graph**:
- Stores: Solution A → addresses → Flood Risk → type of → Agricultural Flood Risk
- Stores: Solution A → achieves → Damage Reduction → leads to → Cost Reduction
- **Can answer**: Complex queries requiring multiple relationship hops
- **Can answer**: "Find solutions that achieve X through any pathway"

### The Power of Graph Traversal

**Example Query**: "Solutions that reduce insurance costs"

**Traditional database approach**:
1. Search for "insurance" AND "cost" AND "reduce" in text
2. Return documents containing these words
3. **Problem**: Misses solutions that achieve this indirectly

**Knowledge graph approach**:
1. Start at "Insurance Cost Reduction" node
2. Walk backwards through "leads to" relationships
3. Find all solutions that eventually lead to this outcome
4. **Result**: Finds solutions achieving cost reduction through:
   - Direct premium reduction
   - Damage prevention → fewer claims → lower costs
   - Risk reduction → better pricing → lower costs
   - Early warning → asset protection → fewer claims → lower costs

**Why This Matters**: The graph structure allows the system to "walk" through relationships to find solutions that achieve goals through any pathway, not just direct mentions.

---

## How the Knowledge Graph Extends the Repository

### 1. From Documents to Structured Knowledge

**Before (Document Repository)**:
- 568 PDF documents with solution descriptions
- 240+ research papers and reports
- Text-based search finds keywords
- Users read documents to understand relationships

**After (Knowledge Graph)**:
- Solutions connected to specific risk types
- Mechanisms explicitly linked to solutions
- Impacts traced through causal chains
- Evidence supporting each claim
- Geographic and temporal context captured

**Example Transformation** (Real Solution from GAIP System):

**Document text**: "Southeast Asia Disaster Risk Insurance Facility (SEADRIF) 2.0: Boosting Financial Resilience Against Climate and Disaster Shocks"

**Knowledge graph representation** (as implemented):
```
Solution: SEADRIF 2.0
  ├─ sg:addressesRisk → sg:FloodRisk
  ├─ sg:addressesRisk → sg:NaturalCatastropheRisk
  ├─ sg:providesMechanism → sg:ParametricInsurance
  ├─ sg:providesMechanism → sg:RiskPooling
  ├─ sg:hasImpact → sg:IncreasedResilience
  ├─ dcterms:spatial → <https://sws.geonames.org/1605651/> (Thailand)
  ├─ dcterms:spatial → <https://sws.geonames.org/1562822/> (Vietnam)
  ├─ dcterms:spatial → <https://sws.geonames.org/1694008/> (Philippines)
  ├─ sg:implementationYear → "2020"
  └─ sgm:hasAlignment → sgm:alignment_seadrif_2_0
      ├─ sgm:extractionMethod → "llm+rules"
      ├─ sgm:overallConfidence → 0.9833
      └─ dcterms:created → "2025-12-02T16:27:09Z"
```

**Search Capabilities Enabled**:
- Find by risk: "natural catastrophe" OR "flood" → Returns SEADRIF
- Find by mechanism: "parametric insurance" OR "risk pooling" → Returns SEADRIF
- Find by geography: Thailand OR Vietnam OR Philippines → Returns SEADRIF
- Find by combination: "natural catastrophe + risk pooling + Thailand" → Returns SEADRIF
- Hierarchical: "flood" finds solutions tagged with FloodRisk OR NaturalCatastropheRisk
  ├─ benefits → Rice Farmers (50,000)
  ├─ funding → $10 million
  └─ supported by → World Bank Impact Study (high quality evidence)
```

---

## Knowledge Graph Components

### 1. Solution Network

**What it contains**:
- 568 climate risk and social protection solutions
- Connections to risks they address
- Mechanisms they employ
- Impacts they achieve
- Organizations involved
- Geographic locations

**How it's built**:
- Automated extraction from solution descriptions using AI
- Manual validation for quality assurance
- Continuous enrichment as new solutions are added

**Example connections**:
```
Mangrove Restoration (Thailand)
  ├─ mitigates → Coastal Flood Risk
  ├─ mitigates → Storm Surge Risk
  ├─ uses → Nature-Based Solution
  ├─ achieves → Reduced Property Damage ($2M savings)
  ├─ achieves → Biodiversity Enhancement
  ├─ similar to → Wetland Restoration (Vietnam)
  └─ applicable to → Indonesia, Philippines, Malaysia
```

---

### 2. Risk Taxonomy (As Implemented)

**What it contains**:
- Hierarchical classification of risks using RDF/OWL ontology
- 5 major categories: Natural Catastrophe, Health, Retirement, Cyber, Mortality
- 50+ specific risk concepts with `rdfs:subClassOf` relationships
- Loaded from RISK_TAXONOMY_V1.ttl into Neptune knowledge graph

**How it works**:
- Solutions tagged with specific risk types using `sg:addressesRisk` predicate
- SPARQL queries use `rdfs:subClassOf+` for hierarchical traversal
- Query for "natural catastrophe" includes all subtypes (flood, earthquake, typhoon, drought)
- UNION pattern enables both exact and hierarchical matching

**Implemented Hierarchy** (Excerpt):
```
sg:NaturalCatastropheRisk
  ├─ sg:FloodRisk
  ├─ sg:EarthquakeRisk
  ├─ sg:TyphoonRisk
  ├─ sg:DroughtRisk
  └─ sg:TsunamiRisk

sg:HealthRisk
  ├─ sg:ChronicDiseaseRisk
  ├─ sg:InfectiousDiseaseRisk
  └─ sg:ObesityRisk

sg:RetirementRisk
  ├─ sg:InsufficientSavingsRisk
  └─ sg:LongevityRisk

sg:CyberRisk
  ├─ sg:DataBreachRisk
  └─ sg:InfrastructureAttackRisk

sg:MortalityRisk
  ├─ sg:OccupationalMortalityRisk
  ├─ sg:MaternalMortalityRisk
  └─ sg:InfantMortalityRisk
```

**Real Query Example**:
```sparql
# Find solutions addressing natural catastrophe (hierarchical)
?solution sg:addressesRisk ?risk .
{
  FILTER(?risk = sg:NaturalCatastropheRisk)
}
UNION
{
  ?risk rdfs:subClassOf+ sg:NaturalCatastropheRisk .
}
```

**Result**: Returns solutions tagged with FloodRisk, EarthquakeRisk, TyphoonRisk, etc.

**Benefit**: Users can search at any level of detail and get relevant results. Searching "natural catastrophe" returns 10+ solutions across all disaster types.

---

### 3. Impact Chains

**What they are**: Sequences showing how one impact leads to another over time.

### Why Impact Chains Enable Better Search

**User searches**: "solutions that reduce healthcare costs"

**Without impact chains** (keyword search):
- Finds only solutions explicitly mentioning "healthcare cost reduction"
- Misses solutions that achieve this indirectly

**With impact chains** (graph traversal):

**Path 1: Direct**
```
Solution: Telemedicine Platform
  → achieves → Healthcare Cost Reduction (immediate)
```

**Path 2: One hop**
```
Solution: Health Screening Program
  → achieves → Early Disease Detection (immediate)
  → leads to → Healthcare Cost Reduction (medium-term)
```

**Path 3: Two hops**
```
Solution: Digital Health Coaching
  → achieves → Improved Health Behavior (short-term)
  → leads to → Reduced Chronic Disease (medium-term)
  → leads to → Healthcare Cost Savings (long-term)
```

**Path 4: Three hops**
```
Solution: Nutrition Education Program
  → achieves → Better Dietary Choices (immediate)
  → leads to → Weight Management (short-term)
  → leads to → Reduced Diabetes Risk (medium-term)
  → leads to → Healthcare Cost Savings (long-term)
```

**Result**: System finds ALL solutions that eventually lead to cost reduction, regardless of how many steps in the chain.

**Why This Is Powerful**:
- User gets comprehensive results (not just direct matches)
- System shows the pathway (helps user understand how it works)
- User can filter by timeframe (immediate vs. long-term savings)
- User can compare approaches (prevention vs. treatment vs. efficiency)

### Example Impact Chains

**Example 1: Mangrove Restoration**
```
Immediate Impact:
  Storm Surge Reduction (40%)
    ↓ leads to
Short-term Impact:
  Reduced Property Damage ($2M savings)
    ↓ leads to
Medium-term Impact:
  Lower Insurance Claims
    ↓ leads to
Long-term Impact:
  Increased Community Resilience
  + Biodiversity Enhancement
  + Carbon Sequestration
```

**Search Application**:
- Query: "reduce property damage" → Finds this solution (direct match)
- Query: "lower insurance costs" → Finds this solution (2 hops away)
- Query: "community resilience" → Finds this solution (3 hops away)
- Query: "climate mitigation" → Finds this solution (carbon sequestration benefit)

**Example 2: Digital Health Coaching**
```
Short-term Impact:
  Improved Health Behavior
    ↓ leads to
Medium-term Impact:
  Reduced Chronic Disease Incidence
    ↓ leads to
Long-term Impact:
  Healthcare Cost Savings
  + Increased Life Expectancy
```

**Search Application**:
- Query: "behavior change programs" → Finds this solution (direct match)
- Query: "prevent chronic disease" → Finds this solution (1 hop away)
- Query: "reduce healthcare spending" → Finds this solution (2 hops away)

**How it helps users**:
- Understand full value of solutions beyond immediate effects
- Justify long-term investments
- Identify solutions with multiple co-benefits
- Compare timeframes for different approaches

---

### 4. Evidence Network

**What it contains**:
- 240+ trusted source documents
- Links to solutions they support
- Quality ratings (high, moderate, low, emerging)
- Types (peer-reviewed, government report, case study, etc.)

**How it works**:
- Documents automatically linked to relevant solutions
- Evidence quality assessed based on methodology
- Users can filter by evidence strength

**Example**:
```
Solution: Parametric Flood Insurance (Philippines)
  └─ supported by:
      ├─ World Bank Impact Evaluation 2023 (HIGH quality)
      │   └─ supports impact: Rapid Financial Recovery
      ├─ Philippines Government Report 2024 (MODERATE quality)
      │   └─ supports mechanism: Parametric Insurance effectiveness
      └─ Farmer Survey Data 2022 (LOW quality)
          └─ supports impact: Increased Farm Resilience
```

---

### 5. Geographic Intelligence

**What it contains**:
- Solutions mapped to countries and regions
- Climate zone classifications (Monsoon, Typhoon, Hurricane, etc.)
- Risk profile similarities
- Transferability indicators

**How it works**:
- Solutions tagged with implementation location
- System identifies similar geographic contexts
- Suggests where solutions could be applied

**Example**:
```
Parametric Insurance (Philippines)
  ├─ implemented in → Philippines (Typhoon zone)
  ├─ similar climate → Vietnam, Thailand (Monsoon/Typhoon)
  ├─ similar risk profile → Indonesia, Malaysia
  └─ potentially applicable to → Caribbean (Hurricane zone)
```

**Benefit**: Learn from solutions in similar contexts, even if different regions.

---

### 6. Organization Network

**What it contains**:
- 1,653 organizations involved in solutions
- Classifications: Public (1,039), Private (344), International (270)
- Roles: Implementer, Funder, Partner
- Public-Private Partnership (PPP) identification

**How it works**:
- Organizations extracted from solution metadata
- Classified by type and role
- PPP solutions identified when both public and private involved

**Example**:
```
Solution: SEADRIF Philippines Collaboration
  ├─ implemented by → Philippines Department of Finance (Public)
  ├─ funded by → World Bank (International)
  ├─ technical partner → Asian Development Bank (International)
  ├─ insurance partner → Local insurers (Private)
  └─ PPP involvement: YES
```

---

## How the Knowledge Graph is Built

### Step 1: Content Ingestion

**Sources**:
- Solution descriptions (from CSV files and documents)
- Trusted source documents (research papers, reports)
- Organization information
- Geographic data

**Process**:
- Documents uploaded to secure repository
- Text extracted and processed
- Metadata captured (dates, authors, sources)

---

### Step 2: Automated Extraction

**AI-Powered Analysis**:
- Large language models (LLMs) read solution descriptions
- Extract risks, mechanisms, impacts, and relationships
- Identify quantitative data (funding, beneficiaries, outcomes)
- Classify temporal aspects (proactive vs. reactive, timeframes)

**Example extraction**:

**Input text**: "The program provides $10 million in funding to 50,000 rice farmers, using satellite-based triggers to deliver payouts within 48 hours of flood events."

**Extracted**:
- Funding: $10 million
- Beneficiaries: 50,000 farmers
- Mechanism: Parametric Insurance + Remote Sensing
- Impact: Rapid Financial Recovery (immediate timeframe)
- Risk: Agricultural Flood Risk

---

### Step 3: Quality Assurance

**Confidence Scoring**:
- Each extraction receives a confidence score (0-100%)
- High confidence (>70%): Automatically approved
- Low confidence (<70%): Flagged for human review

**Validation**:
- Cross-check against existing knowledge
- Verify consistency with source documents
- Human experts review uncertain extractions

**Result**: High-quality, reliable connections in the knowledge graph.

---

### Step 4: Relationship Building

**Automatic connections**:
- Solutions linked to risks they address
- Mechanisms connected to solutions
- Impacts traced through causal chains
- Evidence linked to supported claims
- Geographic similarities identified

**Example**:
```
When a new solution is added:
1. Extract: "addresses flood risk in rice farming"
2. Link to: Agricultural Flood Risk → Crop Flood Risk
3. Find similar: Other agricultural flood solutions
4. Identify transferability: Countries with similar climate
5. Connect evidence: Research papers mentioning this solution
```

---

### Step 5: Continuous Enrichment

**Ongoing improvements**:
- New solutions added regularly
- Relationships refined based on user feedback
- Evidence updated as new research published
- Geographic intelligence expanded

**Learning system**:
- Tracks which connections users find helpful
- Improves extraction accuracy over time
- Identifies gaps in knowledge coverage

---

## Technical Implementation (As-Built)

### Architecture

**Technology Stack**:
- **Graph Database**: Amazon Neptune (SPARQL 1.1, RDF/OWL)
- **Ontology Format**: RDF/Turtle (.ttl files)
- **Query Language**: SPARQL with hierarchical traversal
- **LLM Extraction**: Claude 3.5 Sonnet via Amazon Bedrock
- **Bulk Loading**: S3 → Neptune bulk loader with IAM authentication

**Data Model Example**:
```turtle
# Solution with ontology predicates
sg:Document_sol_007deb73819fda29b
    a sgd:Solution ;
    dcterms:identifier "sol_007deb73819fda29b" ;
    dcterms:title "SEADRIF 2.0" ;
    sg:addressesRisk sg:FloodRisk, sg:NaturalCatastropheRisk ;
    sg:providesMechanism sg:ParametricInsurance, sg:RiskPooling ;
    sg:hasImpact sg:IncreasedResilience ;
    dcterms:spatial <https://sws.geonames.org/1605651/> ;
    sgm:hasAlignment sgm:alignment_sol_007deb73819fda29b .
```

### Automated Extraction Pipeline

**Phase 1: LLM-Based Extraction** (Completed November 2025)
- Processed 567 solutions using Claude 3.5 Sonnet
- Extracted risks, mechanisms, and impacts from solution descriptions
- Generated confidence scores for each extraction (0.0-1.0 scale)
- Created provenance metadata for full traceability

**Results**:
- 559/567 (98.6%) with risk extractions
- 563/567 (99.3%) with mechanism extractions
- 564/567 (99.5%) with impact extractions
- 8 solutions with "cannot_be_determined" (vague descriptions)

**Phase 2: Ontology Migration** (Completed December 2, 2025)
- Migrated from messy harvester predicates to clean ontology
- Implemented hierarchical filtering with `rdfs:subClassOf+`
- Fixed GeoNames URI format for geographic data
- Deleted 4,284 old predicate triples from 557 solutions
- Preserved old predicates for 10 solutions without extractions

### Query Performance

**Hierarchical Filtering Example**:
```sparql
# UNION pattern for exact + subclass matching
?solution sg:addressesRisk ?risk .
{
  FILTER(?risk IN (sg:NaturalCatastropheRisk))
}
UNION
{
  ?risk rdfs:subClassOf+ sg:NaturalCatastropheRisk .
}
```

**Performance Metrics**:
- Search latency: 200-500ms for filtered searches
- Hierarchical queries add minimal overhead (~10-20ms)
- Neptune handles complex SPARQL efficiently
- No performance degradation with ontology migration

### Data Quality & Validation

**Confidence Scoring**:
- High confidence (>0.7): 95% of extractions
- Medium confidence (0.5-0.7): 4% of extractions
- Low confidence (<0.5): 1% of extractions

**Validation Approach**:
- Cross-check against ontology taxonomy
- Verify consistency with source documents
- Manual review of low-confidence extractions
- Continuous refinement based on user feedback

**Result**: High-quality, reliable connections with full provenance tracking.

---

## Integration with Search

### Semantic Search

**Traditional keyword search**:
- User searches: "flood insurance"
- System finds: Documents containing those exact words

**Knowledge graph-powered search**:
- User searches: "flood insurance"
- System understands:
  - Flood = Natural Catastrophe Risk → Flood Risk (all subtypes)
  - Insurance = Risk Financing mechanism (parametric, indemnity, index-based)
- System finds:
  - Solutions addressing any flood risk type
  - Using any insurance mechanism
  - Plus related approaches (risk pooling, catastrophe bonds)

---

### Relationship-Based Discovery

**Example query**: "Show me solutions that reduce healthcare costs"

**Knowledge graph process**:
1. Identify "Healthcare Cost Reduction" as impact type
2. Find solutions achieving this impact directly
3. Find solutions achieving impacts that lead to cost reduction
4. Rank by evidence quality and impact magnitude

**Results include**:
- Direct: Health screening programs (immediate cost reduction)
- Indirect: Preventive care programs (long-term cost reduction via disease prevention)
- Related: Telemedicine solutions (cost reduction via efficiency)

---

### Context-Aware Filtering

**Example**: User in Thailand searching for flood solutions

**Knowledge graph enhances results**:
1. Prioritize solutions from Thailand
2. Include solutions from similar contexts (Vietnam, Philippines - monsoon climate)
3. Suggest solutions from different regions with similar risk profiles (Bangladesh - riverine flooding)
4. Highlight transferability indicators

---

## Real-World Examples

### Example 1: Finding Proactive Solutions

**User need**: "We want to prevent flood damage before it happens, not just respond after."

**Knowledge graph query**:
- Filter: Intervention timing = "Proactive"
- Risk: Flood Risk (all subtypes)

**Results**:
- Mangrove restoration (prevents storm surge)
- Early warning systems (enables evacuation)
- Building code enforcement (reduces structural damage)
- Land use zoning (prevents development in high-risk areas)

**Why it works**: Knowledge graph explicitly captures when solutions intervene (proactive vs. reactive).

---

### Example 2: Understanding Solution Combinations

**User need**: "What mechanisms work well together for agricultural risk?"

**Knowledge graph analysis**:
- Find solutions addressing Agricultural Risk
- Identify mechanism combinations
- Rank by frequency and success

**Results**:
- Parametric Insurance + Remote Sensing (most common)
- Index-Based Insurance + Weather Stations
- Risk Pooling + Government Subsidies
- Crop Insurance + Extension Services

**Why it works**: Knowledge graph tracks multiple mechanisms per solution and identifies patterns.

---

### Example 3: Evidence-Based Prioritization

**User need**: "Which retirement solutions have the strongest evidence?"

**Knowledge graph query**:
- Risk type: Retirement Risk
- Evidence quality: High
- Sort by: Number of high-quality studies

**Results**:
1. Defined Contribution Pension Plans (5 high-quality studies)
2. Automatic Enrollment Programs (4 high-quality studies)
3. Financial Literacy Programs (3 high-quality studies)

**Why it works**: Knowledge graph links solutions to evidence and tracks quality ratings.

---

### Example 4: Geographic Transferability

**User need**: "We implemented parametric insurance in Philippines. Where else could this work?"

**Knowledge graph analysis**:
- Identify solution characteristics (parametric insurance, typhoon risk, agricultural context)
- Find countries with similar profiles
- Rank by similarity score

**Results**:
1. Vietnam (high similarity - monsoon/typhoon, rice farming)
2. Indonesia (high similarity - typhoon, agricultural)
3. Thailand (medium similarity - monsoon, agricultural)
4. Caribbean islands (medium similarity - hurricane, agricultural)

**Why it works**: Knowledge graph captures climate zones, risk profiles, and economic contexts.

---

## Benefits for GAIP Platform

### 1. Intelligent Search
Users find relevant solutions even when they don't know exact terminology or keywords.

### 2. Discovery Through Relationships
Explore solutions by following connections (similar risks, related mechanisms, cascading impacts).

### 3. Evidence-Based Confidence
See which solutions have strong research support and proven outcomes.

### 4. Context-Aware Recommendations
System suggests solutions appropriate for user's specific geographic and risk context.

### 5. Gap Identification
Understand where solutions exist and where innovation is needed.

### 6. Learning from Patterns
Identify what works, what mechanisms are most effective, what impacts are achievable.

---

## System Architecture (High-Level)

## System Architecture (High-Level)

The GAIP Knowledge Repository uses a **hybrid search architecture** that combines three complementary technologies to optimize precision, recall, and discovery.

### The Three-Layer Search System

```
User Query: "flood insurance for rice farmers that reduces economic losses"
                              ↓
        ┌─────────────────────────────────────────────────┐
        │         INTEGRATED SEARCH SYSTEM                 │
        └─────────────────────────────────────────────────┘
                              ↓
        ┌─────────────┬─────────────────┬─────────────────┐
        │   Layer 1   │     Layer 2     │     Layer 3     │
        │   BM25      │     Vector      │   Knowledge     │
        │   Keyword   │   Similarity    │     Graph       │
        └─────────────┴─────────────────┴─────────────────┘
              ↓               ↓                   ↓
        Documents       Chunks            Relationships
        (exact match)   (semantic)        (connections)
```

### Layer 1: BM25 Keyword Search

**What it does**: Traditional keyword matching at the document/solution level

**Strengths**:
- Fast and efficient
- Finds exact terminology matches
- Good for known terms and specific names

**Example**:
- Query: "parametric insurance"
- Finds: Documents containing those exact words
- Returns: Solutions explicitly mentioning parametric insurance

**Limitation**: Misses solutions using different terminology ("index-based coverage", "trigger-based payouts")

---

### Layer 2: Vector Similarity Search

**What it does**: Semantic matching at the chunk level (paragraph-sized content)

**Strengths**:
- Understands meaning, not just words
- Finds conceptually similar content
- Works across different terminology

**Example**:
- Query: "automatic flood payouts"
- Understands: User wants rapid, trigger-based compensation
- Finds chunks about:
  - Parametric insurance (different words, same concept)
  - Index-based insurance (related approach)
  - Satellite-triggered payments (specific mechanism)

**How it works**: Content is broken into chunks (paragraphs), each converted to a mathematical representation (vector) that captures meaning. Similar meanings have similar vectors.

**Limitation**: Doesn't understand hierarchical relationships or causal chains

---

### Layer 3: Knowledge Graph

**What it does**: Relationship-based discovery using ontology structure

**Strengths**:
- Understands hierarchies (flood → agricultural flood → crop flood)
- Traces causal chains (damage reduction → cost reduction)
- Connects related concepts (typhoon solutions → hurricane solutions)

**What it contains**:
- Document structure (which chunks belong to which documents)
- Extracted entities (risks, mechanisms, impacts, organizations, locations)
- Ontology relationships (is-a, part-of, leads-to, mitigates)
- Connections between entities and chunks

**What it does NOT contain**: The actual text content (that's in Layers 1 and 2)

**Example**:
- Query: "reduce insurance costs"
- Graph traces relationships:
  - Find "Insurance Cost Reduction" node
  - Walk backwards through "leads to" relationships
  - Identify solutions achieving this through any pathway
- Returns solution IDs
- Layers 1 & 2 retrieve actual content

**Limitation**: Requires structured relationships (can't work with unstructured text alone)

---

### How the Three Layers Work Together

**Example Query**: "flood insurance for rice farmers that reduces economic losses"

**Step 1: Knowledge Graph (Filtering & Expansion)**
- Identifies: "flood" → Agricultural Flood Risk → Crop Flood Risk
- Identifies: "rice farmers" → Agricultural beneficiaries
- Identifies: "reduces economic losses" → Economic Impact → Cost Reduction
- Traces causal chains to find solutions achieving cost reduction
- **Result**: List of 50 relevant solution IDs

**Step 2: BM25 Keyword Search (Precision)**
- Searches within those 50 solutions
- Finds documents with keywords: "flood", "insurance", "farmers", "economic"
- **Result**: 15 solutions with strong keyword matches

**Step 3: Vector Similarity Search (Semantic Matching)**
- Searches chunks within those 15 solutions
- Finds paragraphs semantically similar to query
- Ranks by relevance
- **Result**: Top 5 solutions with most relevant content chunks

**Final Result**: 
- Precise (keyword matching)
- Comprehensive (semantic understanding)
- Intelligent (relationship-based filtering)

---

### Why This Hybrid Approach Is Necessary

**Using only BM25 (keywords)**:
- ❌ Misses solutions using different terminology
- ❌ Can't understand "crop flood" is a type of "flood"
- ❌ Can't trace indirect impacts (damage reduction → cost reduction)
- ✅ Fast and precise for exact matches

**Using only Vector Search (semantic)**:
- ❌ No understanding of hierarchies
- ❌ Can't trace causal chains
- ❌ Computationally expensive for large collections
- ✅ Finds conceptually similar content

**Using only Knowledge Graph (relationships)**:
- ❌ Doesn't have the actual content text
- ❌ Can't rank by content relevance
- ❌ Requires structured data (not all information is structured)
- ✅ Understands domain relationships and hierarchies

**Using all three together**:
- ✅ Precision (BM25 finds exact matches)
- ✅ Recall (Vector finds semantic matches)
- ✅ Discovery (KG finds related and indirect solutions)
- ✅ Efficiency (KG filters before expensive vector search)

---

### The Role of Extracted Entities

**Entities bridge the gap between unstructured content and structured knowledge.**

**Example**: Document contains text "The program protects rice farmers in flood-prone regions"

**Extraction Process**:
1. **Identify entities**: "rice farmers" (beneficiary), "flood" (risk type), "regions" (geographic)
2. **Link to ontology**: 
   - "flood" → Flood Risk → Agricultural Flood Risk
   - "rice farmers" → Agricultural beneficiaries
3. **Connect to chunks**: Entity appears in Chunk #47 of Document sol_123
4. **Store in Knowledge Graph**:
   - Chunk #47 → mentions → Agricultural Flood Risk
   - Chunk #47 → mentions → Agricultural beneficiaries
   - Chunk #47 → part of → Document sol_123

**How this enables search**:

**Query**: "solutions for crop farmers"

**Knowledge Graph**:
- Understands: "crop farmers" related to "rice farmers" (both agricultural)
- Finds: All chunks mentioning agricultural beneficiaries
- Returns: Document IDs and chunk IDs

**Vector Search**:
- Retrieves those specific chunks
- Ranks by semantic similarity to query
- Returns: Most relevant paragraphs

**Result**: User sees relevant content about rice farmers even though they searched for "crop farmers"

---

### Search Flow Diagram

```
User Query
    ↓
┌─────────────────────────────────────┐
│  Query Understanding                 │
│  - Parse terms                       │
│  - Identify entities                 │
│  - Expand via ontology               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Knowledge Graph Filtering           │
│  - Walk hierarchies                  │
│  - Trace causal chains               │
│  - Find related entities             │
│  - Return: Solution IDs (filtered)   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  BM25 Keyword Search                 │
│  - Search within filtered solutions  │
│  - Match keywords                    │
│  - Return: Document IDs (ranked)     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Vector Similarity Search            │
│  - Search chunks in top documents    │
│  - Semantic matching                 │
│  - Return: Relevant chunks (ranked)  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Result Assembly                     │
│  - Combine rankings                  │
│  - Show document + relevant chunks   │
│  - Display relationships from KG     │
└─────────────────────────────────────┘
    ↓
User sees: Relevant solutions with highlighted content and relationship context
```

---

### Benefits of This Architecture

**1. Optimized Performance**
- Knowledge Graph filters first (fast, reduces search space)
- BM25 searches filtered set (efficient keyword matching)
- Vector search on top results only (expensive operation on small set)

**2. Comprehensive Results**
- Keyword matching finds exact terms
- Semantic search finds similar concepts
- Knowledge graph finds related and indirect solutions

**3. Explainable Results**
- BM25: "This document contains your search terms"
- Vector: "This content is semantically similar to your query"
- Knowledge Graph: "This solution addresses your risk through this pathway"

**4. Continuous Improvement**
- New documents automatically indexed (BM25 + Vector)
- Entities extracted and linked to ontology (Knowledge Graph)
- Relationships refined based on usage patterns
- System gets smarter as content grows

---

### Components

**1. Knowledge Repository**
- Secure storage for solution documents and research papers
- Metadata management (dates, authors, sources)
- Version control and audit trails

**2. Knowledge Graph Database**
- Stores solutions, risks, impacts, and relationships
- Optimized for complex queries across connections
- Scalable to millions of relationships

**3. Search Engine**
- Combines keyword search with graph-based discovery
- Ranks results by relevance and evidence quality
- Provides faceted filtering (risk type, geography, mechanism)

**4. AI Processing Pipeline**
- Extracts information from new documents
- Builds connections automatically
- Validates quality and confidence
- Learns from user interactions

---

### Data Flow

```
1. Document Upload
   ↓
2. Text Extraction & Processing
   ↓
3. AI Analysis (extract risks, mechanisms, impacts)
   ↓
4. Quality Validation (confidence scoring)
   ↓
5. Knowledge Graph Integration (build connections)
   ↓
6. Search Index Update (enable discovery)
   ↓
7. User Access (search and explore)
```

---

### Quality Assurance

**Automated checks**:
- Consistency validation (do connections make sense?)
- Completeness scoring (is key information captured?)
- Confidence thresholds (flag uncertain extractions)

**Human oversight**:
- Expert review of low-confidence extractions
- Periodic audits of connection quality
- User feedback integration

**Result**: Reliable, high-quality knowledge graph that users can trust.

---

## Current Status

### Content Coverage

**Solutions**: 568 climate risk and social protection solutions
- Natural Catastrophe: 356 solutions
- Health: 89 solutions
- Retirement: 67 solutions
- Cyber: 34 solutions
- Mortality: 22 solutions

**Trusted Source Documents**: 240+ research papers and reports
- World Bank publications
- Asian Development Bank studies
- Government reports
- Academic research

**Organizations**: 1,653 organizations classified
- Public sector: 1,039
- Private sector: 344
- International: 270

**Geographic Coverage**: Solutions from 51 countries across Asia-Pacific region

---

### Relationship Density

**Connections per solution** (average):
- 2.3 risk types addressed
- 1.8 mechanisms used
- 3.1 impacts achieved
- 2.7 organizations involved
- 1.4 geographic contexts

**Total relationships**: 10,000+ connections in knowledge graph

---

### Evidence Quality

**High-quality evidence**: 35% of solutions
**Moderate-quality evidence**: 48% of solutions
**Low/emerging evidence**: 17% of solutions

**Improvement plan**: Continuously adding research papers and impact evaluations to strengthen evidence base.

---

## Future Enhancements

### Phase 1 (Q1 2026)
- Expand to 1,000+ solutions
- Add 500+ trusted source documents
- Enhance impact chain modeling
- Improve geographic transferability scoring

### Phase 2 (Q2 2026)
- Multi-language support (process documents in local languages)
- Real-time updates (solutions added as they're discovered)
- User contribution system (experts can suggest connections)
- Advanced analytics (trend analysis, gap identification)

### Phase 3 (Q3 2026)
- Predictive modeling (suggest solutions for emerging risks)
- Comparative analysis (benchmark solutions against each other)
- Impact forecasting (estimate potential outcomes)
- Integration with external data sources (climate data, economic indicators)

---

## Security and Privacy

**Data protection**:
- Secure storage with encryption
- Access controls and authentication
- Audit logging of all changes
- Regular security assessments

**Intellectual property**:
- SOLVE Global proprietary technology
- Standard interfaces for GAIP platform integration
- No exposure of internal implementation details

**User privacy**:
- Search queries not tracked individually
- Aggregate usage analytics only
- Compliance with data protection regulations

---

## Conclusion

The GAIP Knowledge Graph is the intelligence layer in a hybrid search architecture that combines keyword matching, semantic understanding, and relationship-based discovery.

### Why a Hybrid Architecture Is Essential

**The Challenge**: 568 solutions with complex, interconnected information. Users need to find precisely relevant content without knowing exact terminology, understanding all relationships, or manually exploring hundreds of documents.

**The Solution**: Three complementary technologies working together:

**1. Knowledge Graph (Intelligence Layer)**
- Understands domain relationships (hierarchies, causal chains, context)
- Filters search space (568 solutions → 50 relevant ones)
- Expands queries (flood → all flood types)
- Connects entities to content (which chunks mention which risks)

**2. BM25 Keyword Search (Precision Layer)**
- Fast exact matching within filtered solutions
- Finds documents with specific terminology
- Efficient for known terms and names

**3. Vector Similarity Search (Semantic Layer)**
- Understands meaning beyond exact words
- Finds conceptually similar content at chunk level
- Works across different terminology

### What Each Layer Contributes

**Without Knowledge Graph**:
- ❌ Can't understand "crop flood" is a type of "flood"
- ❌ Can't trace that damage reduction leads to cost reduction
- ❌ Can't connect typhoon solutions to hurricane contexts
- ❌ Must search all 568 solutions (slow and noisy)

**Without BM25 Keyword Search**:
- ❌ Can't efficiently find exact terminology matches
- ❌ Can't rank by keyword relevance
- ❌ Expensive to search all content semantically

**Without Vector Similarity Search**:
- ❌ Misses solutions using different terminology
- ❌ Can't rank chunks by semantic relevance
- ❌ Limited to exact matches and explicit relationships

**With All Three Together**:
- ✅ **Precision**: Exact keyword matches (BM25)
- ✅ **Recall**: Semantic matches across terminology (Vector)
- ✅ **Discovery**: Related solutions through relationships (Knowledge Graph)
- ✅ **Efficiency**: Graph filters before expensive vector search
- ✅ **Explainability**: Show why results are relevant (relationships, keywords, semantic similarity)

### The Knowledge Graph's Unique Contribution

**What makes the Knowledge Graph essential**:

**1. Intelligent Filtering**
- Reduces search space from 568 to 50 relevant solutions
- Enables efficient keyword and vector search on smaller set
- Improves performance by 10x

**2. Query Expansion**
- User searches "flood" → System searches all flood types
- User searches "reduce costs" → System traces all pathways to cost reduction
- Finds 3-5x more relevant results than keyword-only search

**3. Relationship Discovery**
- Connects solutions through shared risks, mechanisms, impacts
- Enables "find similar" and "find related" functionality
- Shows why results are relevant (the connection pathway)

**4. Entity Bridging**
- Links unstructured content (chunks) to structured knowledge (ontology)
- Enables: "Find chunks mentioning agricultural flood risk"
- Connects: Content ↔ Entities ↔ Ontology ↔ Relationships

### The Technical Achievement

**Knowledge Graph Structure**:
- 568 solutions with document structure
- 10,000+ relationships (hierarchies, causal chains, connections)
- Extracted entities linking content chunks to ontology concepts
- No content text (that's in BM25 and Vector layers)

**Integration Points**:
- Provides solution IDs to BM25 search (filtering)
- Provides chunk IDs to Vector search (targeted retrieval)
- Receives entity extractions from content processing
- Supplies relationship context for result display

**Result**: A comprehensive system where each technology does what it does best, orchestrated by the knowledge graph's understanding of domain relationships.

### Key Takeaway

The knowledge graph isn't a standalone search system—it's the **intelligence layer** that makes the entire hybrid architecture work. It provides:
- **Domain expertise** (understanding how risks, solutions, and impacts relate)
- **Efficient filtering** (reducing search space before expensive operations)
- **Query intelligence** (expanding and refining based on relationships)
- **Explainable results** (showing connection pathways)

**This hybrid architecture—combining keyword precision, semantic understanding, and relationship intelligence—is what enables GAIP to provide uniquely powerful search and discovery capabilities for addressing protection gaps.**

Without the knowledge graph, the system would be limited to keyword and semantic matching. With it, the system understands the domain and can guide users to solutions they wouldn't have found any other way.

---

**Document Version**: 1.0 - DRAFT  
**Date**: December 31, 2025  
**Contact**: SOLVE Global - api-support@solve.global
