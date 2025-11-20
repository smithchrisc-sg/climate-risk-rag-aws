#!/usr/bin/env python3
import os
import glob

def categorize_scripts():
    """Organize scripts by category and generate documentation"""
    
    categories = {
        'data_loading': ['load_', 'split_and_load', 'ttl_', 'geonames'],
        'testing': ['test_', 'invoke_', 'verify_'],
        'deployment': ['deploy_'],
        'analysis': ['analyze_', 'check_', 'diagnose_', 'examine_'],
        'fixes': ['fix_'],
        'utilities': ['generate_', 'convert_', 'create_', 'process_']
    }
    
    root_dir = '/Users/chris/climate-risk-rag-aws'
    scripts = glob.glob(os.path.join(root_dir, '*.py')) + glob.glob(os.path.join(root_dir, '*.sh'))
    
    organized = {cat: [] for cat in categories}
    uncategorized = []
    
    for script in scripts:
        script_name = os.path.basename(script)
        categorized = False
        for category, patterns in categories.items():
            if any(pattern in script_name.lower() for pattern in patterns):
                organized[category].append(script_name)
                categorized = True
                break
        if not categorized:
            uncategorized.append(script_name)
    
    # Generate documentation
    with open(os.path.join(root_dir, 'SCRIPTS_INVENTORY.md'), 'w') as f:
        f.write("# Project Scripts Inventory\n\n")
        
        for category, scripts in organized.items():
            if scripts:
                f.write("## " + category.replace('_', ' ').title() + "\n")
                for script in sorted(scripts):
                    f.write("- `" + script + "`\n")
                f.write("\n")
        
        if uncategorized:
            f.write("## Uncategorized\n")
            for script in sorted(uncategorized):
                f.write("- `" + script + "`\n")
    
    print("Generated SCRIPTS_INVENTORY.md with " + str(sum(len(s) for s in organized.values())) + " categorized scripts")

if __name__ == "__main__":
    categorize_scripts()
