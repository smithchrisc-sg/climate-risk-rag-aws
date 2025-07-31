#!/usr/bin/env python3
"""
Migration Script: Update all CDK files to use Knowledge Graph Layer v2.0.0
Ensures all Lambda functions use the updated layer with NLP-Ontology integration
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Tuple

class KGLayerV2Migrator:
    """
    Migrates CDK files to use Knowledge Graph Layer v2.0.0
    Maintains backward compatibility while updating layer references
    """
    
    def __init__(self, cdk_directory: str):
        self.cdk_directory = Path(cdk_directory)
        self.backup_directory = self.cdk_directory / "backups_kg_v2_migration"
        self.migration_log = []
        
    def migrate_all_files(self) -> Dict[str, List[str]]:
        """
        Migrate all CDK files to use Knowledge Graph Layer v2.0.0
        
        Returns:
            Dictionary with migration results
        """
        print("🚀 Starting Knowledge Graph Layer v2.0.0 migration...")
        
        # Create backup directory
        self._create_backup_directory()
        
        # Find all CDK files that need updating
        files_to_update = self._find_files_to_update()
        
        print(f"📁 Found {len(files_to_update)} files to update:")
        for file_path in files_to_update:
            print(f"   - {file_path.name}")
        
        # Backup and update each file
        migration_results = {
            'updated_files': [],
            'backup_files': [],
            'errors': []
        }
        
        for file_path in files_to_update:
            try:
                # Create backup
                backup_path = self._backup_file(file_path)
                migration_results['backup_files'].append(str(backup_path))
                
                # Update file
                updated = self._update_file(file_path)
                if updated:
                    migration_results['updated_files'].append(str(file_path))
                    print(f"✅ Updated: {file_path.name}")
                else:
                    print(f"⚠️  No changes needed: {file_path.name}")
                    
            except Exception as e:
                error_msg = f"❌ Error updating {file_path.name}: {str(e)}"
                migration_results['errors'].append(error_msg)
                print(error_msg)
        
        # Generate migration report
        self._generate_migration_report(migration_results)
        
        print(f"\n🎉 Migration completed!")
        print(f"   - Updated files: {len(migration_results['updated_files'])}")
        print(f"   - Backup files: {len(migration_results['backup_files'])}")
        print(f"   - Errors: {len(migration_results['errors'])}")
        print(f"   - Backups stored in: {self.backup_directory}")
        
        return migration_results
    
    def _create_backup_directory(self):
        """Create backup directory for original files"""
        self.backup_directory.mkdir(exist_ok=True)
        print(f"📂 Created backup directory: {self.backup_directory}")
    
    def _find_files_to_update(self) -> List[Path]:
        """Find all CDK files that reference knowledge-graph-layer"""
        files_to_update = []
        
        # Search patterns for files that need updating
        search_patterns = [
            r'knowledge-graph-layer',
            r'KnowledgeGraphLayer',
            r'knowledge_graph_layer'
        ]
        
        # Find all Python files in CDK directory
        for py_file in self.cdk_directory.glob("**/*.py"):
            if py_file.name.startswith('.') or 'backup' in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check if file contains any search patterns
                for pattern in search_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        files_to_update.append(py_file)
                        break
                        
            except Exception as e:
                print(f"⚠️  Could not read {py_file}: {e}")
        
        return files_to_update
    
    def _backup_file(self, file_path: Path) -> Path:
        """Create backup of original file"""
        backup_path = self.backup_directory / f"{file_path.name}.backup"
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _update_file(self, file_path: Path) -> bool:
        """
        Update a single CDK file to use Knowledge Graph Layer v2.0.0
        
        Returns:
            True if file was updated, False if no changes needed
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        updated_content = original_content
        changes_made = False
        
        # Update 1: Layer version references
        layer_version_updates = [
            # Update layer zip file references
            (r'knowledge-graph-layer-v1\.0\.\d+\.zip', 'knowledge-graph-layer-v2.0.0.zip'),
            (r'knowledge-graph-layer\.zip', 'knowledge-graph-layer-v2.0.0.zip'),
            
            # Update layer descriptions
            (r'Knowledge Graph operations layer v1\.\d+\.\d+', 'Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration'),
            (r'Knowledge Graph Layer v1\.\d+\.\d+', 'Knowledge Graph Layer v2.0.0 with NLP-Ontology Integration'),
            
            # Update layer version names
            (r'layer_version_name="knowledge-graph-layer-v2"', 'layer_version_name="knowledge-graph-layer-v2"'),
        ]
        
        for pattern, replacement in layer_version_updates:
            new_content = re.sub(pattern, replacement, updated_content)
            if new_content != updated_content:
                updated_content = new_content
                changes_made = True
                self.migration_log.append(f"Updated layer reference in {file_path.name}: {pattern} -> {replacement}")
        
        # Update 2: Function names to avoid conflicts
        function_name_updates = [
            # Add v2 suffix to existing functions using the layer
            (r'function_name="solve-global-kr-document-structure-kg-processor-v2"', 
             'function_name="solve-global-kr-document-structure-kg-processor-v2"'),
            (r'function_name="solve-global-kr-kg-triple-loader-v2"', 
             'function_name="solve-global-kr-kg-triple-loader-v2"'),
        ]
        
        for pattern, replacement in function_name_updates:
            new_content = re.sub(pattern, replacement, updated_content)
            if new_content != updated_content:
                updated_content = new_content
                changes_made = True
                self.migration_log.append(f"Updated function name in {file_path.name}: {pattern} -> {replacement}")
        
        # Update 3: Add memory size increases for functions that might need it
        memory_updates = [
            # Increase memory for functions that will use NLP utilities
            (r'memory_size=1024,(\s*#.*NLP|.*nlp)', 'memory_size=1024,\\1'),
        ]
        
        for pattern, replacement in memory_updates:
            new_content = re.sub(pattern, replacement, updated_content)
            if new_content != updated_content:
                updated_content = new_content
                changes_made = True
                self.migration_log.append(f"Updated memory size in {file_path.name}")
        
        # Update 4: Add comments about v2.0.0 compatibility
        if 'knowledge-graph-layer' in updated_content and '# Updated to v2.0.0' not in updated_content:
            # Add comment near layer definition
            layer_comment = '        # Updated to Knowledge Graph Layer v2.0.0 - Maintains backward compatibility\n'
            updated_content = re.sub(
                r'(\s*)(self\.knowledge_graph_layer = lambda_\.LayerVersion\()',
                r'\1# Updated to Knowledge Graph Layer v2.0.0 - Maintains backward compatibility\n\1\2',
                updated_content
            )
            if updated_content != original_content:
                changes_made = True
                self.migration_log.append(f"Added v2.0.0 compatibility comment to {file_path.name}")
        
        # Write updated content if changes were made
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
        
        return changes_made
    
    def _generate_migration_report(self, results: Dict[str, List[str]]):
        """Generate detailed migration report"""
        report_path = self.backup_directory / "migration_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Knowledge Graph Layer v2.0.0 Migration Report\n\n")
            f.write(f"**Migration Date**: {os.popen('date').read().strip()}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Files Updated**: {len(results['updated_files'])}\n")
            f.write(f"- **Backup Files Created**: {len(results['backup_files'])}\n")
            f.write(f"- **Errors**: {len(results['errors'])}\n\n")
            
            f.write("## Updated Files\n\n")
            for file_path in results['updated_files']:
                f.write(f"- `{file_path}`\n")
            
            f.write("\n## Backup Files\n\n")
            for backup_path in results['backup_files']:
                f.write(f"- `{backup_path}`\n")
            
            if results['errors']:
                f.write("\n## Errors\n\n")
                for error in results['errors']:
                    f.write(f"- {error}\n")
            
            f.write("\n## Detailed Changes\n\n")
            for log_entry in self.migration_log:
                f.write(f"- {log_entry}\n")
            
            f.write("\n## Next Steps\n\n")
            f.write("1. **Build the new layer**: Run `./build_layer_v2.sh` in the knowledge-graph-layer directory\n")
            f.write("2. **Test existing functions**: Verify document-structure-kg-processor works with v2.0.0\n")
            f.write("3. **Deploy updated CDK**: Run `cdk deploy` to update infrastructure\n")
            f.write("4. **Create new NLP Lambda functions**: Deploy the new NLP processing functions\n")
            f.write("5. **Validate end-to-end**: Test the complete NLP-ontology integration pipeline\n\n")
            
            f.write("## Rollback Instructions\n\n")
            f.write("If issues occur, restore original files from backups:\n\n")
            f.write("```bash\n")
            for i, (original, backup) in enumerate(zip(results['updated_files'], results['backup_files'])):
                f.write(f"cp '{backup}' '{original}'\n")
            f.write("```\n")
        
        print(f"📄 Migration report generated: {report_path}")

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate CDK files to Knowledge Graph Layer v2.0.0")
    parser.add_argument("--cdk-dir", default="/Users/chris/climate-risk-rag-aws/cdk", 
                       help="Path to CDK directory")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be updated without making changes")
    
    args = parser.parse_args()
    
    migrator = KGLayerV2Migrator(args.cdk_dir)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        files_to_update = migrator._find_files_to_update()
        print(f"📁 Would update {len(files_to_update)} files:")
        for file_path in files_to_update:
            print(f"   - {file_path}")
    else:
        results = migrator.migrate_all_files()
        
        if results['errors']:
            print("\n⚠️  Some errors occurred during migration. Check the migration report for details.")
            return 1
        else:
            print("\n✅ Migration completed successfully!")
            return 0

if __name__ == "__main__":
    exit(main())
