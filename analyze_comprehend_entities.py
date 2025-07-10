#!/usr/bin/env python3
"""
Analyze AWS Comprehend entity types and create RDF schema mapping
"""

import boto3
import json
from typing import Dict, List, Any

# Sample climate risk text for testing
SAMPLE_TEXT = """
The Intergovernmental Panel on Climate Change (IPCC) released a report on December 15, 2023, 
warning that global temperatures could rise by 2.5 degrees Celsius by 2050. The report, 
authored by Dr. Sarah Johnson from Stanford University and Professor Michael Chen from MIT, 
highlights risks to coastal cities like Miami, New York, and San Francisco.

ExxonMobil and Shell have invested $50 billion in renewable energy projects across Europe and Asia. 
The European Union's Green Deal, announced by President Ursula von der Leyen, aims to reduce 
carbon emissions by 55% by 2030. The United States Environmental Protection Agency (EPA) 
has set new regulations for methane emissions from oil and gas operations.

Climate activists including Greta Thunberg organized protests in London, Paris, and Berlin 
on September 20, 2024. The World Bank approved a $2.3 billion loan to Bangladesh for 
climate adaptation projects. Amazon rainforest deforestation increased by 12% in 2023, 
affecting biodiversity in Brazil and Peru.
"""

def analyze_comprehend_entities():
    """Analyze what entity types Comprehend returns"""
    
    # Initialize Comprehend client
    comprehend = boto3.client('comprehend', region_name='us-east-1')
    
    try:
        # Detect entities
        response = comprehend.detect_entities(
            Text=SAMPLE_TEXT,
            LanguageCode='en'
        )
        
        # Analyze entity types
        entity_types = {}
        entities_by_type = {}
        
        for entity in response['Entities']:
            entity_type = entity['Type']
            entity_text = entity['Text']
            confidence = entity['Score']
            
            # Count by type
            if entity_type not in entity_types:
                entity_types[entity_type] = 0
                entities_by_type[entity_type] = []
            
            entity_types[entity_type] += 1
            entities_by_type[entity_type].append({
                'text': entity_text,
                'confidence': confidence,
                'begin_offset': entity['BeginOffset'],
                'end_offset': entity['EndOffset']
            })
        
        print("=== AWS COMPREHEND ENTITY ANALYSIS ===")
        print(f"Total entities found: {len(response['Entities'])}")
        print(f"Unique entity types: {len(entity_types)}")
        print()
        
        print("=== ENTITY TYPES AND COUNTS ===")
        for entity_type, count in sorted(entity_types.items()):
            print(f"{entity_type}: {count}")
        print()
        
        print("=== ENTITIES BY TYPE ===")
        for entity_type, entities in entities_by_type.items():
            print(f"\n{entity_type}:")
            for entity in sorted(entities, key=lambda x: x['confidence'], reverse=True):
                print(f"  - {entity['text']} (confidence: {entity['confidence']:.3f})")
        
        return entities_by_type
        
    except Exception as e:
        print(f"Error analyzing entities: {e}")
        return {}

