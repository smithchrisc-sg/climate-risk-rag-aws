#!/usr/bin/env python3
"""
Test the refactored bulk processing pipeline with entity mapping.
"""

import logging
import sys
from pathlib import Path

# Set up path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "database_core_layer" / "python"))
sys.path.append(str(current_dir / "knowledge_graph_layer" / "python"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_refactored_pipeline():
    """Test the refactored pipeline with entity mapping."""
    try:
        from parsers.csv_parser import CSVParser
        from generators.structured_pseudo_document_generator import StructuredPseudoDocumentGenerator
        from generators.production_rdf_generator import ProductionRDFGenerator
        from integrated_entity_mapper import IntegratedEntityMapper
        
        print("Testing Refactored Pipeline with Entity Mapping")
        print("=" * 50)
        
        # Parse first 3 solutions only
        parser = CSVParser()
        csv_file = Path("input_data/natural_catastrophe_26-Sep-2025.csv")
        
        solutions = list(parser.parse_csv_file(csv_file))[:3]
        print("Testing with {} solutions".format(len(solutions)))
        
        # Generate pseudo documents
        pseudo_gen = StructuredPseudoDocumentGenerator()
        processed_solutions = pseudo_gen.process_solutions(solutions)
        
        # Initialize entity mapper and RDF generator
        entity_mapper = IntegratedEntityMapper()
        rdf_generator = ProductionRDFGenerator(entity_mapper)
        
        # Enhance solutions with entity mappings
        for solution in processed_solutions:
            entity_mapper.enhance_solution_metadata(solution)
        
        # Generate RDF for each solution
        for i, solution in enumerate(processed_solutions, 1):
            print("\nProcessing solution {}: {}...".format(i, solution.name[:50]))
            
            # Generate complete RDF
            rdf_content = rdf_generator.generate_document_rdf(solution)
            
            print("  RDF size: {} characters".format(len(rdf_content)))
            print("  Has organization_uri: {}".format(hasattr(solution, 'organization_uri')))
            print("  Has country_uri: {}".format(hasattr(solution, 'country_uri')))
            print("  Has concept_uris: {}".format(hasattr(solution, 'concept_uris')))
            
            # Show first few lines of RDF
            rdf_lines = rdf_content.split('\n')[:10]
            print("  RDF preview:")
            for line in rdf_lines:
                if line.strip():
                    print("    {}".format(line))
        
        print("\nRefactored pipeline test completed!")
        print("Entity mapping statistics:")
        print("  Organizations: {}".format(len(entity_mapper.organization_cache)))
        print("  Geography mappings: {}".format(len(entity_mapper.geography_mapper.country_mappings)))
        print("  Vocabulary concepts: {}".format(len(entity_mapper.vocabulary_mapper.concept_mappings)))
        
        return True
        
    except Exception as e:
        logger.error("Test failed: {}".format(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_refactored_pipeline()
    if not success:
        sys.exit(1)
