#!/usr/bin/env python3
"""
Review Hierarchical Chunks for RDF Document Structure Design
Analyzes the new chunk structure to inform RDF graph model updates
"""

import boto3
import json
import logging
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def review_chunks_for_rdf():
    """Review hierarchical chunks to understand structure for RDF mapping"""
    
    doc_id = "064762102bead7b04a39"
    chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
    
    logger.info(f"📋 Reviewing hierarchical chunks for RDF design: {doc_id}")
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        # List and download chunks
        response = s3_client.list_objects_v2(
            Bucket=chunks_bucket,
            Prefix=f"data-lake/{doc_id}/"
        )
        
        chunk_files = [obj['Key'] for obj in response.get('Contents', []) 
                      if '_chunk_' in obj['Key'] and obj['Key'].endswith('.json')]
        
        chunk_files.sort()
        logger.info(f"Found {len(chunk_files)} chunk files")
        
        # Download all chunks
        chunks = []
        for chunk_file in chunk_files:
            obj = s3_client.get_object(Bucket=chunks_bucket, Key=chunk_file)
            chunk_data = json.loads(obj['Body'].read())
            chunks.append(chunk_data)
        
        logger.info("\n" + "="*80)
        logger.info("📊 CHUNK STRUCTURE ANALYSIS FOR RDF DESIGN")
        logger.info("="*80)
        
        # 1. Analyze chunk properties for RDF schema design
        analyze_chunk_properties(chunks)
        
        # 2. Show hierarchical relationships
        analyze_hierarchical_relationships(chunks)
        
        # 3. Show document structure patterns
        analyze_document_structure_patterns(chunks)
        
        # 4. Show specific examples for each section type
        show_section_type_examples(chunks)
        
        # 5. Analyze split paragraphs
        analyze_split_paragraphs(chunks)
        
        # 6. Propose RDF structure
        propose_rdf_structure(chunks)
        
        return chunks
        
    except Exception as e:
        logger.error(f"❌ Review failed: {str(e)}")
        return None

def analyze_chunk_properties(chunks):
    """Analyze chunk properties for RDF schema design"""
    
    logger.info("\n🔍 CHUNK PROPERTIES ANALYSIS")
    logger.info("-" * 40)
    
    # Collect all unique properties
    all_properties = set()
    property_types = defaultdict(set)
    
    for chunk in chunks:
        for key, value in chunk.items():
            all_properties.add(key)
            property_types[key].add(type(value).__name__)
    
    logger.info("📋 Available Properties for RDF Mapping:")
    for prop in sorted(all_properties):
        types = ", ".join(sorted(property_types[prop]))
        logger.info(f"  • {prop}: {types}")
    
    # Analyze key structural properties
    logger.info("\n🏗️  Key Structural Properties:")
    
    hierarchy_levels = Counter(chunk.get('hierarchy_level') for chunk in chunks)
    section_types = Counter(chunk.get('section_type') for chunk in chunks)
    
    logger.info(f"  • hierarchy_level distribution: {dict(sorted(hierarchy_levels.items()))}")
    logger.info(f"  • section_type distribution: {dict(sorted(section_types.items()))}")
    
    # Parent-child relationship analysis
    chunks_with_parents = sum(1 for chunk in chunks if chunk.get('parent_chunk_id'))
    chunks_with_children = sum(1 for chunk in chunks if chunk.get('child_chunk_ids'))
    
    logger.info(f"  • Chunks with parents: {chunks_with_parents}/{len(chunks)}")
    logger.info(f"  • Chunks with children: {chunks_with_children}/{len(chunks)}")

