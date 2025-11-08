#!/usr/bin/env python3
"""
Structured Pseudo Document Generator for Solution Ingestion
Creates production-aligned pseudo documents with explicit section headers and mad-lib synthesis.
"""

import logging
import sys
import os
from typing import List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.solution import Solution

logger = logging.getLogger(__name__)

class StructuredPseudoDocumentGenerator:
    """Generates structured pseudo-documents matching production schema requirements."""
    
    def generate_pseudo_document(self, solution: Solution) -> str:
        """
        Generate structured pseudo-document with explicit section headers.
        
        Args:
            solution: Solution object with all CSV data
            
        Returns:
            Structured document text with sections: Title, Organizations, Introduction, Description, Key Highlights, Results, Contact Information
        """
        sections = []
        
        # Title section (from Name column)
        if solution.name and solution.name.strip():
            sections.append(solution.name.strip())
        
        # Organizations section (from three organization columns)
        org_section = self._generate_organizations_section(solution)
        if org_section:
            sections.append(org_section)
        
        # Introduction section (mad-lib synthesis)
        sections.append("Introduction")
        intro = self._generate_mad_lib_introduction(solution)
        if intro:
            sections.append(intro)
        
        # Description section
        sections.append("Description")
        if solution.description and solution.description.strip():
            sections.append(solution.description.strip())
        
        # Key Highlights section
        sections.append("Key Highlights")
        if solution.key_highlights and solution.key_highlights.strip():
            sections.append(solution.key_highlights.strip())
        
        # Results section
        sections.append("Results")
        if solution.results and solution.results.strip():
            sections.append(solution.results.strip())
        
        # Contact Information section
        sections.append("Contact Information")
        if solution.contact_information and solution.contact_information.strip():
            sections.append(solution.contact_information.strip())
        
        # Combine all sections with double newlines
        pseudo_document = '\n\n'.join(sections)
        
        logger.debug(f"Generated structured pseudo-document ({len(pseudo_document)} chars) for {solution.id}")
        return pseudo_document
    
    def _generate_organizations_section(self, solution: Solution) -> str:
        """Generate organizations section from three organization columns."""
        org_sections = []
        
        # Collect organizations from all three columns, skipping empty ones
        if solution.public_organisations and solution.public_organisations.strip():
            org_sections.append(solution.public_organisations.strip())
        
        if solution.international_organisations and solution.international_organisations.strip():
            org_sections.append(solution.international_organisations.strip())
        
        if solution.private_organisations and solution.private_organisations.strip():
            org_sections.append(solution.private_organisations.strip())
        
        if not org_sections:
            return ""
        
        # Join with "and" connector as shown in example
        if len(org_sections) == 1:
            return org_sections[0]
        else:
            return '\n\nand \n\n'.join(org_sections)
    
    def _generate_mad_lib_introduction(self, solution: Solution) -> str:
        """Generate mad-lib style introduction paragraph."""
        # Template: This solution, [[Name]] addresses [[Type of Risk]] [[through public private partnerships]] 
        # in [[Country]] between [[All Organizations]]. The program was implemented in [[Year of Implementation]] 
        # and focuses on [[Theme]].
        
        intro_parts = []
        
        # Start with solution name
        if solution.name and solution.name.strip():
            intro_parts.append(f"This solution, {solution.name.strip()}")
        else:
            intro_parts.append("This solution")
        
        # Add risk type
        if solution.type_of_risk and solution.type_of_risk.strip():
            intro_parts.append(f"addresses {solution.type_of_risk.strip().lower()}")
        
        # Add PPP context if applicable
        if solution.ppp and solution.ppp.strip().lower() in ['yes', 'true', '1']:
            intro_parts.append("through public private partnerships")
        
        # Add country
        if solution.country and solution.country.strip():
            intro_parts.append(f"in {solution.country.strip()}")
        
        # Add organizations - keep as single line
        all_orgs = self._get_all_organizations_list(solution)
        if all_orgs:
            intro_parts.append(f"between {all_orgs}.")
        else:
            intro_parts.append(".")
        
        # Add implementation year and theme with correct grammar
        impl_parts = []
        if solution.year_of_implementation and solution.year_of_implementation.strip():
            impl_parts.append(f"The program was implemented in {solution.year_of_implementation.strip()}")
        
        if solution.theme and solution.theme.strip():
            # Format theme with proper conjunctions
            formatted_theme = self._format_theme_list(solution.theme.strip())
            if impl_parts:
                impl_parts.append(f"and focuses on {formatted_theme}.")
            else:
                impl_parts.append(f"The solution focuses on {formatted_theme}.")
        elif impl_parts:
            impl_parts[0] += "."
        
        # Combine all parts into single paragraph
        full_intro = " ".join(intro_parts)
        if impl_parts:
            full_intro += " " + " ".join(impl_parts)
        
        return full_intro
    
    def _format_theme_list(self, theme_text: str) -> str:
        """Format theme text with proper conjunctions."""
        if not theme_text:
            return ""
        
        # Split by comma and clean up
        themes = [theme.strip() for theme in theme_text.split(',') if theme.strip()]
        
        if len(themes) == 1:
            return themes[0].lower()
        elif len(themes) == 2:
            return f"{themes[0].lower()} and {themes[1].lower()}"
        else:
            return f"{', '.join([t.lower() for t in themes[:-1]])}, and {themes[-1].lower()}"
    
    def _get_all_organizations_list(self, solution: Solution) -> str:
        """Get comma-separated list of all organizations, skipping empty values."""
        all_orgs = []
        
        # Collect from all organization fields, skipping empty ones
        for org_field in [solution.public_organisations, solution.international_organisations, solution.private_organisations]:
            if org_field and org_field.strip():
                # Split by comma and clean up, skipping empty entries
                orgs = [org.strip() for org in org_field.split(',') if org.strip()]
                all_orgs.extend(orgs)
        
        if not all_orgs:
            return ""
        
        # Join with commas and "and" for last item
        if len(all_orgs) == 1:
            return all_orgs[0]
        elif len(all_orgs) == 2:
            return f"{all_orgs[0]} and {all_orgs[1]}"
        else:
            return f"{', '.join(all_orgs[:-1])}, and {all_orgs[-1]}"
    
    def process_solutions(self, solutions: List[Solution]) -> List[Solution]:
        """Process multiple solutions to add structured pseudo-document text."""
        processed = []
        
        for solution in solutions:
            try:
                pseudo_doc = self.generate_pseudo_document(solution)
                # Add pseudo_document_text to solution
                solution.pseudo_document_text = pseudo_doc
                processed.append(solution)
                
            except Exception as e:
                logger.error(f"Failed to generate structured pseudo-document for {solution.id}: {e}")
                # Add original content as fallback
                solution.pseudo_document_text = solution.get_full_text()
                processed.append(solution)
        
        logger.info(f"Generated structured pseudo-documents for {len(processed)} solutions")
        return processed

def main():
    """Test structured pseudo-document generation."""
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from parsers.csv_parser import CSVParser
    
    print("Structured Pseudo Document Generator Test")
    print("=" * 60)
    
    # Parse solutions
    parser = CSVParser()
    solutions = list(parser.parse_all_files())
    
    # Generate structured pseudo-documents for first solution
    generator = StructuredPseudoDocumentGenerator()
    test_solution = solutions[0]
    
    processed = generator.process_solutions([test_solution])
    solution = processed[0]
    
    print(f"\n--- Solution: {solution.name} ---")
    print(f"Country: {solution.country}")
    print(f"Type of Risk: {solution.type_of_risk}")
    print(f"PPP: {solution.ppp}")
    print(f"Year: {solution.year_of_implementation}")
    print(f"Theme: {solution.theme}")
    print(f"\nStructured Pseudo-Document:")
    print("=" * 60)
    print(solution.pseudo_document_text)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
