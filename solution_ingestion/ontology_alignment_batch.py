#!/usr/bin/env python3
"""
Ontology Alignment Batch Job
Extracts ontology concepts from solutions using LLM + rules and stores as RDF alignment triples.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_graph_layer.utils.KnowledgeGraphManager import KnowledgeGraphManager
from database_core_layer.utils.DatabaseManager import DatabaseManager

# Import extractors (to be created)
from extractors.llm_extractor import LLMExtractor
from extractors.rule_enhancer import RuleEnhancer
from generators.alignment_rdf_generator import AlignmentRDFGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OntologyAlignmentBatch:
    """Main orchestrator for ontology alignment batch processing."""
    
    def __init__(self, args):
        self.args = args
        self.kg_manager = KnowledgeGraphManager()
        self.db_manager = DatabaseManager()
        self.llm_extractor = LLMExtractor(self.kg_manager)
        self.rule_enhancer = RuleEnhancer()
        self.rdf_generator = AlignmentRDFGenerator()
        
        # Statistics
        self.stats = {
            'total': 0,
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
    
    def run(self):
        """Execute batch processing."""
        logger.info("Starting ontology alignment batch job")
        self.stats['start_time'] = datetime.now()
        
        try:
            # Step 1: Get solutions from KG
            solutions = self.get_solutions_from_kg()
            self.stats['total'] = len(solutions)
            logger.info(f"Found {len(solutions)} solutions to process")
            
            # Step 2: Process each solution
            for i, solution in enumerate(solutions, 1):
                logger.info(f"Processing solution {i}/{len(solutions)}: {solution['doc_id']}")
                
                try:
                    self.process_solution(solution)
                    self.stats['processed'] += 1
                    
                    # Small delay to avoid Neptune CPU spikes
                    if i < len(solutions):
                        time.sleep(2)
                        
                except Exception as e:
                    logger.error(f"Failed to process {solution['doc_id']}: {e}", exc_info=True)
                    self.stats['failed'] += 1
                    
                    # Write error file if output-dir specified
                    if self.args.output_dir:
                        self.write_error_file(solution['doc_id'], e)
            
            # Step 3: Report results
            self.stats['end_time'] = datetime.now()
            self.print_summary()
            
        except Exception as e:
            logger.error(f"Batch job failed: {e}", exc_info=True)
            sys.exit(1)
    
    def get_solutions_from_kg(self) -> List[Dict]:
        """Query Neptune KG for all Solutions."""
        query = """
        PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
        PREFIX sg: <http://solve.global/knowledge-commons/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?solution ?doc_id ?title 
               (GROUP_CONCAT(DISTINCT ?riskLabel; separator=", ") AS ?riskTypes)
               (GROUP_CONCAT(DISTINCT ?solutionLabel; separator=", ") AS ?solutionTypes)
        WHERE {
            ?solution a sgd:Solution ;
                      dcterms:identifier ?doc_id ;
                      dcterms:title ?title .
            
            OPTIONAL {
                ?solution sg:riskType ?riskType .
                ?riskType rdfs:label ?riskLabel .
            }
            
            OPTIONAL {
                ?solution sg:solutionType ?solutionType .
                ?solutionType rdfs:label ?solutionLabel .
            }
        }
        GROUP BY ?solution ?doc_id ?title
        ORDER BY ?doc_id
        """
        
        # Add LIMIT if specified
        if self.args.limit:
            query += f"\nLIMIT {self.args.limit}"
        
        results = self.kg_manager.execute_sparql_query(query)
        
        # Filter by specific doc_ids if provided
        if self.args.doc_ids:
            results = [r for r in results if r['doc_id'] in self.args.doc_ids]
        
        return results
    
    def process_solution(self, solution: Dict):
        """Process a single solution through the pipeline."""
        doc_id = solution['doc_id']
        
        # Step 1: Get chunks by section from KG + S3
        chunks_by_section = self.get_chunks_by_section(doc_id)
        
        if not chunks_by_section:
            logger.warning(f"No chunks found for {doc_id}, skipping")
            self.stats['skipped'] += 1
            return
        
        # Step 2: Extract ontology concepts with LLM
        if self.args.skip_llm:
            extraction = {'risks': [], 'mechanisms': [], 'impacts': [], 'countries': []}
        else:
            extraction = self.llm_extractor.extract(
                doc_id=doc_id,
                chunks_by_section=chunks_by_section,
                kg_metadata=solution
            )
        
        # Step 3: Enhance with rules
        enhanced = self.rule_enhancer.enhance(extraction, chunks_by_section)
        
        # Step 4: Calculate overall confidence
        confidence = self.calculate_confidence(enhanced)
        
        # Step 5: Generate RDF
        rdf_content = self.rdf_generator.generate(
            doc_id=doc_id,
            extraction=enhanced,
            confidence=confidence,
            chunks_by_section=chunks_by_section
        )
        
        # Step 6: Output based on mode
        if self.args.dry_run:
            logger.info(f"DRY RUN - Generated RDF for {doc_id}")
            logger.debug(rdf_content[:500] + "...")
            return
        
        if self.args.output_dir:
            self.write_ttl_file(doc_id, rdf_content, enhanced, confidence)
        
        if self.args.load_to_neptune:
            self.load_to_neptune(doc_id, rdf_content)
    
    def get_chunks_by_section(self, doc_id: str) -> Dict[str, List[Dict]]:
        """Query Neptune for section structure and retrieve chunk content from S3."""
        import boto3
        
        # Query Neptune for section → chunks mapping using actual document structure
        query = f"""
        PREFIX sgd: <http://solve.global/knowledge-commons/document-structure#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        
        SELECT ?sectionTitle ?chunk WHERE {{
            ?solution a sgd:Solution ;
                      dcterms:identifier "{doc_id}" ;
                      sgd:hasChild ?section .
            ?section dcterms:title ?sectionTitle ;
                     sgd:firstChild ?firstChunk .
            ?firstChunk (sgd:nextSibling)* ?chunk .
        }}
        ORDER BY ?section ?chunk
        """
        
        results = self.kg_manager.execute_sparql_query(query)
        
        # Group by section and retrieve content from S3
        s3_client = boto3.client('s3')
        chunks_by_section = {}
        
        for row in results:
            section_title = str(row['sectionTitle'])
            chunk_uri = str(row['chunk'])
            
            if section_title not in chunks_by_section:
                chunks_by_section[section_title] = []
            
            # Extract chunk number from URI (last 4 digits)
            chunk_str = chunk_uri.split('/')[-1] if '/' in chunk_uri else chunk_uri
            # Get last 4 characters as chunk number
            try:
                chunk_num = int(chunk_str[-4:])
            except (ValueError, IndexError):
                logger.warning(f"Could not extract chunk number from URI: {chunk_uri}")
                continue
            
            # Retrieve chunk content from S3 using actual key pattern
            try:
                s3_key = f"data-lake/{doc_id}/{doc_id}_chunk_{chunk_num:04d}.json"
                response = s3_client.get_object(Bucket='solve-global-kr-dl-chunks-861276078413-us-east-1', Key=s3_key)
                chunk_data = json.loads(response['Body'].read().decode('utf-8'))
                
                chunks_by_section[section_title].append({
                    'uri': chunk_uri,
                    'chunk_num': chunk_num,
                    'text': chunk_data.get('text', '')
                })
            except Exception as e:
                logger.warning(f"Failed to retrieve chunk {s3_key} from S3: {e}")
        
        return chunks_by_section
    
    def calculate_confidence(self, extraction: Dict) -> float:
        """Calculate overall confidence score."""
        all_confidences = []
        
        for category in ['risks', 'mechanisms', 'impacts', 'countries']:
            for item in extraction.get(category, []):
                all_confidences.append(item.get('confidence', 0.0))
        
        if not all_confidences:
            return 0.0
        
        return sum(all_confidences) / len(all_confidences)
    
    def write_ttl_file(self, doc_id: str, rdf_content: str, extraction: Dict, confidence: float):
        """Write RDF to local TTL file."""
        output_path = Path(self.args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Write TTL file
        ttl_file = output_path / f"alignment_{doc_id}.ttl"
        with open(ttl_file, 'w', encoding='utf-8') as f:
            f.write(rdf_content)
        
        # Write metadata JSON
        metadata_file = output_path / f"alignment_{doc_id}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'doc_id': doc_id,
                'timestamp': datetime.now().isoformat(),
                'extraction': extraction,
                'overall_confidence': confidence
            }, f, indent=2)
        
        logger.info(f"Wrote TTL to {ttl_file}")
    
    def write_error_file(self, doc_id: str, error: Exception):
        """Write error details to JSON file."""
        import traceback
        
        output_path = Path(self.args.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        error_file = output_path / f"alignment_{doc_id}_ERROR.json"
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump({
                'doc_id': doc_id,
                'timestamp': datetime.now().isoformat(),
                'error': str(error),
                'traceback': traceback.format_exc()
            }, f, indent=2)
    
    def load_to_neptune(self, doc_id: str, rdf_content: str):
        """Load RDF to Neptune with retry."""
        try:
            self.kg_manager.bulk_insert_ttl(rdf_content)
            logger.info(f"Loaded RDF to Neptune for {doc_id}")
        except Exception as e:
            logger.warning(f"Neptune load failed, retrying: {e}")
            time.sleep(2)
            try:
                self.kg_manager.bulk_insert_ttl(rdf_content)
                logger.info(f"Loaded RDF to Neptune for {doc_id} (retry successful)")
            except Exception as e2:
                logger.error(f"Neptune load failed after retry: {e2}")
                raise
    
    def print_summary(self):
        """Print processing summary."""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info("=" * 60)
        logger.info("ONTOLOGY ALIGNMENT BATCH JOB SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total solutions: {self.stats['total']}")
        logger.info(f"Processed: {self.stats['processed']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped: {self.stats['skipped']}")
        logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"Average: {duration/self.stats['total']:.1f} seconds per solution")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Ontology Alignment Batch Job')
    
    # Input selection
    parser.add_argument('--limit', type=int, help='Limit number of solutions to process')
    parser.add_argument('--doc-ids', nargs='+', help='Specific doc_ids to process')
    
    # Output modes
    parser.add_argument('--output-dir', type=str, help='Output directory for TTL files')
    parser.add_argument('--load-to-neptune', action='store_true', help='Load RDF to Neptune')
    parser.add_argument('--dry-run', action='store_true', help='Generate RDF but do not write')
    
    # Processing options
    parser.add_argument('--skip-llm', action='store_true', help='Skip LLM extraction (rules only)')
    parser.add_argument('--confidence-threshold', type=float, default=0.0, help='Minimum confidence')
    
    args = parser.parse_args()
    
    # Validation
    if not args.output_dir and not args.load_to_neptune and not args.dry_run:
        parser.error("Must specify at least one of: --output-dir, --load-to-neptune, --dry-run")
    
    # Run batch job
    batch = OntologyAlignmentBatch(args)
    batch.run()


if __name__ == '__main__':
    main()