def analyze_hierarchical_relationships(chunks):
    """Analyze hierarchical relationships for RDF structure"""
    
    logger.info("\n🌳 HIERARCHICAL RELATIONSHIP ANALYSIS")
    logger.info("-" * 40)
    
    # Build relationship maps
    parent_to_children = defaultdict(list)
    child_to_parent = {}
    
    for chunk in chunks:
        chunk_id = chunk['chunk_id']
        parent_id = chunk.get('parent_chunk_id')
        child_ids = chunk.get('child_chunk_ids', [])
        
        if parent_id:
            child_to_parent[chunk_id] = parent_id
            parent_to_children[parent_id].append(chunk_id)
    
    # Find root nodes (no parents)
    root_chunks = [chunk for chunk in chunks if not chunk.get('parent_chunk_id')]
    
    logger.info(f"📊 Relationship Statistics:")
    logger.info(f"  • Root chunks (no parent): {len(root_chunks)}")
    logger.info(f"  • Parent-child pairs: {len(child_to_parent)}")
    logger.info(f"  • Unique parents: {len(parent_to_children)}")
    
    # Show root chunk structure
    logger.info(f"\n🌲 Root Chunk Structure:")
    for i, root in enumerate(root_chunks[:5]):  # Show first 5
        section_type = root.get('section_type', 'unknown')
        level = root.get('hierarchy_level', 0)
        children_count = len(root.get('child_chunk_ids', []))
        text_preview = root.get('text', '')[:50].replace('\n', ' ')
        
        logger.info(f"  {i+1}. {root['chunk_id']}")
        logger.info(f"     Type: {section_type}, Level: {level}, Children: {children_count}")
        logger.info(f"     Text: \"{text_preview}...\"")
    
    if len(root_chunks) > 5:
        logger.info(f"     ... and {len(root_chunks) - 5} more root chunks")

def analyze_document_structure_patterns(chunks):
    """Analyze document structure patterns"""
    
    logger.info("\n📐 DOCUMENT STRUCTURE PATTERNS")
    logger.info("-" * 40)
    
    # Analyze hierarchy patterns
    level_to_types = defaultdict(Counter)
    type_to_levels = defaultdict(Counter)
    
    for chunk in chunks:
        level = chunk.get('hierarchy_level', 0)
        section_type = chunk.get('section_type', 'unknown')
        
        level_to_types[level][section_type] += 1
        type_to_levels[section_type][level] += 1
    
    logger.info("📊 Hierarchy Level → Section Type Patterns:")
    for level in sorted(level_to_types.keys()):
        types = dict(level_to_types[level])
        logger.info(f"  Level {level}: {types}")
    
    logger.info("\n📊 Section Type → Hierarchy Level Patterns:")
    for section_type in sorted(type_to_levels.keys()):
        levels = dict(type_to_levels[section_type])
        logger.info(f"  {section_type}: {levels}")

def show_section_type_examples(chunks):
    """Show examples of each section type"""
    
    logger.info("\n📋 SECTION TYPE EXAMPLES")
    logger.info("-" * 40)
    
    # Group chunks by section type
    by_section_type = defaultdict(list)
    for chunk in chunks:
        section_type = chunk.get('section_type', 'unknown')
        by_section_type[section_type].append(chunk)
    
    # Show examples for each type
    for section_type in sorted(by_section_type.keys()):
        chunks_of_type = by_section_type[section_type]
        logger.info(f"\n🏷️  {section_type.upper()} ({len(chunks_of_type)} chunks):")
        
        # Show first 2 examples
        for i, chunk in enumerate(chunks_of_type[:2]):
            level = chunk.get('hierarchy_level', 0)
            parent = chunk.get('parent_chunk_id', 'None')
            children_count = len(chunk.get('child_chunk_ids', []))
            text = chunk.get('text', '')[:100].replace('\n', ' ')
            
            logger.info(f"  Example {i+1}:")
            logger.info(f"    ID: {chunk['chunk_id']}")
            logger.info(f"    Level: {level}, Parent: {parent}, Children: {children_count}")
            logger.info(f"    Text: \"{text}...\"")

def analyze_split_paragraphs(chunks):
    """Analyze split paragraph patterns"""
    
    logger.info("\n✂️  SPLIT PARAGRAPH ANALYSIS")
    logger.info("-" * 40)
    
    split_chunks = [chunk for chunk in chunks if chunk.get('is_split_paragraph', False)]
    
    logger.info(f"📊 Split Paragraph Statistics:")
    logger.info(f"  • Total split chunks: {len(split_chunks)}")
    
    if split_chunks:
        # Group by document and total_splits
        split_groups = defaultdict(list)
        for chunk in split_chunks:
            total_splits = chunk.get('total_splits', 1)
            split_groups[total_splits].append(chunk)
        
        logger.info(f"  • Split size distribution:")
        for total_splits in sorted(split_groups.keys()):
            count = len(split_groups[total_splits]) // total_splits  # Number of original paragraphs
            logger.info(f"    - {total_splits} parts: {count} paragraphs")
        
        # Show example of split paragraph
        example = split_chunks[0]
        logger.info(f"\n📝 Split Paragraph Example:")
        logger.info(f"  ID: {example['chunk_id']}")
        logger.info(f"  Part: {example.get('split_part', 1)}/{example.get('total_splits', 1)}")
        logger.info(f"  Text: \"{example.get('text', '')[:150]}...\"")

