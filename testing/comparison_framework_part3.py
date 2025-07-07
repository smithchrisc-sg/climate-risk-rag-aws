"""
Comparison Framework Part 3: Analysis and Metrics Functions
"""

def _compare_text_quality(self, poc_text: str, aws_text: str, doc_id: str) -> Dict[str, Any]:
    """Compare quality of text extraction methods"""
    
    comparison = {
        'doc_id': doc_id,
        'poc_length': len(poc_text),
        'aws_length': len(aws_text),
        'length_ratio': len(aws_text) / len(poc_text) if len(poc_text) > 0 else 0,
        'poc_word_count': len(poc_text.split()),
        'aws_word_count': len(aws_text.split()),
        'common_words': 0,
        'jaccard_similarity': 0.0,
        'quality_score': 0.0
    }
    
    # Calculate word overlap
    poc_words = set(poc_text.lower().split())
    aws_words = set(aws_text.lower().split())
    
    if poc_words and aws_words:
        intersection = poc_words.intersection(aws_words)
        union = poc_words.union(aws_words)
        
        comparison['common_words'] = len(intersection)
        comparison['jaccard_similarity'] = len(intersection) / len(union) if union else 0
    
    # Simple quality score (can be enhanced)
    comparison['quality_score'] = (
        comparison['jaccard_similarity'] * 0.6 +
        min(comparison['length_ratio'], 1.0) * 0.4
    )
    
    return comparison

def _compare_ner_results(self, flair_entities: List[Dict], 
                        comprehend_entities: List[Dict], doc_id: str) -> Dict[str, Any]:
    """Compare NER results between Flair and Comprehend"""
    
    comparison = {
        'doc_id': doc_id,
        'flair_entity_count': len(flair_entities),
        'comprehend_entity_count': len(comprehend_entities),
        'flair_types': {},
        'comprehend_types': {},
        'common_entities': [],
        'precision': 0.0,
        'recall': 0.0,
        'f1_score': 0.0
    }
    
    # Count entity types
    for entity in flair_entities:
        entity_type = entity.get('label', 'UNKNOWN')
        comparison['flair_types'][entity_type] = comparison['flair_types'].get(entity_type, 0) + 1
    
    for entity in comprehend_entities:
        entity_type = entity.get('Type', 'UNKNOWN')
        comparison['comprehend_types'][entity_type] = comparison['comprehend_types'].get(entity_type, 0) + 1
    
    # Find common entities (simplified matching by text)
    flair_texts = {entity.get('text', '').lower() for entity in flair_entities}
    comprehend_texts = {entity.get('Text', '').lower() for entity in comprehend_entities}
    
    common = flair_texts.intersection(comprehend_texts)
    comparison['common_entities'] = list(common)
    
    # Calculate precision, recall, F1
    if comprehend_entities:
        comparison['precision'] = len(common) / len(comprehend_entities)
    if flair_entities:
        comparison['recall'] = len(common) / len(flair_entities)
    
    if comparison['precision'] + comparison['recall'] > 0:
        comparison['f1_score'] = 2 * (comparison['precision'] * comparison['recall']) / (comparison['precision'] + comparison['recall'])
    
    return comparison

def _compare_embedding_quality(self, poc_embeddings: List[Dict], 
                              titan_embeddings: List[List[float]], 
                              text_chunks: List[str], doc_id: str) -> Dict[str, Any]:
    """Compare embedding quality between POC and Titan"""
    
    comparison = {
        'doc_id': doc_id,
        'poc_embedding_count': len(poc_embeddings),
        'titan_embedding_count': len(titan_embeddings),
        'dimension_comparison': {},
        'similarity_analysis': {},
        'quality_metrics': {}
    }
    
    if poc_embeddings and titan_embeddings:
        # Extract POC embedding vectors (assuming they're stored in the data)
        poc_vectors = []
        for emb in poc_embeddings[:len(titan_embeddings)]:  # Match counts
            if 'embedding' in emb:
                poc_vectors.append(emb['embedding'])
        
        if poc_vectors:
            # Dimension comparison
            poc_dim = len(poc_vectors[0]) if poc_vectors else 0
            titan_dim = len(titan_embeddings[0]) if titan_embeddings else 0
            
            comparison['dimension_comparison'] = {
                'poc_dimensions': poc_dim,
                'titan_dimensions': titan_dim,
                'dimension_ratio': titan_dim / poc_dim if poc_dim > 0 else 0
            }
            
            # Similarity analysis (if dimensions match or can be compared)
            if poc_dim == titan_dim and len(poc_vectors) == len(titan_embeddings):
                similarities = []
                for poc_vec, titan_vec in zip(poc_vectors, titan_embeddings):
                    sim = cosine_similarity([poc_vec], [titan_vec])[0][0]
                    similarities.append(sim)
                
                comparison['similarity_analysis'] = {
                    'mean_similarity': np.mean(similarities),
                    'std_similarity': np.std(similarities),
                    'min_similarity': np.min(similarities),
                    'max_similarity': np.max(similarities)
                }
    
    return comparison

