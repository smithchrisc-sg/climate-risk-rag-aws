#!/usr/bin/env python3
"""
Comprehend Precision/Recall Evaluator
Tests Amazon Comprehend against ontology-driven ground truth
Focuses on climate risk domain entities and relationships
"""
import boto3
import json
import time
from typing import Dict, List, Any, Set, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ComprehendEvaluator:
    """
    Evaluate Amazon Comprehend precision and recall for climate risk domain
    Uses ontology-driven approach as ground truth baseline
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """Initialize Comprehend client and evaluation framework"""
        self.comprehend = boto3.client('comprehend', region_name=region_name)
        self.region_name = region_name
        
        # Climate risk ontology vocabulary (from your POC experience)
        self.climate_ontology = self._load_climate_ontology()
        
        logger.info(f"Initialized Comprehend evaluator with {len(self.climate_ontology)} ontology terms")
    
    def _load_climate_ontology(self) -> Dict[str, List[str]]:
        """
        Load climate risk ontology vocabulary
        Based on your POC ontology-driven approach
        """
        
        # This would ideally load from your actual ontology files
        # For now, using representative climate risk terms
        return {
            'climate_events': [
                'climate change', 'global warming', 'greenhouse effect',
                'carbon emissions', 'sea level rise', 'ocean acidification',
                'extreme weather', 'heat waves', 'droughts', 'floods',
                'hurricanes', 'cyclones', 'wildfires', 'ice melt',
                'permafrost thaw', 'coral bleaching', 'desertification'
            ],
            'climate_impacts': [
                'biodiversity loss', 'species extinction', 'habitat destruction',
                'food security', 'water scarcity', 'agricultural impacts',
                'economic losses', 'infrastructure damage', 'health impacts',
                'migration', 'displacement', 'social disruption'
            ],
            'climate_solutions': [
                'renewable energy', 'solar power', 'wind energy',
                'carbon capture', 'reforestation', 'afforestation',
                'energy efficiency', 'electric vehicles', 'green technology',
                'carbon pricing', 'emissions trading', 'climate adaptation',
                'mitigation strategies', 'sustainable development'
            ],
            'organizations': [
                'IPCC', 'UNFCCC', 'Paris Agreement', 'Kyoto Protocol',
                'World Bank', 'UN Environment', 'EPA', 'NOAA',
                'NASA', 'climate organizations', 'environmental groups'
            ],
            'locations': [
                'Arctic', 'Antarctica', 'Greenland', 'Amazon',
                'Pacific Islands', 'coastal regions', 'polar regions',
                'tropical regions', 'developing countries'
            ],
            'measurements': [
                'temperature increase', 'CO2 levels', 'ppm', 'degrees Celsius',
                'carbon footprint', 'emissions reduction', 'renewable capacity',
                'energy consumption', 'efficiency gains'
            ]
        }
    
    def evaluate_document(self, text: str, doc_id: str = None) -> Dict[str, Any]:
        """
        Evaluate Comprehend performance on a single document
        
        Args:
            text: Document text to analyze
            doc_id: Optional document identifier
            
        Returns:
            Evaluation results with precision/recall metrics
        """
        
        doc_id = doc_id or f"eval_{int(time.time())}"
        
        logger.info(f"Evaluating document {doc_id} ({len(text)} characters)")
        
        # Step 1: Get Comprehend results
        comprehend_results = self._get_comprehend_results(text)
        
        # Step 2: Get ontology-driven ground truth
        ontology_results = self._get_ontology_ground_truth(text)
        
        # Step 3: Calculate precision and recall
        evaluation_metrics = self._calculate_metrics(comprehend_results, ontology_results)
        
        # Step 4: Analyze entity types
        entity_analysis = self._analyze_entity_types(comprehend_results, ontology_results)
        
        return {
            'doc_id': doc_id,
            'text_length': len(text),
            'evaluated_at': datetime.now().isoformat(),
            'comprehend_results': comprehend_results,
            'ontology_ground_truth': ontology_results,
            'evaluation_metrics': evaluation_metrics,
            'entity_type_analysis': entity_analysis,
            'recommendations': self._generate_recommendations(evaluation_metrics, entity_analysis)
        }
    
    def _get_comprehend_results(self, text: str) -> Dict[str, Any]:
        """Get entity detection results from Amazon Comprehend"""
        
        try:
            # Handle text length limits
            if len(text) > 5000:
                # Process in chunks and combine results
                return self._process_long_text_comprehend(text)
            
            # Single API call for shorter text
            start_time = time.time()
            
            response = self.comprehend.detect_entities(
                Text=text,
                LanguageCode='en'
            )
            
            processing_time = time.time() - start_time
            
            entities = []
            for entity in response['Entities']:
                entities.append({
                    'text': entity['Text'].lower(),  # Normalize for comparison
                    'type': entity['Type'],
                    'confidence': entity['Score'],
                    'begin_offset': entity['BeginOffset'],
                    'end_offset': entity['EndOffset']
                })
            
            return {
                'entities': entities,
                'processing_time': processing_time,
                'api_calls': 1,
                'total_entities': len(entities)
            }
            
        except Exception as e:
            logger.error(f"Error getting Comprehend results: {str(e)}")
            return {
                'entities': [],
                'processing_time': 0,
                'api_calls': 0,
                'total_entities': 0,
                'error': str(e)
            }
    
    def _process_long_text_comprehend(self, text: str) -> Dict[str, Any]:
        """Process long text in chunks for Comprehend"""
        
        chunk_size = 4500
        all_entities = []
        total_processing_time = 0
        api_calls = 0
        
        for i in range(0, len(text), chunk_size):
            chunk = text[i:min(i + chunk_size, len(text))]
            
            try:
                start_time = time.time()
                
                response = self.comprehend.detect_entities(
                    Text=chunk,
                    LanguageCode='en'
                )
                
                processing_time = time.time() - start_time
                total_processing_time += processing_time
                api_calls += 1
                
                # Adjust offsets for global document position
                for entity in response['Entities']:
                    all_entities.append({
                        'text': entity['Text'].lower(),
                        'type': entity['Type'],
                        'confidence': entity['Score'],
                        'begin_offset': entity['BeginOffset'] + i,
                        'end_offset': entity['EndOffset'] + i
                    })
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Error processing chunk at offset {i}: {str(e)}")
                continue
        
        return {
            'entities': all_entities,
            'processing_time': total_processing_time,
            'api_calls': api_calls,
            'total_entities': len(all_entities)
        }
    
    def _get_ontology_ground_truth(self, text: str) -> Dict[str, Any]:
        """
        Get ground truth using ontology-driven approach
        Finds ontology terms in text (your POC approach)
        """
        
        text_lower = text.lower()
        found_entities = []
        
        for category, terms in self.climate_ontology.items():
            for term in terms:
                term_lower = term.lower()
                
                # Find all occurrences of this term
                start_pos = 0
                while True:
                    pos = text_lower.find(term_lower, start_pos)
                    if pos == -1:
                        break
                    
                    found_entities.append({
                        'text': term_lower,
                        'type': category,
                        'confidence': 1.0,  # Ontology matches are definitive
                        'begin_offset': pos,
                        'end_offset': pos + len(term_lower),
                        'source': 'ontology'
                    })
                    
                    start_pos = pos + 1
        
        # Remove duplicates and overlaps
        unique_entities = self._deduplicate_entities(found_entities)
        
        return {
            'entities': unique_entities,
            'total_entities': len(unique_entities),
            'ontology_categories': list(self.climate_ontology.keys()),
            'terms_searched': sum(len(terms) for terms in self.climate_ontology.values())
        }
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Remove duplicate and overlapping entities"""
        
        # Sort by position
        entities.sort(key=lambda x: (x['begin_offset'], x['end_offset']))
        
        unique_entities = []
        
        for entity in entities:
            # Check for overlap with existing entities
            overlaps = False
            for existing in unique_entities:
                if (entity['begin_offset'] < existing['end_offset'] and 
                    entity['end_offset'] > existing['begin_offset']):
                    overlaps = True
                    break
            
            if not overlaps:
                unique_entities.append(entity)
        
        return unique_entities
    
    def _calculate_metrics(self, comprehend_results: Dict, ontology_results: Dict) -> Dict[str, Any]:
        """Calculate precision, recall, and F1 score"""
        
        comprehend_entities = set(entity['text'] for entity in comprehend_results['entities'])
        ontology_entities = set(entity['text'] for entity in ontology_results['entities'])
        
        # True positives: entities found by both
        true_positives = comprehend_entities.intersection(ontology_entities)
        
        # False positives: entities found by Comprehend but not in ontology
        false_positives = comprehend_entities - ontology_entities
        
        # False negatives: entities in ontology but not found by Comprehend
        false_negatives = ontology_entities - comprehend_entities
        
        # Calculate metrics
        precision = len(true_positives) / len(comprehend_entities) if comprehend_entities else 0
        recall = len(true_positives) / len(ontology_entities) if ontology_entities else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'true_positives': len(true_positives),
            'false_positives': len(false_positives),
            'false_negatives': len(false_negatives),
            'true_positive_entities': list(true_positives),
            'false_positive_entities': list(false_positives),
            'false_negative_entities': list(false_negatives)
        }
    
    def _analyze_entity_types(self, comprehend_results: Dict, ontology_results: Dict) -> Dict[str, Any]:
        """Analyze how well Comprehend handles different entity types"""
        
        # Group ontology entities by type
        ontology_by_type = {}
        for entity in ontology_results['entities']:
            entity_type = entity['type']
            if entity_type not in ontology_by_type:
                ontology_by_type[entity_type] = set()
            ontology_by_type[entity_type].add(entity['text'])
        
        # Group Comprehend entities by type
        comprehend_by_type = {}
        for entity in comprehend_results['entities']:
            entity_type = entity['type']
            if entity_type not in comprehend_by_type:
                comprehend_by_type[entity_type] = set()
            comprehend_by_type[entity_type].add(entity['text'])
        
        type_analysis = {}
        
        # Analyze each ontology category
        for ont_type, ont_entities in ontology_by_type.items():
            # Find best matching Comprehend type
            best_match_type = None
            best_overlap = 0
            
            for comp_type, comp_entities in comprehend_by_type.items():
                overlap = len(ont_entities.intersection(comp_entities))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match_type = comp_type
            
            type_analysis[ont_type] = {
                'ontology_entities_count': len(ont_entities),
                'best_comprehend_match': best_match_type,
                'entities_found': best_overlap,
                'type_recall': best_overlap / len(ont_entities) if ont_entities else 0
            }
        
        return type_analysis
    
    def _generate_recommendations(self, metrics: Dict, entity_analysis: Dict) -> List[str]:
        """Generate recommendations based on evaluation results"""
        
        recommendations = []
        
        # Overall performance
        if metrics['precision'] > 0.8:
            recommendations.append("High precision: Comprehend rarely identifies incorrect entities")
        elif metrics['precision'] < 0.5:
            recommendations.append("Low precision: Many false positives, consider filtering")
        
        if metrics['recall'] > 0.8:
            recommendations.append("High recall: Comprehend finds most relevant entities")
        elif metrics['recall'] < 0.5:
            recommendations.append("Low recall: Many climate entities missed, consider supplementing")
        
        if metrics['f1_score'] > 0.7:
            recommendations.append("Good overall performance for climate risk domain")
        elif metrics['f1_score'] < 0.4:
            recommendations.append("Poor overall performance, consider alternative approaches")
        
        # Entity type specific
        for ont_type, analysis in entity_analysis.items():
            if analysis['type_recall'] < 0.3:
                recommendations.append(f"Poor detection of {ont_type} - consider custom rules")
        
        return recommendations
    
    def evaluate_corpus(self, documents: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Evaluate Comprehend on a corpus of documents
        
        Args:
            documents: List of {'text': str, 'doc_id': str} dictionaries
        """
        
        logger.info(f"Evaluating corpus of {len(documents)} documents")
        
        all_results = []
        aggregate_metrics = {
            'total_precision': 0,
            'total_recall': 0,
            'total_f1': 0,
            'total_true_positives': 0,
            'total_false_positives': 0,
            'total_false_negatives': 0
        }
        
        for i, doc in enumerate(documents):
            logger.info(f"Processing document {i+1}/{len(documents)}: {doc.get('doc_id', 'unknown')}")
            
            result = self.evaluate_document(doc['text'], doc.get('doc_id'))
            all_results.append(result)
            
            # Aggregate metrics
            metrics = result['evaluation_metrics']
            aggregate_metrics['total_precision'] += metrics['precision']
            aggregate_metrics['total_recall'] += metrics['recall']
            aggregate_metrics['total_f1'] += metrics['f1_score']
            aggregate_metrics['total_true_positives'] += metrics['true_positives']
            aggregate_metrics['total_false_positives'] += metrics['false_positives']
            aggregate_metrics['total_false_negatives'] += metrics['false_negatives']
            
            # Rate limiting
            time.sleep(0.5)
        
        # Calculate averages
        doc_count = len(documents)
        corpus_metrics = {
            'average_precision': aggregate_metrics['total_precision'] / doc_count,
            'average_recall': aggregate_metrics['total_recall'] / doc_count,
            'average_f1_score': aggregate_metrics['total_f1'] / doc_count,
            'total_true_positives': aggregate_metrics['total_true_positives'],
            'total_false_positives': aggregate_metrics['total_false_positives'],
            'total_false_negatives': aggregate_metrics['total_false_negatives']
        }
        
        return {
            'corpus_size': doc_count,
            'evaluated_at': datetime.now().isoformat(),
            'corpus_metrics': corpus_metrics,
            'individual_results': all_results,
            'summary_recommendations': self._generate_corpus_recommendations(corpus_metrics)
        }
    
    def _generate_corpus_recommendations(self, corpus_metrics: Dict) -> List[str]:
        """Generate recommendations for corpus-level evaluation"""
        
        recommendations = []
        
        avg_precision = corpus_metrics['average_precision']
        avg_recall = corpus_metrics['average_recall']
        avg_f1 = corpus_metrics['average_f1_score']
        
        recommendations.append(f"Corpus Average - Precision: {avg_precision:.2%}, Recall: {avg_recall:.2%}, F1: {avg_f1:.2%}")
        
        if avg_precision > 0.7 and avg_recall > 0.7:
            recommendations.append("✅ Comprehend performs well for climate risk domain")
        elif avg_precision > 0.7:
            recommendations.append("⚠️ High precision but low recall - consider hybrid approach")
        elif avg_recall > 0.7:
            recommendations.append("⚠️ High recall but low precision - consider filtering")
        else:
            recommendations.append("❌ Poor performance - consider alternative NLP approaches")
        
        return recommendations

def main():
    """Example usage of Comprehend evaluator"""
    
    evaluator = ComprehendEvaluator()
    
    # Test document
    test_text = """
    Climate change is causing unprecedented global warming, leading to rising sea levels 
    and extreme weather events. The IPCC reports show that carbon emissions must be 
    reduced by 50% by 2030 to limit temperature increase to 1.5 degrees Celsius. 
    Renewable energy solutions like solar power and wind energy are crucial for 
    mitigation strategies. The Paris Agreement aims to coordinate global climate action.
    """
    
    # Evaluate single document
    result = evaluator.evaluate_document(test_text, "test_doc_001")
    
    print("=== COMPREHEND EVALUATION RESULTS ===")
    print(f"Precision: {result['evaluation_metrics']['precision']:.2%}")
    print(f"Recall: {result['evaluation_metrics']['recall']:.2%}")
    print(f"F1 Score: {result['evaluation_metrics']['f1_score']:.2%}")
    
    print(f"\nTrue Positives: {result['evaluation_metrics']['true_positives']}")
    print(f"False Positives: {result['evaluation_metrics']['false_positives']}")
    print(f"False Negatives: {result['evaluation_metrics']['false_negatives']}")
    
    print("\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  • {rec}")
    
    # Save results
    with open('comprehend_evaluation_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("\nDetailed results saved to: comprehend_evaluation_results.json")

if __name__ == "__main__":
    main()
