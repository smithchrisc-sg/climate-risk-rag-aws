#!/usr/bin/env python3
"""
Standalone Entity Mapping Quality Analysis
Analyzes existing NLP results to understand mapping success rates
WITHOUT modifying any production code
"""
import boto3
import json
import tempfile
import tarfile
from datetime import datetime
from typing import Dict, List, Any

def analyze_document_mapping_quality(doc_id: str) -> Dict[str, Any]:
    """Analyze mapping quality for a specific document using existing data"""
    
    print(f"🔍 Analyzing mapping quality for document: {doc_id}")
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    try:
        # Step 1: Load original text
        text_bucket = "solve-global-kr-dl-text-861276078413-us-east-1"
        text_key = f"data-lake/{doc_id}/raw_text.txt"
        
        response = s3_client.get_object(Bucket=text_bucket, Key=text_key)
        original_text = response['Body'].read().decode('utf-8')
        print(f"✅ Loaded original text: {len(original_text):,} characters")
        
        # Step 2: Load chunks
        chunks_bucket = "solve-global-kr-dl-chunks-861276078413-us-east-1"
        chunks_prefix = f"data-lake/{doc_id}/"
        
        response = s3_client.list_objects_v2(Bucket=chunks_bucket, Prefix=chunks_prefix)
        chunk_files = [obj['Key'] for obj in response.get('Contents', []) 
                      if obj['Key'].endswith('.json') and 'chunk_' in obj['Key']]
        
        chunks = []
        for chunk_file in chunk_files:
            obj_response = s3_client.get_object(Bucket=chunks_bucket, Key=chunk_file)
            chunk_data = json.loads(obj_response['Body'].read().decode('utf-8'))
            chunks.append(chunk_data)
        
        print(f"✅ Loaded {len(chunks)} chunks")
        
        # Step 3: Analyze chunk finding success
        chunks_found = 0
        chunks_not_found = []
        potential_ocr_issues = []
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '').strip()
            chunk_id = chunk.get('chunk_id', '')
            
            if chunk_text and chunk_text in original_text:
                chunks_found += 1
            else:
                chunks_not_found.append(chunk_id)
                
                # Check for OCR/formatting artifacts
                if any(indicator in chunk_text.lower() for indicator in 
                      ['public disclosure', 'authorized', 'document of']):
                    potential_ocr_issues.append({
                        'chunk_id': chunk_id,
                        'issue_type': 'document_watermark',
                        'section_type': chunk.get('section_type', 'unknown'),
                        'text_preview': chunk_text[:100]
                    })
        
        chunk_finding_rate = (chunks_found / len(chunks) * 100) if chunks else 0
        
        # Step 4: Load real Comprehend results
        ner_bucket = "solve-global-kr-dl-ner-results-861276078413-us-east-1"
        
        # Get entity results
        entity_dirs = []
        try:
            response = s3_client.list_objects_v2(
                Bucket=ner_bucket,
                Prefix=f"comprehend-output/{doc_id}/entities/",
                Delimiter='/'
            )
            entity_dirs = [prefix['Prefix'] for prefix in response.get('CommonPrefixes', [])]
        except:
            pass
        
        entities = []
        if entity_dirs:
            # Use the first entity result directory
            entity_dir = entity_dirs[0]
            entity_file = f"{entity_dir}output/output.tar.gz"
            
            try:
                with tempfile.NamedTemporaryFile() as tmp_file:
                    s3_client.download_fileobj(ner_bucket, entity_file, tmp_file)
                    tmp_file.seek(0)
                    
                    with tarfile.open(fileobj=tmp_file, mode='r:gz') as tar:
                        output_file = tar.extractfile('output')
                        comprehend_output = json.loads(output_file.read().decode('utf-8'))
                        entities = comprehend_output.get('Entities', [])
            except Exception as e:
                print(f"⚠️  Could not load entity results: {e}")
        
        print(f"✅ Loaded {len(entities)} entities from Comprehend")
        
        # Step 5: Simulate entity mapping analysis
        mappable_entities = 0
        unmappable_entities = 0
        entity_type_analysis = {
            'LOCATION': {'mappable': 0, 'unmappable': 0},
            'ORGANIZATION': {'mappable': 0, 'unmappable': 0},
            'PERSON': {'mappable': 0, 'unmappable': 0},
            'DATE': {'mappable': 0, 'unmappable': 0},
            'QUANTITY': {'mappable': 0, 'unmappable': 0},
            'OTHER': {'mappable': 0, 'unmappable': 0}
        }
        
        # Find chunks that exist in original text (mappable chunks)
        mappable_chunk_positions = []
        for chunk in chunks:
            chunk_text = chunk.get('text', '').strip()
            if chunk_text and chunk_text in original_text:
                pos = original_text.find(chunk_text)
                mappable_chunk_positions.append({
                    'chunk_id': chunk.get('chunk_id'),
                    'start_offset': pos,
                    'end_offset': pos + len(chunk_text)
                })
        
        # Analyze which entities could be mapped
        for entity in entities:
            entity_start = entity.get('BeginOffset', 0)
            entity_end = entity.get('EndOffset', 0)
            entity_type = entity.get('Type', 'OTHER')
            
            # Check if entity overlaps with any mappable chunk
            can_map = False
            for chunk_pos in mappable_chunk_positions:
                if (entity_start < chunk_pos['end_offset'] and 
                    entity_end > chunk_pos['start_offset']):
                    can_map = True
                    break
            
            if can_map:
                mappable_entities += 1
                entity_type_analysis[entity_type]['mappable'] += 1
            else:
                unmappable_entities += 1
                entity_type_analysis[entity_type]['unmappable'] += 1
        
        # Calculate metrics
        total_entities = len(entities)
        entity_mapping_rate = (mappable_entities / total_entities * 100) if total_entities > 0 else 0
        
        # Calculate search quality impact
        critical_types = ['LOCATION', 'ORGANIZATION', 'PERSON']
        critical_mappable = sum(entity_type_analysis[t]['mappable'] for t in critical_types)
        critical_unmappable = sum(entity_type_analysis[t]['unmappable'] for t in critical_types)
        total_critical = critical_mappable + critical_unmappable
        critical_success_rate = (critical_mappable / total_critical * 100) if total_critical > 0 else 0
        
        # Estimate search quality impact
        search_impact = 0.0
        for entity_type, counts in entity_type_analysis.items():
            if entity_type in ['LOCATION', 'ORGANIZATION']:
                search_impact += counts['mappable'] * 1.0  # High impact
            elif entity_type == 'PERSON':
                search_impact += counts['mappable'] * 0.8  # Medium-high impact
            elif entity_type in ['DATE', 'QUANTITY']:
                search_impact += counts['mappable'] * 0.6  # Medium impact
            else:
                search_impact += counts['mappable'] * 0.4  # Lower impact
        
        # Compile comprehensive analysis
        analysis = {
            'doc_id': doc_id,
            'timestamp': datetime.utcnow().isoformat(),
            'analysis_type': 'mapping_quality_assessment',
            
            # Basic metrics
            'total_chunks': len(chunks),
            'chunks_found_in_original': chunks_found,
            'chunks_not_found': len(chunks_not_found),
            'chunk_finding_success_rate': round(chunk_finding_rate, 2),
            
            # Entity mapping potential
            'total_entities': total_entities,
            'entities_mappable': mappable_entities,
            'entities_unmappable': unmappable_entities,
            'entity_mapping_potential_rate': round(entity_mapping_rate, 2),
            
            # Critical entity analysis
            'critical_entities_mappable': critical_mappable,
            'critical_entities_unmappable': critical_unmappable,
            'critical_entity_success_rate': round(critical_success_rate, 2),
            
            # Search impact estimation
            'estimated_search_quality_impact': round(search_impact, 3),
            'entity_type_breakdown': entity_type_analysis,
            
            # Issue analysis
            'potential_ocr_issues': len(potential_ocr_issues),
            'ocr_issue_samples': potential_ocr_issues[:3],
            'chunks_not_found_sample': chunks_not_found[:5],
            
            # Recommendations
            'recommendations': generate_recommendations(chunk_finding_rate, critical_success_rate, potential_ocr_issues)
        }
        
        return analysis
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None