def create_rdf_mapping_analysis(entities_by_type: Dict[str, List[Dict]]):
    """Create analysis of how Comprehend types map to RDF ontologies"""
    
    # AWS Comprehend entity types and their RDF mappings
    comprehend_to_rdf_mapping = {
        'PERSON': {
            'primary_ontology': 'FOAF (Friend of a Friend)',
            'rdf_class': 'foaf:Person',
            'properties': [
                'foaf:name',
                'foaf:givenName', 
                'foaf:familyName',
                'foaf:title'
            ],
            'alternative_ontologies': [
                'schema:Person (Schema.org)',
                'vcard:Individual (vCard)',
                'dbo:Person (DBpedia)'
            ],
            'climate_specific': False,
            'examples': entities_by_type.get('PERSON', [])
        },
        
        'LOCATION': {
            'primary_ontology': 'GeoNames / Schema.org',
            'rdf_class': 'schema:Place',
            'properties': [
                'schema:name',
                'schema:geo',
                'schema:address',
                'geo:lat',
                'geo:long'
            ],
            'alternative_ontologies': [
                'gn:Feature (GeoNames)',
                'dbo:Place (DBpedia)',
                'wgs84:SpatialThing'
            ],
            'climate_specific': True,
            'climate_extensions': [
                'Climate vulnerability assessment',
                'Sea level rise risk',
                'Temperature change projections'
            ],
            'examples': entities_by_type.get('LOCATION', [])
        },
        
        'ORGANIZATION': {
            'primary_ontology': 'FOAF / Schema.org',
            'rdf_class': 'foaf:Organization',
            'properties': [
                'foaf:name',
                'schema:legalName',
                'schema:organizationType',
                'foaf:homepage'
            ],
            'alternative_ontologies': [
                'schema:Organization',
                'org:Organization (W3C Organization Ontology)',
                'dbo:Organisation (DBpedia)'
            ],
            'climate_specific': True,
            'climate_extensions': [
                'Carbon footprint data',
                'Sustainability commitments',
                'Climate risk exposure'
            ],
            'examples': entities_by_type.get('ORGANIZATION', [])
        },
        
        'DATE': {
            'primary_ontology': 'Time Ontology / Schema.org',
            'rdf_class': 'time:Instant',
            'properties': [
                'time:inXSDDateTime',
                'schema:startDate',
                'schema:endDate',
                'time:hasDateTimeDescription'
            ],
            'alternative_ontologies': [
                'schema:Date',
                'dcterms:date (Dublin Core)',
                'time:TemporalEntity'
            ],
            'climate_specific': True,
            'climate_extensions': [
                'Climate event timestamps',
                'Projection timeframes',
                'Historical climate data points'
            ],
            'examples': entities_by_type.get('DATE', [])
        },
        
        'QUANTITY': {
            'primary_ontology': 'QUDT (Quantities, Units, Dimensions and Types)',
            'rdf_class': 'qudt:Quantity',
            'properties': [
                'qudt:numericValue',
                'qudt:unit',
                'qudt:quantityKind',
                'schema:value'
            ],
            'alternative_ontologies': [
                'schema:QuantitativeValue',
                'om:Quantity (Ontology of units of Measure)',
                'uo:UO (Units Ontology)'
            ],
            'climate_specific': True,
            'climate_extensions': [
                'Temperature measurements',
                'Emission quantities',
                'Sea level measurements',
                'Precipitation amounts'
            ],
            'examples': entities_by_type.get('QUANTITY', [])
        },
        
        'EVENT': {
            'primary_ontology': 'Event Ontology / Schema.org',
            'rdf_class': 'event:Event',
            'properties': [
                'event:time',
                'event:place',
                'event:agent',
                'schema:startDate',
                'schema:location'
            ],
            'alternative_ontologies': [
                'schema:Event',
                'sem:Event (Simple Event Model)',
                'lode:Event (LODE)'
            ],
            'climate_specific': True,
            'climate_extensions': [
                'Climate events (storms, droughts)',
                'Policy announcements',
                'Scientific conferences',
                'Protest events'
            ],
            'examples': entities_by_type.get('EVENT', [])
        },
        
        'COMMERCIAL_ITEM': {
            'primary_ontology': 'Schema.org / GoodRelations',
            'rdf_class': 'schema:Product',
            'properties': [
                'schema:name',
                'schema:description',
                'schema:category',
                'gr:ProductOrService'
            ],
            'alternative_ontologies': [
                'gr:ProductOrService (GoodRelations)',
                'dbo:Product (DBpedia)'
            ],
            'climate_specific': True,
            'climate_extensions': [
                'Carbon footprint',
                'Sustainability rating',
                'Renewable energy products'
            ],
            'examples': entities_by_type.get('COMMERCIAL_ITEM', [])
        },
        
        'OTHER': {
            'primary_ontology': 'SKOS (Simple Knowledge Organization System)',
            'rdf_class': 'skos:Concept',
            'properties': [
                'skos:prefLabel',
                'skos:altLabel',
                'skos:definition',
                'skos:broader',
                'skos:narrower'
            ],
            'alternative_ontologies': [
                'schema:Thing',
                'owl:Thing',
                'rdfs:Resource'
            ],
            'climate_specific': True,
            'climate_extensions': [
                'Climate concepts',
                'Scientific terminology',
                'Policy terms'
            ],
            'examples': entities_by_type.get('OTHER', [])
        }
    }
    
    print("\n=== RDF ONTOLOGY MAPPING ANALYSIS ===")
    
    for comprehend_type, mapping in comprehend_to_rdf_mapping.items():
        if comprehend_type in entities_by_type:
            print(f"\n{comprehend_type} ({len(entities_by_type[comprehend_type])} found)")
            print(f"  Primary Ontology: {mapping['primary_ontology']}")
            print(f"  RDF Class: {mapping['rdf_class']}")
            print(f"  Key Properties: {', '.join(mapping['properties'][:3])}")
            print(f"  Climate Specific: {mapping['climate_specific']}")
            
            if mapping['climate_specific'] and 'climate_extensions' in mapping:
                print(f"  Climate Extensions: {', '.join(mapping['climate_extensions'][:2])}")
    
    return comprehend_to_rdf_mapping

