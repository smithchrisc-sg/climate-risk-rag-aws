#!/usr/bin/env python3
"""
Migrate only embeddings for the sample documents
"""

import sys
import json
sys.path.append('.')
from selective_migration_ner import SelectiveMigrator

def main():
    # Load sample
    with open('migration/sample_documents_1000_ner.json', 'r') as f:
        sample = json.load(f)

    sample_docs = sample['sample_documents']
    
    print(f"🔧 Migrating embeddings for {len(sample_docs)} sample documents...")
    print("This will upload ~275K embedding files to S3...")

    # Create migrator
    migrator = SelectiveMigrator(
        local_path='/Volumes/G-RAID Photo 24TB/climate_risk_rag',
        documents_bucket='solve-global-kr-documents-861276078413-us-west-2',
        chunks_bucket='solve-global-kr-chunks-861276078413-us-west-2',
        embeddings_bucket='solve-global-kr-embeddings-861276078413-us-west-2',
        ner_results_bucket='solve-global-kr-ner-861276078413-us-west-2',
        extracted_text_bucket='solve-global-kr-text-861276078413-us-west-2',
        region='us-west-2',
        profile='solve-global'
    )

    # Migrate embeddings only
    success = migrator.migrate_sample_embeddings(sample_docs, dry_run=False)
    
    if success:
        print("✅ Embeddings migration completed successfully!")
        print(f"📊 Uploaded embeddings: {migrator.stats['embeddings_uploaded']}")
    else:
        print("❌ Embeddings migration failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
