#!/usr/bin/env python3
"""
Local Setup Test
Tests basic functionality that should work locally before EC2 deployment.
"""

import logging
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsers.csv_parser import CSVParser
from generators.pseudo_document_generator import PseudoDocumentGenerator
from generators.chunk_generator import ChunkGenerator
from utils.data_lake_writer import DataLakeWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_csv_parsing():
    """Test CSV parsing functionality."""
    
    print("CSV Parsing Test")
    print("=" * 20)
    
    try:
        parser = CSVParser()
        solutions = list(parser.parse_all_files())
        
        print(f"✅ Parsed {len(solutions)} solutions")
        
        if solutions:
            sample = solutions[0]
            print(f"Sample solution: {sample.name[:50]}...")
            print(f"Doc ID: {sample.doc_id}")
            print(f"Source URL: {sample.source_url}")
            return True
        else:
            print("❌ No solutions parsed")
            return False
            
    except Exception as e:
        print(f"❌ CSV parsing failed: {e}")
        return False

def test_pseudo_document_generation():
    """Test pseudo-document generation."""
    
    print("\nPseudo-Document Generation Test")
    print("=" * 35)
    
    try:
        parser = CSVParser()
        solutions = list(parser.parse_all_files())[:2]
        
        generator = PseudoDocumentGenerator()
        processed = generator.process_solutions(solutions)
        
        print(f"✅ Generated pseudo-documents for {len(processed)} solutions")
        
        if processed:
            sample = processed[0]
            if hasattr(sample, 'pseudo_document_text'):
                print(f"Sample length: {len(sample.pseudo_document_text)} chars")
                return True
            else:
                print("❌ No pseudo_document_text generated")
                return False
        else:
            return False
            
    except Exception as e:
        print(f"❌ Pseudo-document generation failed: {e}")
        return False

def test_chunk_generation():
    """Test chunk generation."""
    
    print("\nChunk Generation Test")
    print("=" * 25)
    
    try:
        parser = CSVParser()
        solutions = list(parser.parse_all_files())[:2]
        
        doc_generator = PseudoDocumentGenerator()
        processed_solutions = doc_generator.process_solutions(solutions)
        
        chunk_generator = ChunkGenerator()
        chunks = chunk_generator.process_solutions(processed_solutions)
        
        print(f"✅ Generated {len(chunks)} chunks")
        
        if chunks:
            sample = chunks[0]
            print(f"Sample chunk: {sample.chunk_id}")
            print(f"Chunk type: {sample.chunk_type}")
            print(f"Text length: {sample.character_count} chars")
            return True
        else:
            print("❌ No chunks generated")
            return False
            
    except Exception as e:
        print(f"❌ Chunk generation failed: {e}")
        return False

def test_data_lake_writer():
    """Test data lake writing."""
    
    print("\nData Lake Writer Test")
    print("=" * 25)
    
    try:
        parser = CSVParser()
        solutions = list(parser.parse_all_files())[:2]
        
        doc_generator = PseudoDocumentGenerator()
        processed_solutions = doc_generator.process_solutions(solutions)
        
        chunk_generator = ChunkGenerator()
        chunks = chunk_generator.process_solutions(processed_solutions)
        
        writer = DataLakeWriter()
        writer.write_solutions(processed_solutions)
        writer.write_chunks(chunks)
        
        stats = writer.get_stats()
        print(f"✅ Wrote {stats['text_documents']} documents, {stats['chunks']} chunks")
        print(f"Total size: {stats['total_size_mb']} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Data lake writing failed: {e}")
        return False

