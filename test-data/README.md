# Test Data Files
**Purpose**: Test data, sample payloads, and testing configurations

## Directory Structure

### `/test-payloads/` - Test Messages & Payloads
Sample messages and payloads for testing Lambda functions and services.
- `nlp_kg_test_message.json` - NLP knowledge graph test message
- `nlp_kg_test_payload.json` - NLP knowledge graph test payload
- `test_entity_alignment_message.json` - Entity alignment test message
- `test-nlp-existing-doc.json` - NLP test for existing document
- `test-nlp-initiator-message.json` - NLP initiator test message
- `test-nlp-message.json` - Basic NLP test message

### `/responses/` - API/Service Response Samples
Sample responses from APIs and services for testing and validation.
- `response-nlp-real.json` - Real NLP response sample
- `response-nlp.json` - NLP response sample

### `/progress/` - Progress Tracking Files
Files tracking processing progress and batch operations.
- `progress_100docs.json` - 100 documents processing progress (archived)

### `/ontology/` - Ontology Test Configurations
Test configurations and data for ontology operations.
- `test_concept_search.json` - Concept search test configuration
- `test_contextual_alignment_config.json` - Contextual alignment configuration
- `test_load_climate_ontology.json` - Climate ontology loading test
- `test_multi_ontology_config.json` - Multi-ontology configuration
- `test_multi_ontology_stats.json` - Multi-ontology statistics

## Usage
These files are used for testing system components, validating API responses, and configuring test scenarios. Reference them in test scripts and validation procedures.
