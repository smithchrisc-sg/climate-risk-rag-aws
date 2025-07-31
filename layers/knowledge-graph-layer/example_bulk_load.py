#!/usr/bin/env python3
"""
Example usage of Knowledge Graph Layer with Bulk Load functionality
Demonstrates both SPARQL INSERT and Neptune bulk load capabilities
"""
import os
import sys

# Add the layer to Python path (for testing)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def example_usage():
    """Example usage of KG layer with bulk load"""
    
    # Note: This example shows the API usage but won't run without proper AWS credentials
    # and Neptune endpoint configuration
    
    print("Knowledge Graph Layer Bulk Load Example")
    print("=" * 50)
    
    # Example TTL content - small dataset
    small_ttl = """
    @prefix kcc: <http://solve.global/knowledge-commons/> .
    @prefix dcterms: <http://purl.org/dc/terms/> .
    
    kcc:doc123 a dcterms:Document ;
        dcterms:title "Small Climate Report" ;
        dcterms:creator "Author Name" .
    
    kcc:chunk123 a kcc:DocumentChunk ;
        dcterms:isPartOf kcc:doc123 ;
        kcc:mentionsConcept <http://ontology.org/climate/ClimateChange> .
    """
    
    # Example TTL content - large dataset (simulated)
    large_ttl_base = """
    @prefix kcc: <http://solve.global/knowledge-commons/> .
    @prefix dcterms: <http://purl.org/dc/terms/> .
    
    """
    
    # Generate large TTL content (>1000 triples to trigger bulk load)
    large_ttl_triples = []
    for i in range(1200):  # Generate 1200 triples
        large_ttl_triples.append(f"kcc:doc{i} a dcterms:Document ;")
        large_ttl_triples.append(f'    dcterms:title "Document {i}" ;')
        large_ttl_triples.append(f'    dcterms:creator "Author {i}" .')
    
    large_ttl = large_ttl_base + "\n".join(large_ttl_triples)
    
    print("Example API Usage:")
    print("-" * 30)
    
    print("""
# Initialize KG Manager
from utils.KnowledgeGraphManager import KnowledgeGraphManager

kg_manager = KnowledgeGraphManager()

# Small dataset - will use SPARQL INSERT
small_result = kg_manager.triple_manager.insert_triples_optimized(small_ttl)
print(f"Small dataset: {small_result['method']} - {small_result['success']}")

# Large dataset - will use Neptune bulk load
large_result = kg_manager.triple_manager.insert_triples_optimized(large_ttl)
print(f"Large dataset: {large_result['method']} - {large_result['records_loaded']} records")

# Manual bulk load from existing S3 file
load_result = kg_manager.bulk_load_from_s3(
    s3_uri="s3://my-bucket/large-dataset.ttl",
    format='turtle',
    wait=True
)

# Asynchronous bulk load
load_id = kg_manager.bulk_load_from_s3(
    s3_uri="s3://my-bucket/huge-dataset.ttl", 
    wait=False
)

# Monitor load progress
status = kg_manager.get_bulk_load_status(load_id)
print(f"Load status: {status['status']}")

# List recent loads
recent_loads = kg_manager.list_recent_bulk_loads(limit=5)
for load in recent_loads:
    print(f"Load {load['load_id']}: {load['status']} - {load['total_records']} records")
""")
    
    print("\nBulk Load Decision Logic:")
    print("-" * 30)
    
    # Demonstrate the decision logic
    try:
        from utils.BulkLoadManager import BulkLoadManager
        
        # Create a mock manager for demonstration
        class MockKGManager:
            def __init__(self):
                self.neptune_endpoint = "test-endpoint"
                self.neptune_port = "8182"
                self.aws_region = "us-east-1"
        
        mock_kg = MockKGManager()
        bulk_manager = BulkLoadManager(mock_kg)
        
        # Test decision logic
        small_count = bulk_manager.estimate_triple_count(small_ttl)
        large_count = bulk_manager.estimate_triple_count(large_ttl)
        
        print(f"Small TTL estimated triples: {small_count}")
        print(f"Should use bulk load: {bulk_manager.should_use_bulk_load(small_ttl)}")
        print()
        print(f"Large TTL estimated triples: {large_count}")
        print(f"Should use bulk load: {bulk_manager.should_use_bulk_load(large_ttl)}")
        print(f"Bulk load threshold: {bulk_manager.BULK_LOAD_THRESHOLD}")
        
    except ImportError as e:
        print(f"Could not demonstrate decision logic: {e}")
    
    print("\nEnvironment Variables Required:")
    print("-" * 30)
    print("""
NEPTUNE_ENDPOINT=your-neptune-cluster-endpoint
NEPTUNE_PORT=8182
AWS_REGION=us-east-1
NEPTUNE_TIMEOUT=30
NEPTUNE_MAX_RETRIES=3
TTL_BUCKET=your-s3-bucket-for-bulk-load-files
""")

if __name__ == "__main__":
    example_usage()