def _compare_chunking_quality(self, poc_chunks: List[Dict], 
                             aws_chunks: List[Dict], doc_id: str) -> Dict[str, Any]:
    """Compare chunking approaches"""
    
    comparison = {
        'doc_id': doc_id,
        'poc_chunk_count': len(poc_chunks),
        'aws_chunk_count': len(aws_chunks),
        'poc_avg_length': 0,
        'aws_avg_length': 0,
        'poc_length_variance': 0,
        'aws_length_variance': 0,
        'content_overlap': 0.0,
        'boundary_quality': {}
    }
    
    # Calculate chunk statistics
    if poc_chunks:
        poc_lengths = [len(chunk.get('text', '')) for chunk in poc_chunks]
        comparison['poc_avg_length'] = np.mean(poc_lengths)
        comparison['poc_length_variance'] = np.var(poc_lengths)
    
    if aws_chunks:
        aws_lengths = [len(chunk.get('text', '')) for chunk in aws_chunks]
        comparison['aws_avg_length'] = np.mean(aws_lengths)
        comparison['aws_length_variance'] = np.var(aws_lengths)
    
    # Content overlap analysis
    if poc_chunks and aws_chunks:
        poc_text = ' '.join([chunk.get('text', '') for chunk in poc_chunks])
        aws_text = ' '.join([chunk.get('text', '') for chunk in aws_chunks])
        
        poc_words = set(poc_text.lower().split())
        aws_words = set(aws_text.lower().split())
        
        if poc_words and aws_words:
            intersection = poc_words.intersection(aws_words)
            union = poc_words.union(aws_words)
            comparison['content_overlap'] = len(intersection) / len(union)
    
    return comparison

def _calculate_text_metrics(self, comparisons: List[Dict]) -> Dict[str, Any]:
    """Calculate aggregate text extraction metrics"""
    
    if not comparisons:
        return {}
    
    metrics = {
        'avg_length_ratio': np.mean([c['length_ratio'] for c in comparisons]),
        'avg_jaccard_similarity': np.mean([c['jaccard_similarity'] for c in comparisons]),
        'avg_quality_score': np.mean([c['quality_score'] for c in comparisons]),
        'consistency': np.std([c['quality_score'] for c in comparisons]),
        'sample_size': len(comparisons)
    }
    
    # Determine winner
    if metrics['avg_quality_score'] > 0.7:
        metrics['recommendation'] = "Both methods perform well, AWS Textract recommended for consistency"
    elif metrics['avg_quality_score'] > 0.5:
        metrics['recommendation'] = "Moderate similarity, consider hybrid approach"
    else:
        metrics['recommendation'] = "Significant differences, manual review recommended"
    
    return metrics

def _calculate_ner_metrics(self, comparisons: List[Dict]) -> Dict[str, Any]:
    """Calculate aggregate NER metrics"""
    
    if not comparisons:
        return {}
    
    metrics = {
        'avg_precision': np.mean([c['precision'] for c in comparisons]),
        'avg_recall': np.mean([c['recall'] for c in comparisons]),
        'avg_f1_score': np.mean([c['f1_score'] for c in comparisons]),
        'entity_count_ratio': np.mean([
            c['comprehend_entity_count'] / c['flair_entity_count'] 
            if c['flair_entity_count'] > 0 else 0 
            for c in comparisons
        ]),
        'sample_size': len(comparisons)
    }
    
    # Determine winner
    if metrics['avg_f1_score'] > 0.7:
        metrics['recommendation'] = "High agreement between methods"
    elif metrics['avg_f1_score'] > 0.5:
        metrics['recommendation'] = "Moderate agreement, consider ensemble approach"
    else:
        metrics['recommendation'] = "Low agreement, domain-specific tuning needed"
    
    return metrics

def _generate_recommendations(self) -> List[str]:
    """Generate recommendations based on comparison results"""
    
    recommendations = []
    
    # Text extraction recommendations
    if 'text_extraction' in self.comparison_results:
        text_metrics = self.comparison_results['text_extraction'].get('metrics', {})
        if text_metrics.get('avg_quality_score', 0) > 0.8:
            recommendations.append("AWS Textract shows high similarity to POC extraction - recommended for production")
        else:
            recommendations.append("Consider hybrid text extraction approach combining both methods")
    
    # NER recommendations
    if 'ner_comparison' in self.comparison_results:
        ner_metrics = self.comparison_results['ner_comparison'].get('metrics', {})
        if ner_metrics.get('avg_f1_score', 0) > 0.7:
            recommendations.append("AWS Comprehend performs well compared to Flair - cost-effective option")
        else:
            recommendations.append("Flair NER shows superior performance - consider keeping for specialized entities")
    
    # Embedding recommendations
    if 'embedding_comparison' in self.comparison_results:
        recommendations.append("Compare embedding performance on downstream tasks before deciding")
        recommendations.append("Consider cost vs performance trade-offs for embedding generation")
    
    # Chunking recommendations
    if 'chunking_comparison' in self.comparison_results:
        recommendations.append("AWS structured chunking preserves document hierarchy better")
        recommendations.append("POC sentence-based chunking may be better for semantic coherence")
    
    # General recommendations
    recommendations.extend([
        "Implement A/B testing for production deployment",
        "Monitor performance metrics continuously",
        "Consider hybrid approaches for optimal results",
        "Evaluate cost implications of each approach"
    ])
    
    return recommendations
