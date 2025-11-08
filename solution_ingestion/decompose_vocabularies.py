#!/usr/bin/env python3
"""
Vocabulary Decomposer
Decomposes comma-separated vocabulary values into individual concepts for RDF generation.
"""

import csv
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set

class VocabularyDecomposer:
    """Decomposes vocabularies into individual concepts."""
    
    def __init__(self, input_dir: str = "input_data"):
        self.input_dir = Path(input_dir)
        self.risk_concepts = Counter()
        self.solution_concepts = Counter()
        self.theme_concepts = Counter()
        
    def normalize_concept(self, concept: str) -> str:
        """Normalize concept variations to canonical forms."""
        concept = concept.strip()
        
        # Skip if it contains multiple concepts (should be split differently)
        if any(separator in concept for separator in ['\n', ' Risk ', ' Collaboration', ' Accessibility']):
            # These are malformed entries that contain multiple concepts
            return None
        
        # Normalization rules
        normalization_rules = {
            # Solution type normalizations
            'Increased Penetration': 'Increase Penetration',
            
            # Risk type normalizations
            'Earthquakes & Typhoons': 'Natural Catastrophe',
            
            # Theme normalizations - clean up variations
            'Leveraging Tech': 'Leveraging Technology',
            'Increasing Response Efficiency': 'Increase Response Efficiency',
            'Raise Awareness': 'Raising Awareness',
            'Accessibilty': 'Accessibility',  # Fix typo
        }
        
        # Apply direct mappings
        if concept in normalization_rules:
            return normalization_rules[concept]
        
        # Pattern-based normalizations
        normalized = ' '.join(concept.split())
        
        # Handle verb tense variations
        if normalized.endswith('ed Penetration'):
            normalized = normalized.replace('ed Penetration', 'e Penetration')
        
        return normalized
    
    def clean_and_split_value(self, value: str) -> List[str]:
        """Clean and split comma-separated value into individual concepts."""
        if not value or value.upper() in ['NIL', 'N/A', 'NULL', '', 'CANNOT BE DETERMINED']:
            return []
        
        # Split by comma and clean each concept
        concepts = []
        for concept in value.split(','):
            cleaned = concept.strip()
            if cleaned:
                # Apply normalization
                normalized = self.normalize_concept(cleaned)
                if normalized:
                    concepts.append(normalized)
        
        return concepts
    
    def create_concept_uri(self, concept: str, concept_type: str) -> str:
        """Create URI for a concept."""
        # Normalize for URI
        normalized = re.sub(r'[^\w\s-]', '', concept.lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        normalized = re.sub(r'_+', '_', normalized).strip('_')
        
        return f"sg:{concept_type}_{normalized}"
    
    def process_csv_file(self, csv_file: Path):
        """Process a single CSV file and extract individual concepts."""
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Extract and decompose risk types
                    risk_value = row.get('Type of Risk', '')
                    risk_concepts = self.clean_and_split_value(risk_value)
                    for concept in risk_concepts:
                        self.risk_concepts[concept] += 1
                    
                    # Extract and decompose solution types
                    solution_value = row.get('Type of Solution', '') or row.get('Type of Solution ', '')
                    solution_concepts = self.clean_and_split_value(solution_value)
                    for concept in solution_concepts:
                        self.solution_concepts[concept] += 1
                    
                    # Extract and decompose themes
                    theme_value = row.get('Theme', '')
                    theme_concepts = self.clean_and_split_value(theme_value)
                    for concept in theme_concepts:
                        self.theme_concepts[concept] += 1
                        
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
    
    def analyze_all_csv_files(self):
        """Process all CSV files."""
        csv_files = list(self.input_dir.glob("*.csv"))
        
        for csv_file in csv_files:
            self.process_csv_file(csv_file)
    
    def generate_concepts_rdf(self) -> str:
        """Generate RDF for all individual concepts."""
        rdf_lines = [
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            "@prefix sg: <http://solve.global/knowledge-commons/> .",
            "",
            "# Concept Schemes",
            "",
            "sg:RiskTypeScheme a skos:ConceptScheme ;",
            '    rdfs:label "Risk Type Concept Scheme" ;',
            '    skos:prefLabel "Risk Types" .',
            "",
            "sg:SolutionTypeScheme a skos:ConceptScheme ;",
            '    rdfs:label "Solution Type Concept Scheme" ;',
            '    skos:prefLabel "Solution Types" .',
            "",
            "sg:ThemeScheme a skos:ConceptScheme ;",
            '    rdfs:label "Theme Concept Scheme" ;',
            '    skos:prefLabel "Themes" .',
            "",
            "# Risk Type Concepts",
            ""
        ]
        
        # Generate risk type concepts
        for concept, count in self.risk_concepts.most_common():
            uri = self.create_concept_uri(concept, "RiskType")
            rdf_lines.extend([
                f"{uri} a skos:Concept ;",
                f"    skos:inScheme sg:RiskTypeScheme ;",
                f'    skos:prefLabel "{self.escape_literal(concept)}" ;',
                f'    rdfs:label "{self.escape_literal(concept)}" .',
                ""
            ])
        
        rdf_lines.append("# Solution Type Concepts")
        rdf_lines.append("")
        
        # Generate solution type concepts
        for concept, count in self.solution_concepts.most_common():
            uri = self.create_concept_uri(concept, "SolutionType")
            rdf_lines.extend([
                f"{uri} a skos:Concept ;",
                f"    skos:inScheme sg:SolutionTypeScheme ;",
                f'    skos:prefLabel "{self.escape_literal(concept)}" ;',
                f'    rdfs:label "{self.escape_literal(concept)}" .',
                ""
            ])
        
        rdf_lines.append("# Theme Concepts")
        rdf_lines.append("")
        
        # Generate theme concepts
        for concept, count in self.theme_concepts.most_common():
            uri = self.create_concept_uri(concept, "Theme")
            rdf_lines.extend([
                f"{uri} a skos:Concept ;",
                f"    skos:inScheme sg:ThemeScheme ;",
                f'    skos:prefLabel "{self.escape_literal(concept)}" ;',
                f'    rdfs:label "{self.escape_literal(concept)}" .',
                ""
            ])
        
        return '\n'.join(rdf_lines)
    
    def escape_literal(self, text: str) -> str:
        """Escape text for RDF literal."""
        if not text:
            return ""
        return text.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
    
    def get_decomposed_stats(self) -> Dict:
        """Get statistics about decomposed concepts."""
        return {
            'risk_concepts': len(self.risk_concepts),
            'solution_concepts': len(self.solution_concepts),
            'theme_concepts': len(self.theme_concepts),
            'total_concepts': len(self.risk_concepts) + len(self.solution_concepts) + len(self.theme_concepts)
        }

def main():
    """Generate individual concept RDF."""
    print("Vocabulary Decomposer - Individual Concepts")
    print("=" * 45)
    
    decomposer = VocabularyDecomposer()
    decomposer.analyze_all_csv_files()
    
    # Show statistics
    stats = decomposer.get_decomposed_stats()
    print(f"\nDecomposed Concept Statistics:")
    print(f"  Risk Type concepts: {stats['risk_concepts']}")
    print(f"  Solution Type concepts: {stats['solution_concepts']}")
    print(f"  Theme concepts: {stats['theme_concepts']}")
    print(f"  Total individual concepts: {stats['total_concepts']}")
    
    # Show top concepts
    print(f"\nTop Risk Type Concepts:")
    for concept, count in decomposer.risk_concepts.most_common(10):
        print(f"  {count:3d}x {concept}")
    
    print(f"\nTop Solution Type Concepts:")
    for concept, count in decomposer.solution_concepts.most_common(10):
        print(f"  {count:3d}x {concept}")
    
    print(f"\nTop Theme Concepts:")
    for concept, count in decomposer.theme_concepts.most_common(10):
        print(f"  {count:3d}x {concept}")
    
    # Generate RDF
    rdf_content = decomposer.generate_concepts_rdf()
    
    # Save to file
    output_file = "vocabulary_concepts.ttl"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(rdf_content)
    
    print(f"\nConcept RDF saved to: {output_file}")
    print("Ready for individual concept triples in solution RDF!")

if __name__ == "__main__":
    main()
