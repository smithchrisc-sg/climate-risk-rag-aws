"""
Comparison Framework Part 2: Helper Methods and Analysis Functions
"""

def _compare_embeddings(self, sample_docs: List[Dict], artifacts_bucket: str) -> Dict[str, Any]:
    """Compare POC embeddings vs AWS Titan embeddings"""
    
    comparison_results = {
        'method': 'embedding_comparison',
        'sample_size': len(sample_docs),
        'comparisons': [],
        'metrics': {}
    }
    
    # Process sample of documents
    sample_subset = sample_docs[:15]  # Limit for detailed comparison
    
    for doc in tqdm(sample_subset, desc="Comparing embeddings"):
        try:
            doc_id = doc['doc_id']
            
            # Get POC embeddings
            poc_embeddings = self._get_poc_embeddings(doc_id, artifacts_bucket)
            
            # Get corresponding text chunks
            text_chunks = self._get_sample_chunks_text(doc_id, artifacts_bucket)
            
            if poc_embeddings and text_chunks:
                # Generate AWS Titan embeddings
                titan_embeddings = self._generate_titan_embeddings(text_chunks)
                
                # Compare embeddings
                comparison = self._compare_embedding_quality(
                    poc_embeddings, titan_embeddings, text_chunks, doc_id
                )
                comparison_results['comparisons'].append(comparison)
                
        except Exception as e:
            logger.error(f"Error comparing embeddings for {doc['doc_id']}: {str(e)}")
    
    # Calculate aggregate metrics
    if comparison_results['comparisons']:
        comparison_results['metrics'] = self._calculate_embedding_metrics(
            comparison_results['comparisons']
        )
    
    return comparison_results

def _compare_chunking_methods(self, sample_docs: List[Dict], artifacts_bucket: str) -> Dict[str, Any]:
    """Compare POC 5-sentence chunking vs AWS structured chunking"""
    
    comparison_results = {
        'method': 'chunking_comparison',
        'sample_size': len(sample_docs),
        'comparisons': [],
        'metrics': {}
    }
    
    # Process sample of documents that have sample chunks
    for doc in tqdm(sample_docs[:10], desc="Comparing chunking methods"):
        try:
            doc_id = doc['doc_id']
            
            # Get POC chunks (from sample)
            poc_chunks = self._get_sample_chunks(doc_id, artifacts_bucket)
            
            # Get original text
            text = self._get_poc_extracted_text(doc_id, artifacts_bucket)
            
            if poc_chunks and text:
                # Generate AWS structured chunks (simulate)
                aws_chunks = self._generate_structured_chunks(text)
                
                # Compare chunking approaches
                comparison = self._compare_chunking_quality(
                    poc_chunks, aws_chunks, doc_id
                )
                comparison_results['comparisons'].append(comparison)
                
        except Exception as e:
            logger.error(f"Error comparing chunking for {doc['doc_id']}: {str(e)}")
    
    # Calculate aggregate metrics
    if comparison_results['comparisons']:
        comparison_results['metrics'] = self._calculate_chunking_metrics(
            comparison_results['comparisons']
        )
    
    return comparison_results

def _compare_rag_performance(self, sample_docs: List[Dict], 
                           documents_bucket: str, artifacts_bucket: str) -> Dict[str, Any]:
    """Compare end-to-end RAG performance"""
    
    comparison_results = {
        'method': 'rag_performance_comparison',
        'sample_size': len(sample_docs),
        'test_queries': [],
        'performance_metrics': {}
    }
    
    # Define test queries for climate risk domain
    test_queries = [
        "What are the main physical climate risks?",
        "How do carbon emissions affect climate change?",
        "What adaptation strategies exist for sea level rise?",
        "How can businesses assess climate risk?",
        "What are the financial implications of climate change?",
        "How does temperature rise affect agriculture?",
        "What are the key climate risk indicators?",
        "How do extreme weather events impact infrastructure?",
        "What are the main climate mitigation strategies?",
        "How does climate change affect water resources?"
    ]
    
    for query in tqdm(test_queries, desc="Testing RAG performance"):
        try:
            # Test POC-based RAG (simulated)
            poc_response = self._simulate_poc_rag_response(query, artifacts_bucket)
            
            # Test AWS-based RAG (simulated)
            aws_response = self._simulate_aws_rag_response(query, documents_bucket, artifacts_bucket)
            
            # Compare responses
            comparison = self._compare_rag_responses(query, poc_response, aws_response)
            comparison_results['test_queries'].append(comparison)
            
        except Exception as e:
            logger.error(f"Error testing RAG for query '{query}': {str(e)}")
    
    # Calculate performance metrics
    if comparison_results['test_queries']:
        comparison_results['performance_metrics'] = self._calculate_rag_metrics(
            comparison_results['test_queries']
        )
    
    return comparison_results

