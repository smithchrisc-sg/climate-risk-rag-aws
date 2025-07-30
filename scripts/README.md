# Scripts Directory Organization

This directory contains organized utility scripts for the Climate Risk RAG system. Scripts have been categorized by function to improve maintainability and discoverability.

## 📁 Directory Structure

### `deployment/`
Scripts for deploying infrastructure and Lambda functions:
- CDK deployment scripts
- Lambda deployment utilities
- Infrastructure setup scripts

### `testing/`
Scripts for testing various components:
- End-to-end pipeline tests
- Integration tests
- Component-specific tests
- Test utilities and helpers

### `maintenance/`
Scripts for system maintenance and operations:
- Cleanup utilities
- Status monitoring
- Data processing scripts
- System maintenance tasks

### `database/`
Database-related scripts:
- Schema migrations
- Database cleanup
- Data migration scripts
- Database utilities

### `lambda-updates/`
Scripts for updating and fixing Lambda functions:
- Lambda code updates
- Configuration fixes
- Environment variable updates
- Bug fixes and patches

### `infrastructure/`
Infrastructure management scripts:
- Layer building scripts
- Infrastructure validation
- System configuration

### `analysis/`
Analysis and monitoring scripts:
- Performance analysis
- Data analysis utilities
- System monitoring
- Connection examples

### `test-data/`
Test data files and configuration:
- Sample payloads
- Test results
- Configuration files
- Mock data

### `DEPRECATED/`
Obsolete scripts kept for reference:
- Old versions of scripts
- Deprecated implementations
- One-off fixes no longer needed
- Legacy code

## 🎯 Main Entry Point

The primary script remains at the root level:
- `../invoke_pipeline_test.py` - Main pipeline testing script

## 📋 Usage Guidelines

1. **Before running any script**: Check if it's in the DEPRECATED folder
2. **For testing**: Start with scripts in `testing/` directory
3. **For deployment**: Use scripts in `deployment/` directory
4. **For maintenance**: Use scripts in `maintenance/` directory

## 🔍 Finding Scripts

To find a specific script:
```bash
# Search by name
find scripts/ -name "*keyword*"

# Search by content
grep -r "search_term" scripts/

# List all scripts in a category
ls scripts/category_name/
```

## ⚠️ Important Notes

- Scripts in `DEPRECATED/` should not be used for new development
- Always check script documentation before running
- Some scripts may require specific environment setup
- Test scripts in development environment before production use

---

**Last Updated**: 2025-07-29  
**Organization**: Categorical by function  
**Total Scripts Organized**: ~150+ files
