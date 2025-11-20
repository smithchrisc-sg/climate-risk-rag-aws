#!/usr/bin/env python3
"""
Focused analysis of climate-related NLP entities and key phrases
"""

import json
import subprocess
import tempfile
from collections import defaultdict, Counter
import re

def load_nlp_results():
    """Load entities and key phrases from extracted files"""
    import os
    
    # Load entities first
    os.chdir('/tmp/nlp-analysis')
    subprocess.run(['rm', '-f', 'output'], check=False)
    subprocess.run(['tar', '-xzf', 'entities.tar.gz'], check=True)
    
    with open('/tmp/nlp-analysis/output', 'r') as f:
        entities_data = json.load(f)
    
    # Extract key phrases
    subprocess.run(['rm', '-f', 'output'], check=False)
    subprocess.run(['tar', '-xzf', 'keyphrases.tar.gz'], check=True)
    
    with open('/tmp/nlp-analysis/output', 'r') as f:
        keyphrases_data = json.load(f)
    
    return entities_data, keyphrases_data

def get_ontology_concepts():
    """Get concepts from the loaded ontology via admin ontology manager"""
    payload = {
        "operation": "get_concepts",
        "parameters": {
            "limit": 1000
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(payload, f)
        payload_file = f.name
    
    try:
        result = subprocess.run([
            'aws', 'lambda', 'invoke',
            '--function-name', 'solve-global-kr-admin-ontology-manager',
            '--cli-binary-format', 'raw-in-base64-out',
            '--payload', f'file://{payload_file}',
            '--region', 'us-east-1',
            '/tmp/ontology_concepts.json'
        ], capture_output=True, text=True, check=True)
        
        with open('/tmp/ontology_concepts.json', 'r') as f:
            response_data = json.load(f)
        
        if response_data.get('statusCode') == 200:
            body = json.loads(response_data['body'])
            if body.get('success'):
                return body['result']['concepts']
        
        return []
            
    except Exception as e:
        print(f"❌ Error calling admin ontology manager: {e}")
        return []
    finally:
        import os
        os.unlink(payload_file)

def is_climate_related(text: str) -> bool:
    """Check if text is potentially climate/disaster/financial related"""
    climate_keywords = [
        'climate', 'disaster', 'earthquake', 'flood', 'drought', 'storm', 'weather',
        'environmental', 'risk', 'vulnerability', 'resilience', 'adaptation',
        'financial', 'bank', 'credit', 'loan', 'investment', 'fund', 'capital',
        'economic', 'development', 'poverty', 'reconstruction', 'recovery',
        'nepal', 'kathmandu', 'government', 'policy', 'sector', 'institution'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in climate_keywords)

def analyze_climate_nlp():
    """Analyze climate-related NLP results"""
    print("🔍 Loading NLP results...")
    entities_data, keyphrases_data = load_nlp_results()
    
    print("🔍 Loading ontology concepts...")
    ontology_concepts = get_ontology_concepts()
    
    print(f"📊 Found {len(ontology_concepts)} ontology concepts")
    print(f"📊 Found {len(entities_data.get('Entities', []))} entities")
    print(f"📊 Found {len(keyphrases_data.get('KeyPhrases', []))} key phrases")
    
    # Filter for climate-related entities
    climate_entities = []
    for entity in entities_data.get('Entities', []):
        if is_climate_related(entity['Text']):
            climate_entities.append(entity)
    
    # Filter for climate-related key phrases
    climate_keyphrases = []
    for keyphrase in keyphrases_data.get('KeyPhrases', []):
        if is_climate_related(keyphrase['Text']):
            climate_keyphrases.append(keyphrase)
    
    print(f"🌍 Found {len(climate_entities)} climate-related entities")
    print(f"🌍 Found {len(climate_keyphrases)} climate-related key phrases")
    
    # Analyze entities by type
    print("\n" + "="*80)
    print("🏷️  CLIMATE-RELATED ENTITIES BY TYPE")
    print("="*80)
    
    entity_types = defaultdict(list)
    for entity in climate_entities:
        entity_types[entity['Type']].append(entity)
    
    for entity_type, entities in sorted(entity_types.items()):
        print(f"\n{entity_type} ({len(entities)} entities):")
        # Sort by score and show top examples
        sorted_entities = sorted(entities, key=lambda x: x['Score'], reverse=True)
        for entity in sorted_entities[:10]:
            print(f"  '{entity['Text']}' (score: {entity['Score']:.3f})")
    
    # Analyze high-scoring key phrases
    print("\n" + "="*80)
    print("🔑 HIGH-SCORING CLIMATE-RELATED KEY PHRASES")
    print("="*80)
    
    # Sort by score and show top phrases
    sorted_keyphrases = sorted(climate_keyphrases, key=lambda x: x['Score'], reverse=True)
    
    print("\nTop 20 climate-related key phrases:")
    for i, keyphrase in enumerate(sorted_keyphrases[:20], 1):
        print(f"{i:2d}. '{keyphrase['Text']}' (score: {keyphrase['Score']:.3f})")
    
    # Look for specific climate risk concepts
    print("\n" + "="*80)
    print("🎯 SPECIFIC CLIMATE RISK PATTERNS")
    print("="*80)
    
    # Financial sector terms
    financial_terms = []
    for item in climate_entities + climate_keyphrases:
        text = item['Text'].lower()
        if any(term in text for term in ['bank', 'financial', 'credit', 'loan', 'fund', 'capital', 'investment']):
            financial_terms.append(item)
    
    print(f"\n💰 Financial sector terms ({len(financial_terms)}):")
    for item in sorted(financial_terms, key=lambda x: x['Score'], reverse=True)[:10]:
        print(f"  '{item['Text']}' (score: {item['Score']:.3f})")
    
    # Disaster/risk terms
    disaster_terms = []
    for item in climate_entities + climate_keyphrases:
        text = item['Text'].lower()
        if any(term in text for term in ['disaster', 'earthquake', 'risk', 'vulnerability', 'crisis', 'damage']):
            disaster_terms.append(item)
    
    print(f"\n🌪️  Disaster/risk terms ({len(disaster_terms)}):")
    for item in sorted(disaster_terms, key=lambda x: x['Score'], reverse=True)[:10]:
        print(f"  '{item['Text']}' (score: {item['Score']:.3f})")
    
    # Geographic terms
    geo_terms = []
    for item in climate_entities + climate_keyphrases:
        text = item['Text'].lower()
        if any(term in text for term in ['nepal', 'kathmandu', 'district', 'region', 'area', 'valley']):
            geo_terms.append(item)
    
    print(f"\n🗺️  Geographic terms ({len(geo_terms)}):")
    for item in sorted(geo_terms, key=lambda x: x['Score'], reverse=True)[:10]:
        print(f"  '{item['Text']}' (score: {item['Score']:.3f})")
    
    # Show ontology concepts for comparison
    print("\n" + "="*80)
    print("🧠 ONTOLOGY CONCEPTS (for comparison)")
    print("="*80)
    
    print("\nCurrent ontology concepts:")
    for concept in ontology_concepts:
        print(f"  - {concept['label']}: {concept.get('description', 'No description')}")
    
    # Gap analysis
    print("\n" + "="*80)
    print("📋 GAP ANALYSIS & RECOMMENDATIONS")
    print("="*80)
    
    print("\n🔍 Key observations:")
    print(f"1. The document contains {len(climate_entities)} climate-related entities and {len(climate_keyphrases)} key phrases")
    print(f"2. Current ontology has only {len(ontology_concepts)} concepts (very limited)")
    print(f"3. Most NLP-extracted terms are domain-specific and not covered by current ontology")
    
    print("\n💡 Recommendations for ontology expansion:")
    
    # Suggest new concepts based on frequent terms
    all_climate_texts = [item['Text'] for item in climate_entities + climate_keyphrases]
    
    # Extract potential new concepts
    potential_concepts = set()
    for text in all_climate_texts:
        # Clean and normalize
        clean_text = re.sub(r'[^\w\s]', ' ', text)
        words = clean_text.split()
        
        # Look for capitalized terms (likely proper nouns/concepts)
        for word in words:
            if word.istitle() and len(word) > 3:
                potential_concepts.add(word)
    
    # Filter out common words
    common_words = {'This', 'That', 'The', 'And', 'For', 'With', 'From', 'Bank', 'Government'}
    potential_concepts = potential_concepts - common_words
    
    print("\n   Suggested new ontology concepts:")
    for concept in sorted(list(potential_concepts))[:15]:
        print(f"     - {concept}")
    
    print("\n   Suggested concept categories to add:")
    print("     - Financial institutions (banks, microfinance, etc.)")
    print("     - Geographic entities (Nepal regions, districts)")
    print("     - Disaster types (earthquake, flooding, etc.)")
    print("     - Economic indicators (GDP, inflation, etc.)")
    print("     - Policy instruments (credits, loans, funds)")
    print("     - Stakeholder types (government, donors, etc.)")

if __name__ == "__main__":
    analyze_climate_nlp()