# Helper methods for data retrieval

def _get_poc_extracted_text(self, doc_id: str, bucket: str) -> Optional[str]:
    """Get POC extracted text for a document"""
    try:
        key = f"processed_text/{doc_id}.txt"
        response = self.s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.debug(f"Could not get POC text for {doc_id}: {str(e)}")
        return None

def _get_textract_text(self, document_key: str, bucket: str) -> Optional[str]:
    """Get text using AWS Textract"""
    try:
        # For this comparison, we'll simulate Textract results
        # In production, you'd call Textract API
        response = self.textract.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': document_key
                }
            }
        )
        
        text = ""
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text += block['Text'] + '\n'
        
        return text
    except Exception as e:
        logger.debug(f"Could not get Textract text for {document_key}: {str(e)}")
        return None

def _get_flair_ner_results(self, doc_id: str, bucket: str) -> Optional[List[Dict]]:
    """Get Flair NER results for a document"""
    try:
        key = f"processed_ner_flair/{doc_id}_Flair.json"
        response = self.s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response['Body'].read())
    except Exception as e:
        logger.debug(f"Could not get Flair NER for {doc_id}: {str(e)}")
        return None

def _get_comprehend_entities(self, text: str) -> List[Dict]:
    """Get entities using AWS Comprehend"""
    try:
        # Limit text size for Comprehend
        if len(text) > 5000:
            text = text[:5000]
        
        response = self.comprehend.detect_entities(
            Text=text,
            LanguageCode='en'
        )
        
        return response.get('Entities', [])
    except Exception as e:
        logger.debug(f"Could not get Comprehend entities: {str(e)}")
        return []

def _get_poc_embeddings(self, doc_id: str, bucket: str) -> Optional[List[Dict]]:
    """Get POC embeddings for a document"""
    try:
        # List all embedding files for this document
        paginator = self.s3.get_paginator('list_objects_v2')
        embeddings = []
        
        for page in paginator.paginate(Bucket=bucket, Prefix=f"processed_embeddings/{doc_id}/"):
            for obj in page.get('Contents', []):
                if obj['Key'].endswith('.json'):
                    response = self.s3.get_object(Bucket=bucket, Key=obj['Key'])
                    embedding_data = json.loads(response['Body'].read())
                    embeddings.append(embedding_data)
        
        return embeddings if embeddings else None
    except Exception as e:
        logger.debug(f"Could not get POC embeddings for {doc_id}: {str(e)}")
        return None

def _get_sample_chunks_text(self, doc_id: str, bucket: str) -> Optional[List[str]]:
    """Get sample chunks text for a document"""
    try:
        # List all chunk files for this document
        paginator = self.s3.get_paginator('list_objects_v2')
        chunks = []
        
        for page in paginator.paginate(Bucket=bucket, Prefix=f"sample_chunks/{doc_id}/"):
            for obj in page.get('Contents', []):
                if obj['Key'].endswith('.json'):
                    response = self.s3.get_object(Bucket=bucket, Key=obj['Key'])
                    chunk_data = json.loads(response['Body'].read())
                    if 'text' in chunk_data:
                        chunks.append(chunk_data['text'])
        
        return chunks if chunks else None
    except Exception as e:
        logger.debug(f"Could not get sample chunks for {doc_id}: {str(e)}")
        return None

def _generate_titan_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
    """Generate embeddings using AWS Titan"""
    embeddings = []
    
    for chunk in text_chunks[:10]:  # Limit for comparison
        try:
            body = json.dumps({"inputText": chunk})
            
            response = self.bedrock.invoke_model(
                modelId='amazon.titan-embed-text-v1',
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            embeddings.append(response_body['embedding'])
            
        except Exception as e:
            logger.debug(f"Error generating Titan embedding: {str(e)}")
            continue
    
    return embeddings
