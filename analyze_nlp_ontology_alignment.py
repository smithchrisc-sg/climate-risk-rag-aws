#!/usr/bin/env python3
"""
Analyze NLP entities and key phrases alignment with climate risk ontology
"""

import json
import requests
from collections import defaultdict, Counter
from typing import Dict, List, Set
import re

def load_nlp_results():
    """Load entities and key phrases from extracted files"""
    
    # Load entities first
    import subprocess
    import os
    
    # Make sure we're in the right directory and extract entities
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
    import subprocess
    import tempfile
    
    # Create payload for getting concepts
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
        # Call admin ontology manager
        result = subprocess.run([
            'aws', 'lambda', 'invoke',
            '--function-name', 'solve-global-kr-admin-ontology-manager',
            '--cli-binary-format', 'raw-in-base64-out',
            '--payload', f'file://{payload_file}',
            '--region', 'us-east-1',
            '/tmp/ontology_concepts.json'
        ], capture_output=True, text=True, check=True)
        
        # Read the response
        with open('/tmp/ontology_concepts.json', 'r') as f:
            response_data = json.load(f)
        
        if response_data.get('statusCode') == 200:
            body = json.loads(response_data['body'])
            if body.get('success'):
                concept_list = body['result']['concepts']
                
                concepts = {}
                for concept in concept_list:
                    label = concept['label']
                    concepts[label.lower()] = {
                        'uri': concept['uri'],
                        'label': label,
                        'comment': concept.get('description', '')
                    }
                
                return concepts
            else:
                print(f"❌ Admin ontology manager error: {body.get('error', 'Unknown error')}")
                return {}
        else:
            print(f"❌ Lambda invocation failed: {response_data}")
            return {}
            
    except Exception as e:
        print(f"❌ Error calling admin ontology manager: {e}")
        return {}
    finally:
        import os
        os.unlink(payload_file)

def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    # Remove extra whitespace, newlines, convert to lowercase
    text = re.sub(r'\s+', ' ', text.strip().lower())
    # Remove common punctuation
    text = re.sub(r'[^\w\s-]', '', text)
    return text

def find_concept_matches(nlp_text: str, ontology_concepts: Dict) -> List[Dict]:
    """Find potential matches between NLP text and ontology concepts"""
    normalized_nlp = normalize_text(nlp_text)
    matches = []
    
    for concept_label, concept_data in ontology_concepts.items():
        normalized_concept = normalize_text(concept_label)
        
        # Exact match
        if normalized_nlp == normalized_concept:
            matches.append({
                'type': 'exact',
                'confidence': 1.0,
                'concept': concept_data
            })
        # Partial match (concept contains NLP text or vice versa)
        elif normalized_concept in normalized_nlp or normalized_nlp in normalized_concept:
            confidence = min(len(normalized_nlp), len(normalized_concept)) / max(len(normalized_nlp), len(normalized_concept))
            matches.append({
                'type': 'partial',
                'confidence': confidence,
                'concept': concept_data
            })
        # Word overlap
        elif len(set(normalized_nlp.split()) & set(normalized_concept.split())) > 0:
            nlp_words = set(normalized_nlp.split())
            concept_words = set(normalized_concept.split())
            overlap = len(nlp_words & concept_words)
            confidence = overlap / max(len(nlp_words), len(concept_words))
            if confidence > 0.3:  # Only include if significant overlap
                matches.append({
                    'type': 'word_overlap',
                    'confidence': confidence,
                    'concept': concept_data
                })
    
    return sorted(matches, key=lambda x: x['confidence'], reverse=True)