def generate_recommendations(chunk_finding_rate: float, critical_success_rate: float, 
                           ocr_issues: List[Dict]) -> List[str]:
    """Generate recommendations based on analysis results"""
    
    recommendations = []
    
    if chunk_finding_rate < 95:
        recommendations.append(f"Chunk finding rate is {chunk_finding_rate:.1f}% - consider fuzzy matching")
    
    if critical_success_rate < 90:
        recommendations.append(f"Critical entity success rate is {critical_success_rate:.1f}% - prioritize LOCATION/ORGANIZATION mapping")
    
    if len(ocr_issues) > 0:
        recommendations.append(f"Found {len(ocr_issues)} potential OCR artifacts - consider text normalization")
    
    if chunk_finding_rate > 95 and critical_success_rate > 90:
        recommendations.append("Mapping quality is excellent - current approach is sufficient")
    
    return recommendations

def analyze_multiple_documents(doc_ids: List[str]) -> Dict[str, Any]:
    """Analyze mapping quality across multiple documents"""
    
    print(f"📊 Analyzing mapping quality across {len(doc_ids)} documents")
    
    all_analyses = []
    summary_stats = {
        'total_documents': len(doc_ids),
        'successful_analyses': 0,
        'avg_chunk_finding_rate': 0.0,
        'avg_entity_mapping_rate': 0.0,
        'avg_critical_success_rate': 0.0,
        'total_ocr_issues': 0
    }
    
    for doc_id in doc_ids:
        analysis = analyze_document_mapping_quality(doc_id)
        if analysis:
            all_analyses.append(analysis)
            summary_stats['successful_analyses'] += 1
            summary_stats['avg_chunk_finding_rate'] += analysis['chunk_finding_success_rate']
            summary_stats['avg_entity_mapping_rate'] += analysis['entity_mapping_potential_rate']
            summary_stats['avg_critical_success_rate'] += analysis['critical_entity_success_rate']
            summary_stats['total_ocr_issues'] += analysis['potential_ocr_issues']
    
    # Calculate averages
    if summary_stats['successful_analyses'] > 0:
        count = summary_stats['successful_analyses']
        summary_stats['avg_chunk_finding_rate'] = round(summary_stats['avg_chunk_finding_rate'] / count, 2)
        summary_stats['avg_entity_mapping_rate'] = round(summary_stats['avg_entity_mapping_rate'] / count, 2)
        summary_stats['avg_critical_success_rate'] = round(summary_stats['avg_critical_success_rate'] / count, 2)
    
    return {
        'summary_stats': summary_stats,
        'individual_analyses': all_analyses,
        'timestamp': datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Test with our known document
    doc_id = "064762102bead7b04a39"
    
    print("🧪 SAFE MAPPING QUALITY ANALYSIS")
    print("✅ No production code modifications")
    print("✅ Uses existing data in S3")
    
    analysis = analyze_document_mapping_quality(doc_id)
    
    if analysis:
        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"  Chunk finding success rate: {analysis['chunk_finding_success_rate']}%")
        print(f"  Entity mapping potential rate: {analysis['entity_mapping_potential_rate']}%")
        print(f"  Critical entity success rate: {analysis['critical_entity_success_rate']}%")
        print(f"  Search quality impact score: {analysis['estimated_search_quality_impact']}")
        print(f"  Potential OCR issues: {analysis['potential_ocr_issues']}")
        
        print(f"\n🏷️  ENTITY TYPE BREAKDOWN:")
        for entity_type, counts in analysis['entity_type_breakdown'].items():
            total = counts['mappable'] + counts['unmappable']
            if total > 0:
                rate = (counts['mappable'] / total * 100)
                print(f"  {entity_type}: {counts['mappable']}/{total} mappable ({rate:.1f}%)")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in analysis['recommendations']:
            print(f"  • {rec}")
        
        print(f"\n🎉 Analysis complete - no production code touched!")
        
    else:
        print(f"❌ Analysis failed for document {doc_id}")
