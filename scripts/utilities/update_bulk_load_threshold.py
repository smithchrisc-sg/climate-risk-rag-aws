#!/usr/bin/env python3
"""
Update the bulk load threshold in the knowledge graph layer
"""

def update_bulk_load_threshold():
    """Update BULK_LOAD_THRESHOLD to a higher value for document structure data"""
    
    file_path = "/Users/chris/climate-risk-rag-aws/layers/knowledge-graph-layer/python/utils/BulkLoadManager.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update the threshold from 1000 to 5000
    # This ensures document structure data (typically 1000-3000 estimated triples) uses SPARQL INSERT
    old_threshold = "BULK_LOAD_THRESHOLD = 1000"
    new_threshold = "BULK_LOAD_THRESHOLD = 5000"
    
    if old_threshold in content:
        updated_content = content.replace(old_threshold, new_threshold)
        
        # Write back
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        print(f"✅ Updated BULK_LOAD_THRESHOLD from 1000 to 5000")
        print(f"📋 This ensures document structure data uses SPARQL INSERT")
        print(f"📋 Bulk load will be used for datasets with >5000 estimated triples")
        
        return True
    else:
        print(f"❌ Could not find BULK_LOAD_THRESHOLD = 1000 in {file_path}")
        return False

def rebuild_knowledge_graph_layer():
    """Rebuild the knowledge graph layer with updated threshold"""
    import subprocess
    import os
    
    layer_dir = "/Users/chris/climate-risk-rag-aws/layers/knowledge-graph-layer"
    
    try:
        # Change to layer directory
        os.chdir(layer_dir)
        
        # Run the build script
        result = subprocess.run(['./build_layer.sh'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Knowledge graph layer rebuilt successfully")
            return True
        else:
            print(f"❌ Layer build failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error rebuilding layer: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Updating bulk load threshold for better SPARQL INSERT usage...")
    print("=" * 70)
    
    if update_bulk_load_threshold():
        print(f"\n🏗️  Rebuilding knowledge graph layer...")
        if rebuild_knowledge_graph_layer():
            print(f"\n🎯 Next steps:")
            print(f"1. Update kg-triple-loader function with new layer")
            print(f"2. Test with document structure data")
            print(f"3. Verify SPARQL INSERT is used instead of bulk load")
        else:
            print(f"\n⚠️  Layer rebuild failed - manual rebuild required")
    else:
        print(f"\n❌ Threshold update failed")
