#!/usr/bin/env python3
"""
Pseudo Document Generator for Solution Ingestion
Creates comprehensive document text for improved TF/IDF indexing accuracy.
"""

import logging
import sys
import os
from typing import List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.solution import Solution

logger = logging.getLogger(__name__)

class PseudoDocumentGenerator:
    """Generates pseudo-documents with enhanced text content for TF/IDF indexing."""
    
    def generate_pseudo_document(self, solution: Solution) -> str:
        """
        Generate comprehensive pseudo-document text for improved TF/IDF precision/recall.
        
        Args:
            solution: Solution object with all CSV data
            
        Returns:
            Enhanced document text combining introduction + original content
        """
        parts = []
        
        # Generate contextual introduction
        intro = self._generate_introduction(solution)
        if intro:
            parts.append(intro)
        
        # Add original content sections
        content_sections = [
            solution.description,
            solution.key_highlights, 
            solution.results
        ]
        
        for section in content_sections:
            if section and section.strip():
                parts.append(section.strip())
        
        # Combine all parts
        pseudo_document = '\n\n'.join(parts)
        
        logger.debug(f"Generated pseudo-document ({len(pseudo_document)} chars) for {solution.id}")
        return pseudo_document
    
    def _generate_introduction(self, solution: Solution) -> str:
        """Generate contextual introduction paragraph."""
        intro_parts = []
        
        # Base introduction with solution name
        if solution.name:
            intro_parts.append(f"This solution, '{solution.name}',")
        else:
            intro_parts.append("This solution")
        
        # Add risk and location context
        context_parts = []
        if solution.type_of_risk:
            context_parts.append(f"addresses {solution.type_of_risk.lower()} risks")
        if solution.country:
            context_parts.append(f"in {solution.country}")
        
        if context_parts:
            intro_parts.append(" ".join(context_parts) + ".")
        
        # Add implementation details
        impl_parts = []
        if solution.type_of_solution:
            impl_parts.append(f"It represents a {solution.type_of_solution.lower()} approach")
        if solution.theme:
            impl_parts.append(f"focused on {solution.theme.lower()}")
        if solution.year_of_implementation:
            impl_parts.append(f"implemented in {solution.year_of_implementation}")
        
        if impl_parts:
            intro_parts.append(" ".join(impl_parts) + ".")
        
        # Add organizational context
        org_parts = []
        orgs = []
        if solution.public_organisations and solution.public_organisations.strip():
            orgs.append("public sector organizations")
        if solution.international_organisations and solution.international_organisations.strip():
            orgs.append("international organizations")
        if solution.private_organisations and solution.private_organisations.strip():
            orgs.append("private sector entities")
        
        if orgs:
            if len(orgs) == 1:
                org_parts.append(f"The solution involves {orgs[0]}.")
            elif len(orgs) == 2:
                org_parts.append(f"The solution involves {orgs[0]} and {orgs[1]}.")
            else:
                org_parts.append(f"The solution involves {', '.join(orgs[:-1])}, and {orgs[-1]}.")
        
        if solution.ppp and solution.ppp.strip().lower() in ['yes', 'true', '1']:
            org_parts.append("This represents a public-private partnership initiative.")
        
        if org_parts:
            intro_parts.extend(org_parts)
        
        return " ".join(intro_parts)
    
    def process_solutions(self, solutions: List[Solution]) -> List[Solution]:
        """Process multiple solutions to add pseudo-document text."""
        processed = []
        
        for solution in solutions:
            try:
                pseudo_doc = self.generate_pseudo_document(solution)
                # Add pseudo_document_text to solution
                solution.pseudo_document_text = pseudo_doc
                processed.append(solution)
                
            except Exception as e:
                logger.error(f"Failed to generate pseudo-document for {solution.id}: {e}")
                # Add original content as fallback
                solution.pseudo_document_text = solution.get_full_text()
                processed.append(solution)
        
        logger.info(f"Generated pseudo-documents for {len(processed)} solutions")
        return processed

def main():
    """Test pseudo-document generation."""
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from parsers.csv_parser import CSVParser
    
    print("Pseudo Document Generator Test")
    print("=" * 50)
    
    # Parse solutions
    parser = CSVParser()
    solutions = list(parser.parse_all_files())
    
    # Generate pseudo-documents for first 3 solutions
    generator = PseudoDocumentGenerator()
    test_solutions = solutions[:3]
    
    processed = generator.process_solutions(test_solutions)
    
    for i, solution in enumerate(processed, 1):
        print(f"\n--- Solution {i}: {solution.name[:60]}... ---")
        print(f"Original length: {len(solution.get_full_text())} chars")
        print(f"Pseudo-doc length: {len(solution.pseudo_document_text)} chars")
        print(f"Source URL: {solution.source_url}")
        print("\nPseudo-document preview:")
        print(solution.pseudo_document_text[:500] + "..." if len(solution.pseudo_document_text) > 500 else solution.pseudo_document_text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