def test_layer_imports():
    """Test layer imports using Lambda layer structure."""
    
    print("\nLayer Import Test")
    print("=" * 20)
    
    base_path = Path(__file__).parent
    
    # Test database layer - Lambda layer structure
    db_layer_path = base_path / "layers" / "database-core-layer" / "python"
    
    if not db_layer_path.exists():
        raise RuntimeError(f"Database layer path not found: {db_layer_path}")
    
    # Add the layer python directory to sys.path (Lambda layer convention)
    if str(db_layer_path.absolute()) not in sys.path:
        sys.path.insert(0, str(db_layer_path.absolute()))
    
    try:
        # Import using the same pattern as Lambda
        from utils.DocumentIDManager import DocumentIDManager
        from utils.DatabaseManager import DatabaseManager
        
        print(f"✅ Database layer imports successful from: {db_layer_path}")
        
        # Test instantiation (will fail without DATABASE_SECRET_NAME, but that's expected)
        try:
            doc_mgr = DocumentIDManager()
            print("✅ DocumentIDManager instantiated successfully")
        except Exception as e:
            if "DATABASE_SECRET_NAME" in str(e):
                print("✅ DocumentIDManager import successful (instantiation requires DATABASE_SECRET_NAME)")
            else:
                print(f"❌ DocumentIDManager instantiation failed: {e}")
                raise
                
    except ImportError as e:
        print(f"❌ Database layer import failed: {e}")
        raise RuntimeError(f"Critical system error - database layer imports failed: {e}")
    
    # Test knowledge graph layer
    kg_layer_path = base_path / "layers" / "knowledge-graph-layer" / "python"
    
    if not kg_layer_path.exists():
        raise RuntimeError(f"Knowledge graph layer path not found: {kg_layer_path}")
    
    if str(kg_layer_path.absolute()) not in sys.path:
        sys.path.insert(0, str(kg_layer_path.absolute()))
    
    try:
        from utils.KnowledgeGraphManager import KnowledgeGraphManager
        print(f"✅ Knowledge graph layer imports successful from: {kg_layer_path}")
    except ImportError as e:
        print(f"❌ Knowledge graph layer import failed: {e}")
        raise RuntimeError(f"Critical system error - knowledge graph layer imports failed: {e}")
    
    return True

def main():
    """Run local setup tests."""
    
    print("Local Setup Test Suite")
    print("=" * 50)
    
    # Run tests
    csv_ok = test_csv_parsing()
    pseudo_ok = test_pseudo_document_generation()
    chunk_ok = test_chunk_generation()
    data_lake_ok = test_data_lake_writer()
    layers_ok = test_layer_imports()
    
    # Summary
    print("\n" + "=" * 50)
    print("LOCAL TEST RESULTS")
    print("=" * 50)
    
    print(f"CSV Parsing: {'✅' if csv_ok else '❌'}")
    print(f"Pseudo-Documents: {'✅' if pseudo_ok else '❌'}")
    print(f"Chunk Generation: {'✅' if chunk_ok else '❌'}")
    print(f"Data Lake Writer: {'✅' if data_lake_ok else '❌'}")
    print(f"Layer Imports: {'✅' if layers_ok else '❌' if os.getenv('AWS_EXECUTION_ENV') else '⚠️  (Expected to fail locally)'}")
    
    # On EC2, layer imports should work
    is_ec2 = os.getenv('AWS_EXECUTION_ENV') or os.path.exists('/opt/aws')
    local_ready = csv_ok and pseudo_ok and chunk_ok and data_lake_ok
    ec2_ready = local_ready and (layers_ok if is_ec2 else True)
    
    print(f"\nLocal Development: {'✅ READY' if local_ready else '❌ NEEDS FIXES'}")
    
    if is_ec2:
        print(f"EC2 Environment: {'✅ READY' if ec2_ready else '❌ LAYER IMPORTS FAILING'}")
    else:
        print(f"EC2 Deployment: {'✅ READY TO TEST' if local_ready else '❌ FIX LOCAL ISSUES FIRST'}")
    
    if local_ready:
        print("\nNext steps:")
        print("1. Run ./deploy.sh to create deployment package")
        print("2. Deploy to EC2 and run test_database_integration.py")
        print("3. Validate DocumentIDManager and DatabaseManager")
    
    if not layers_ok and is_ec2:
        print("\n❌ LAYER IMPORT ISSUES DETECTED ON EC2")
        print("Run diagnostic: python test_layer_imports.py")
        print("Check layer deployment and path configuration")
    elif not layers_ok:
        print("\nFor layer import debugging on EC2:")
        print("Run: python test_layer_imports.py")

if __name__ == "__main__":
    main()