def analyze_alignment():
    """Main analysis function"""
    print("🔍 Loading NLP results...")
    entities_data, keyphrases_data = load_nlp_results()
    
    print("🔍 Loading ontology concepts...")
    ontology_concepts = get_ontology_concepts()
    
    print(f"📊 Found {len(ontology_concepts)} ontology concepts")
    print(f"📊 Found {len(entities_data.get('Entities', []))} entities")
    print(f"📊 Found {len(keyphrases_data.get('KeyPhrases', []))} key phrases")
    
    # Analyze entities
    print("\n" + "="*80)
    print("🏷️  ENTITY ANALYSIS")
    print("="*80)
    
    entity_matches = defaultdict(list)
    entity_types = Counter()
    
    for entity in entities_data.get('Entities', [])[:50]:  # Limit for analysis
        entity_text = entity['Text']
        entity_type = entity['Type']
        score = entity['Score']
        
        entity_types[entity_type] += 1
        
        matches = find_concept_matches(entity_text, ontology_concepts)
        if matches:
            entity_matches[entity_type].append({
                'text': entity_text,
                'score': score,
                'matches': matches[:3]  # Top 3 matches
            })
    
    print(f"\n📈 Entity Types Distribution:")
    for entity_type, count in entity_types.most_common():
        print(f"  {entity_type}: {count}")
    
    print(f"\n🎯 Entities with Ontology Matches:")
    for entity_type, matches in entity_matches.items():
        if matches:
            print(f"\n  {entity_type} ({len(matches)} matches):")
            for match in matches[:5]:  # Top 5 per type
                print(f"    '{match['text']}' (score: {match['score']:.3f})")
                for concept_match in match['matches']:
                    print(f"      → {concept_match['concept']['label']} ({concept_match['type']}, {concept_match['confidence']:.3f})")
    
    # Analyze key phrases
    print("\n" + "="*80)
    print("🔑 KEY PHRASE ANALYSIS")
    print("="*80)
    
    keyphrase_matches = []
    
    for keyphrase in keyphrases_data.get('KeyPhrases', [])[:50]:  # Limit for analysis
        phrase_text = keyphrase['Text']
        score = keyphrase['Score']
        
        matches = find_concept_matches(phrase_text, ontology_concepts)
        if matches:
            keyphrase_matches.append({
                'text': phrase_text,
                'score': score,
                'matches': matches[:3]  # Top 3 matches
            })
    
    print(f"\n🎯 Key Phrases with Ontology Matches ({len(keyphrase_matches)} total):")
    for match in keyphrase_matches[:10]:  # Top 10
        print(f"  '{match['text']}' (score: {match['score']:.3f})")
        for concept_match in match['matches']:
            print(f"    → {concept_match['concept']['label']} ({concept_match['type']}, {concept_match['confidence']:.3f})")
    
    # Summary analysis
    print("\n" + "="*80)
    print("📋 ALIGNMENT SUMMARY")
    print("="*80)
    
    total_entities = len(entities_data.get('Entities', []))
    matched_entities = sum(len(matches) for matches in entity_matches.values())
    
    total_keyphrases = len(keyphrases_data.get('KeyPhrases', []))
    matched_keyphrases = len(keyphrase_matches)
    
    entity_pct = (matched_entities/total_entities*100) if total_entities > 0 else 0
    keyphrase_pct = (matched_keyphrases/total_keyphrases*100) if total_keyphrases > 0 else 0
    
    print(f"Entity Alignment: {matched_entities}/{total_entities} ({entity_pct:.1f}%)")
    print(f"Key Phrase Alignment: {matched_keyphrases}/{total_keyphrases} ({keyphrase_pct:.1f}%)")
    
    # Identify gaps
    print(f"\n🔍 ONTOLOGY COVERAGE GAPS:")
    
    # Find ontology concepts that weren't matched
    matched_concept_labels = set()
    for matches in entity_matches.values():
        for match in matches:
            for concept_match in match['matches']:
                matched_concept_labels.add(concept_match['concept']['label'].lower())
    
    for match in keyphrase_matches:
        for concept_match in match['matches']:
            matched_concept_labels.add(concept_match['concept']['label'].lower())
    
    unmatched_concepts = []
    for concept_label, concept_data in ontology_concepts.items():
        if concept_label not in matched_concept_labels:
            unmatched_concepts.append(concept_data['label'])
    
    print(f"Unmatched ontology concepts: {len(unmatched_concepts)}/{len(ontology_concepts)}")
    if unmatched_concepts:
        print("Sample unmatched concepts:")
        for concept in unmatched_concepts[:10]:
            print(f"  - {concept}")

if __name__ == "__main__":
    analyze_alignment()