def propose_rdf_structure(chunks):
    """Propose RDF structure based on chunk analysis"""
    
    logger.info("\n🎯 PROPOSED RDF STRUCTURE FOR DOCUMENT GRAPH")
    logger.info("="*60)
    
    logger.info("""
📋 Core RDF Classes:

1. Document Structure Classes:
   • doc:Document - The complete document
   • doc:Section - A document section (title, header, etc.)
   • doc:Chunk - Individual text chunks
   • doc:Page - Document pages

2. Content Type Classes:
   • doc:Title - Document/section titles
   • doc:Header - Section headers  
   • doc:Paragraph - Text paragraphs
   • doc:List - List content
   • doc:Table - Tabular content
   • doc:Figure - Figures/images

3. Structural Relationships:
   • doc:hasChild - Parent → Child relationship
   • doc:hasParent - Child → Parent relationship  
   • doc:hasSibling - Sibling relationships
   • doc:isPartOf - Chunk → Section/Document
   • doc:contains - Document/Section → Chunks
   • doc:followedBy - Sequential ordering
   • doc:precededBy - Reverse sequential ordering

4. Properties:
   • doc:chunkId - Unique chunk identifier
   • doc:hierarchyLevel - Structural level (1-5)
   • doc:sectionType - Content type classification
   • doc:pageNumber - Page location
   • doc:characterCount - Text length
   • doc:textContent - Actual text content
   • doc:isSplitParagraph - Boolean for split content
   • doc:splitPart - Part number if split
   • doc:totalSplits - Total parts if split

5. NLP Entity Anchoring:
   • nlp:Entity - Extracted entities (persons, orgs, etc.)
   • nlp:mentionedIn - Entity → Chunk relationship
   • nlp:hasContext - Entity → Parent chunk context
   • nlp:spans - Text span within chunk
   • nlp:confidence - Extraction confidence

6. Example RDF Structure:
   ```turtle
   doc:064762102bead7b04a39 a doc:Document ;
       doc:contains doc:chunk_0009 .
   
   doc:chunk_0009 a doc:Title ;
       doc:chunkId "064762102bead7b04a39_chunk_0009" ;
       doc:hierarchyLevel 1 ;
       doc:sectionType "title" ;
       doc:textContent "ABBREVIATIONS AND ACRONYMS" ;
       doc:hasChild doc:chunk_0000, doc:chunk_0001 ;
       doc:isPartOf doc:064762102bead7b04a39 .
   
   doc:chunk_0000 a doc:Paragraph ;
       doc:chunkId "064762102bead7b04a39_chunk_0000" ;
       doc:hierarchyLevel 2 ;
       doc:hasParent doc:chunk_0009 ;
       doc:hasSibling doc:chunk_0001 ;
       doc:textContent "Public Disclosure Authorized" .
   
   # NLP entities can now be anchored to specific chunks
   nlp:WorldBank a nlp:Organization ;
       nlp:mentionedIn doc:chunk_0001 ;
       nlp:hasContext doc:chunk_0009 .
   ```
""")
    
    logger.info("\n🔗 Benefits for NLP Entity Mapping:")
    logger.info("  ✅ Direct chunk-to-entity relationships")
    logger.info("  ✅ Hierarchical context for entities")
    logger.info("  ✅ Section-type filtering for entity types")
    logger.info("  ✅ Parent-child context propagation")
    logger.info("  ✅ Clean text without artificial context")
    logger.info("  ✅ Proper document structure preservation")

def main():
    """Main review execution"""
    
    logger.info("🚀 Starting chunk review for RDF design")
    
    try:
        chunks = review_chunks_for_rdf()
        
        if chunks:
            logger.info(f"\n" + "="*80)
            logger.info("✅ CHUNK REVIEW COMPLETED SUCCESSFULLY!")
            logger.info("="*80)
            logger.info("Ready to update document structure graph model with:")
            logger.info("• Hierarchical chunk relationships")
            logger.info("• Clean section type boundaries") 
            logger.info("• Parent-child context chains")
            logger.info("• Direct NLP entity anchoring points")
            
            return 0
        else:
            logger.error("❌ Chunk review failed")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Review execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
