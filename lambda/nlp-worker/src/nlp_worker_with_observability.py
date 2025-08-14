#!/usr/bin/env python3
"""
Observability wrapper for NLP Worker
This adds comprehensive metrics tracking without modifying the core nlp_worker.py
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
from nlp_worker import NLPWorker

logger = logging.getLogger()

class NLPWorkerWithObservability(NLPWorker):
    """
    Enhanced NLP Worker with comprehensive observability metrics
    Inherits from the original NLPWorker without modifying it
    """
    
    def map_results_to_chunks(self, comprehend_results: Dict[str, List], chunks: List[Dict], doc_id: str) -> Dict[str, List]:
        """
        Enhanced version of map_results_to_chunks with observability
        Calls the original method and adds comprehensive metrics tracking
        """
        
        # Call the original method
        original_results = super().map_results_to_chunks(comprehend_results, chunks, doc_id)
        
        # Add observability metrics
        try:
            # Generate comprehensive metrics
            metrics = self.generate_mapping_metrics(
                doc_id=doc_id,
                chunks=chunks,
                comprehend_results=comprehend_results,
                original_results=original_results
            )
            
            # Log metrics for observability
            self.log_mapping_metrics(metrics)
            
            # Store metrics in database for analysis
            self.store_mapping_metrics(metrics)
            
            # Add metrics to the response
            enhanced_results = original_results.copy()
            enhanced_results['mapping_metrics'] = metrics
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Failed to generate observability metrics: {e}")
            # Return original results if metrics fail - don't break processing
            return original_results
    
    def generate_mapping_metrics(self, doc_id: str, chunks: List[Dict], 
                               comprehend_results: Dict[str, List], 
                               original_results: Dict[str, List]) -> Dict[str, Any]:
        """Generate comprehensive mapping metrics for semantic search optimization"""
        
        entities = comprehend_results.get('entities', [])
        keyphrases = comprehend_results.get('key_phrases', [])
        entities_mapped = original_results.get('entities_by_chunk', [])
        keyphrases_mapped = original_results.get('key_phrases_by_chunk', [])
        
        # Calculate basic metrics
        total_entities = len(entities)
        total_keyphrases = len(keyphrases)
        entities_mapped_count = len(entities_mapped)
        keyphrases_mapped_count = len(keyphrases_mapped)
        
        # Calculate success rates
        entity_success_rate = (entities_mapped_count / total_entities * 100) if total_entities > 0 else 0
        keyphrase_success_rate = (keyphrases_mapped_count / total_keyphrases * 100) if total_keyphrases > 0 else 0
        
        # Analyze unmapped entities
        mapped_entity_texts = set(e.get('entity', '') for e in entities_mapped)
        entities_unmapped = [e for e in entities if e.get('text', '') not in mapped_entity_texts]
        
        mapped_keyphrase_texts = set(k.get('phrase', '') for k in keyphrases_mapped)
        keyphrases_unmapped = [k for k in keyphrases if k.get('text', '') not in mapped_keyphrase_texts]
        
        # Chunk coverage metrics
        chunks_with_entities = len(set(e.get('chunk_id', '') for e in entities_mapped))
        chunks_with_keyphrases = len(set(k.get('chunk_id', '') for k in keyphrases_mapped))
        total_chunks = len(chunks)
        
        # Entity type analysis for search impact
        entity_type_analysis = self.analyze_entity_types(entities_mapped, entities_unmapped)
        
        # Search quality impact estimation
        search_quality_impact = self.estimate_search_quality_impact(
            entities_mapped, keyphrases_mapped, entity_type_analysis
        )
        
        # Estimate chunk finding success (approximate)
        chunk_finding_success_rate = self.estimate_chunk_finding_rate(chunks, entities_mapped, keyphrases_mapped)
        
        metrics = {
            # Document identification
            'doc_id': doc_id,
            'timestamp': datetime.utcnow().isoformat(),
            'processing_stage': 'nlp_entity_mapping',
            
            # Basic counts
            'total_entities': total_entities,
            'total_keyphrases': total_keyphrases,
            'total_chunks': total_chunks,
            
            # Mapping success metrics
            'entities_mapped': entities_mapped_count,
            'entities_unmapped': len(entities_unmapped),
            'keyphrases_mapped': keyphrases_mapped_count,
            'keyphrases_unmapped': len(keyphrases_unmapped),
            
            # Success rates (key metrics for monitoring)
            'entity_mapping_success_rate': round(entity_success_rate, 2),
            'keyphrase_mapping_success_rate': round(keyphrase_success_rate, 2),
            'chunk_finding_success_rate': round(chunk_finding_success_rate, 2),
            
            # Chunk coverage for search system
            'chunks_with_entities': chunks_with_entities,
            'chunks_with_keyphrases': chunks_with_keyphrases,
            'chunk_entity_coverage_rate': round((chunks_with_entities / total_chunks * 100) if total_chunks > 0 else 0, 2),
            'chunk_keyphrase_coverage_rate': round((chunks_with_keyphrases / total_chunks * 100) if total_chunks > 0 else 0, 2),
            
            # Entity type analysis (critical for search quality)
            'entity_types_mapped': entity_type_analysis['mapped_by_type'],
            'entity_types_unmapped': entity_type_analysis['unmapped_by_type'],
            'critical_entities_mapped': entity_type_analysis['critical_mapped'],
            'critical_entities_unmapped': entity_type_analysis['critical_unmapped'],
            'critical_entity_success_rate': entity_type_analysis['critical_success_rate'],
            
            # Search system impact estimation
            'estimated_search_quality_impact': round(search_quality_impact, 3),
            'search_impact_breakdown': self.calculate_search_impact_breakdown(entities_mapped, keyphrases_mapped),
            
            # Unmapped entity analysis (samples for debugging)
            'unmapped_entity_sample': entities_unmapped[:5],
            'unmapped_keyphrase_sample': keyphrases_unmapped[:5],
            
            # Performance metrics
            'avg_entities_per_chunk': round(entities_mapped_count / chunks_with_entities if chunks_with_entities > 0 else 0, 2),
            'avg_keyphrases_per_chunk': round(keyphrases_mapped_count / chunks_with_keyphrases if chunks_with_keyphrases > 0 else 0, 2)
        }
        
        return metrics
    
    def estimate_chunk_finding_rate(self, chunks: List[Dict], entities_mapped: List[Dict], keyphrases_mapped: List[Dict]) -> float:
        """Estimate chunk finding success rate based on mapping results"""
        
        # Get unique chunk IDs that have mappings
        mapped_chunk_ids = set()
        mapped_chunk_ids.update(e.get('chunk_id', '') for e in entities_mapped)
        mapped_chunk_ids.update(k.get('chunk_id', '') for k in keyphrases_mapped)
        mapped_chunk_ids.discard('')  # Remove empty strings
        
        total_chunks = len(chunks)
        chunks_found = len(mapped_chunk_ids)
        
        return (chunks_found / total_chunks * 100) if total_chunks > 0 else 0
    
    def analyze_entity_types(self, entities_mapped: List[Dict], entities_unmapped: List[Dict]) -> Dict[str, Any]:
        """Analyze entity types for search system impact assessment"""
        
        # Define critical entity types for search system
        critical_types = ['LOCATION', 'ORGANIZATION', 'PERSON']
        
        # Count mapped entities by type
        mapped_by_type = {}
        critical_mapped = 0
        
        for entity in entities_mapped:
            entity_type = entity.get('type', 'UNKNOWN')
            mapped_by_type[entity_type] = mapped_by_type.get(entity_type, 0) + 1
            if entity_type in critical_types:
                critical_mapped += 1
        
        # Count unmapped entities by type
        unmapped_by_type = {}
        critical_unmapped = 0
        
        for entity in entities_unmapped:
            entity_type = entity.get('Type', entity.get('type', 'UNKNOWN'))  # Handle both formats
            unmapped_by_type[entity_type] = unmapped_by_type.get(entity_type, 0) + 1
            if entity_type in critical_types:
                critical_unmapped += 1
        
        # Calculate critical entity success rate
        total_critical = critical_mapped + critical_unmapped
        critical_success_rate = (critical_mapped / total_critical * 100) if total_critical > 0 else 0
        
        return {
            'mapped_by_type': mapped_by_type,
            'unmapped_by_type': unmapped_by_type,
            'critical_mapped': critical_mapped,
            'critical_unmapped': critical_unmapped,
            'critical_success_rate': round(critical_success_rate, 2)
        }
    
    def estimate_search_quality_impact(self, entities_mapped: List[Dict], keyphrases_mapped: List[Dict], 
                                     entity_type_analysis: Dict[str, Any]) -> float:
        """Estimate the impact on search quality based on mapped entities and keyphrases"""
        
        impact_score = 0.0
        
        # Entity impact scoring
        for entity in entities_mapped:
            entity_type = entity.get('type', '')
            entity_score = entity.get('score', 0)
            
            # Weight by entity type importance for search
            if entity_type in ['LOCATION', 'ORGANIZATION']:
                type_weight = 1.0  # Highest impact
            elif entity_type == 'PERSON':
                type_weight = 0.8  # High impact
            elif entity_type in ['DATE', 'QUANTITY', 'TITLE']:
                type_weight = 0.6  # Medium impact
            else:
                type_weight = 0.4  # Lower impact
            
            # Combine Comprehend confidence with type importance
            entity_impact = entity_score * type_weight
            impact_score += entity_impact
        
        # Keyphrase impact scoring (generally lower weight than entities)
        for keyphrase in keyphrases_mapped:
            keyphrase_score = keyphrase.get('score', 0)
            keyphrase_impact = keyphrase_score * 0.5  # Keyphrases have moderate impact
            impact_score += keyphrase_impact
        
        return impact_score
    
    def calculate_search_impact_breakdown(self, entities_mapped: List[Dict], keyphrases_mapped: List[Dict]) -> Dict[str, float]:
        """Calculate detailed breakdown of search impact by category"""
        
        breakdown = {
            'location_impact': 0.0,
            'organization_impact': 0.0,
            'person_impact': 0.0,
            'temporal_impact': 0.0,  # Dates, quantities
            'keyphrase_impact': 0.0,
            'other_impact': 0.0
        }
        
        for entity in entities_mapped:
            entity_type = entity.get('type', '')
            entity_score = entity.get('score', 0)
            
            if entity_type == 'LOCATION':
                breakdown['location_impact'] += entity_score
            elif entity_type == 'ORGANIZATION':
                breakdown['organization_impact'] += entity_score
            elif entity_type == 'PERSON':
                breakdown['person_impact'] += entity_score
            elif entity_type in ['DATE', 'QUANTITY']:
                breakdown['temporal_impact'] += entity_score
            else:
                breakdown['other_impact'] += entity_score
        
        for keyphrase in keyphrases_mapped:
            keyphrase_score = keyphrase.get('score', 0)
            breakdown['keyphrase_impact'] += keyphrase_score * 0.5
        
        # Round all values
        return {k: round(v, 3) for k, v in breakdown.items()}
    
    def log_mapping_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log mapping metrics for CloudWatch observability"""
        
        doc_id = metrics.get('doc_id', 'unknown')
        
        # Log key metrics as structured log entries for CloudWatch
        logger.info(f"ENTITY_MAPPING_METRICS doc_id={doc_id} "
                   f"entity_success_rate={metrics.get('entity_mapping_success_rate', 0)} "
                   f"keyphrase_success_rate={metrics.get('keyphrase_mapping_success_rate', 0)} "
                   f"chunk_success_rate={metrics.get('chunk_finding_success_rate', 0)} "
                   f"search_impact={metrics.get('estimated_search_quality_impact', 0)}")
        
        # Log critical entity metrics (most important for search quality)
        logger.info(f"CRITICAL_ENTITY_METRICS doc_id={doc_id} "
                   f"critical_mapped={metrics.get('critical_entities_mapped', 0)} "
                   f"critical_unmapped={metrics.get('critical_entities_unmapped', 0)} "
                   f"critical_success_rate={metrics.get('critical_entity_success_rate', 0)}")
        
        # Log chunk coverage metrics
        logger.info(f"CHUNK_COVERAGE_METRICS doc_id={doc_id} "
                   f"chunks_with_entities={metrics.get('chunks_with_entities', 0)} "
                   f"total_chunks={metrics.get('total_chunks', 0)} "
                   f"coverage_rate={metrics.get('chunk_entity_coverage_rate', 0)}")
        
        # Log search impact breakdown for detailed analysis
        impact_breakdown = metrics.get('search_impact_breakdown', {})
        logger.info(f"SEARCH_IMPACT_BREAKDOWN doc_id={doc_id} "
                   f"location={impact_breakdown.get('location_impact', 0)} "
                   f"organization={impact_breakdown.get('organization_impact', 0)} "
                   f"person={impact_breakdown.get('person_impact', 0)} "
                   f"keyphrase={impact_breakdown.get('keyphrase_impact', 0)}")
    
    def store_mapping_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store mapping metrics in database for analysis and monitoring"""
        
        try:
            # Store key metrics in document_processing_status table
            self.update_status(
                doc_id=metrics['doc_id'],
                stage='nlp_entity_mapping_metrics',
                status='completed',
                metadata={
                    'entity_mapping_success_rate': metrics.get('entity_mapping_success_rate'),
                    'keyphrase_mapping_success_rate': metrics.get('keyphrase_mapping_success_rate'),
                    'chunk_finding_success_rate': metrics.get('chunk_finding_success_rate'),
                    'estimated_search_quality_impact': metrics.get('estimated_search_quality_impact'),
                    'critical_entity_success_rate': metrics.get('critical_entity_success_rate'),
                    'chunks_with_entities': metrics.get('chunks_with_entities'),
                    'total_chunks': metrics.get('total_chunks'),
                    'entity_types_mapped': metrics.get('entity_types_mapped'),
                    'search_impact_breakdown': metrics.get('search_impact_breakdown')
                }
            )
                
        except Exception as e:
            logger.error(f"Failed to store mapping metrics: {e}")
            # Don't raise exception - metrics storage failure shouldn't break processing