def generate_schema_recommendations():
    """Generate recommendations for RDF schema design"""
    
    recommendations = {
        'core_ontologies': {
            'FOAF': {
                'purpose': 'People and organizations',
                'namespace': 'http://xmlns.com/foaf/0.1/',
                'key_classes': ['foaf:Person', 'foaf:Organization', 'foaf:Agent'],
                'priority': 'High'
            },
            'Schema.org': {
                'purpose': 'General structured data',
                'namespace': 'https://schema.org/',
                'key_classes': ['schema:Person', 'schema:Organization', 'schema:Place', 'schema:Event'],
                'priority': 'High'
            },
            'Dublin Core': {
                'purpose': 'Document metadata',
                'namespace': 'http://purl.org/dc/terms/',
                'key_classes': ['dcterms:BibliographicResource', 'dcterms:Agent'],
                'priority': 'High'
            },
            'SKOS': {
                'purpose': 'Concept organization',
                'namespace': 'http://www.w3.org/2004/02/skos/core#',
                'key_classes': ['skos:Concept', 'skos:ConceptScheme'],
                'priority': 'Medium'
            }
        },
        
        'climate_specific_ontologies': {
            'QUDT': {
                'purpose': 'Quantities and measurements',
                'namespace': 'http://qudt.org/schema/qudt/',
                'key_classes': ['qudt:Quantity', 'qudt:Unit'],
                'priority': 'High',
                'use_case': 'Temperature, emissions, measurements'
            },
            'Time Ontology': {
                'purpose': 'Temporal relationships',
                'namespace': 'http://www.w3.org/2006/time#',
                'key_classes': ['time:Instant', 'time:Interval'],
                'priority': 'Medium',
                'use_case': 'Climate projections, historical data'
            },
            'GeoSPARQL': {
                'purpose': 'Spatial relationships',
                'namespace': 'http://www.opengis.net/ont/geosparql#',
                'key_classes': ['geo:Feature', 'geo:Geometry'],
                'priority': 'Medium',
                'use_case': 'Location-based climate risks'
            }
        },
        
        'document_refactoring': {
            'current_schema': 'Custom document properties',
            'recommended_schema': 'Dublin Core Terms',
            'benefits': [
                'Standardized metadata',
                'Better interoperability',
                'Rich provenance tracking'
            ],
            'key_mappings': {
                'title': 'dcterms:title',
                'author': 'dcterms:creator',
                'date': 'dcterms:created',
                'source': 'dcterms:source',
                'description': 'dcterms:description',
                'subject': 'dcterms:subject'
            }
        }
    }
    
    print("\n=== SCHEMA RECOMMENDATIONS ===")
    
    print("\nCore Ontologies (High Priority):")
    for name, details in recommendations['core_ontologies'].items():
        if details['priority'] == 'High':
            print(f"  {name}: {details['purpose']}")
            print(f"    Namespace: {details['namespace']}")
    
    print("\nClimate-Specific Ontologies:")
    for name, details in recommendations['climate_specific_ontologies'].items():
        print(f"  {name}: {details['purpose']}")
        print(f"    Use Case: {details['use_case']}")
    
    print("\nDocument Schema Refactoring:")
    print("  Migrate from custom properties to Dublin Core:")
    for current, dc_term in recommendations['document_refactoring']['key_mappings'].items():
        print(f"    {current} → {dc_term}")
    
    return recommendations

if __name__ == "__main__":
    print("Analyzing AWS Comprehend entity types for RDF schema mapping...")
    
    # Analyze Comprehend entities
    entities_by_type = analyze_comprehend_entities()
    
    # Create RDF mapping analysis
    rdf_mapping = create_rdf_mapping_analysis(entities_by_type)
    
    # Generate recommendations
    recommendations = generate_schema_recommendations()
    
    print("\n=== NEXT STEPS ===")
    print("1. Implement core ontology namespaces (FOAF, Schema.org, Dublin Core)")
    print("2. Create climate-specific extensions using QUDT for measurements")
    print("3. Refactor document schema to use Dublin Core terms")
    print("4. Design entity linking strategy from NLP results to KG nodes")
    print("5. Implement SKOS concept hierarchy for climate terminology")
