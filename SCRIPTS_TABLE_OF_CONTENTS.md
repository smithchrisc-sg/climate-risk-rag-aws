# Scripts Table of Contents
**Created**: 2025-11-20  
**Purpose**: Organized directory structure for utility scripts and tools

## 📁 Directory Structure

### **Top Level**
- `invoke_pipeline_test.py` - Main pipeline testing entry point (frequently used)

### **`/scripts/analysis/`** - Data Analysis & Exploration
Scripts for analyzing data, exploring datasets, and generating insights.

| Script | Purpose |
|--------|---------|
| `analyze_adm_levels.py` | Administrative level analysis |
| `analyze_climate_nlp_fixed.py` | NLP analysis (corrected version) |
| `analyze_climate_nlp.py` | NLP analysis (original) |
| `analyze_geonames_features.py` | GeoNames feature analysis |
| `analyze_nlp_ontology_alignment.py` | Ontology alignment analysis |
| `analyze_opensearch_usage.py` | OpenSearch usage analysis |
| `diagnose_search_methods.py` | Search method diagnostics |

### **`/scripts/deployment/`** - Deployment & Infrastructure
Scripts for deploying components and managing infrastructure.

| Script | Purpose |
|--------|---------|
| `cleanup_serverless_opensearch.py` | Clean up serverless OpenSearch |
| `create_opensearch_domain_revised.py` | Create OpenSearch domain (revised) |
| `create_opensearch_domain.py` | Create OpenSearch domain |
| `deploy_admin_ontology_manager.py` | Deploy admin ontology manager |
| `deploy_gaip_api.py` | Deploy GAIP API |
| `deploy_proper_search.py` | Deploy proper search functionality |
| `deploy_real_search.py` | Deploy real search implementation |
| `deploy_simple.py` | Simple deployment script |
| `deploy_solution_ingestion.py` | Deploy solution ingestion pipeline |
| `deploy_test_webapp.sh` | Deploy test webapp |
| `fix_api_gateway.py` | Fix API Gateway configuration |
| `fix_opensearch_roles.py` | Fix OpenSearch role configurations |
| `generate_api_keys.py` | Generate API keys |
| `generate_jwt_token.py` | Generate JWT tokens for testing |
| `opensearch_managed_config.py` | OpenSearch managed configuration |
| `setup_cognito_accounts.py` | Setup Cognito accounts |
| `setup_gaip_cognito_account.py` | Setup GAIP Cognito account |

### **`/scripts/testing/`** - Testing & Validation
Scripts for testing system components and validating functionality.

| Script | Purpose |
|--------|---------|
| `invoke_pipeline_batches.py` | Batch pipeline testing |
| `invoke_pretest_cleanup.py` | Pre-test cleanup operations |
| `test_admin_ontology_manager.py` | Test admin ontology manager |
| `test_api.py` | Test API functionality |
| `test_document_reconstruction.py` | Test document reconstruction |
| `test_enhanced_search.py` | Test enhanced search functionality |
| `test_filters.py` | Test search filters |
| `test_multi_ontology_basic.py` | Test multi-ontology operations |
| `test_neptune_fts_integration.py` | Test Neptune FTS integration |
| `test_opensearch_access.py` | Test OpenSearch access |
| `test_sns_notifications.py` | Test SNS notifications |
| `test_solution_ingestion.py` | Test solution ingestion |
| `test_sparql_data.py` | Test SPARQL data operations |
| `test_vpc_fix.py` | Test VPC fixes |
| `verify_sns_config.py` | Verify SNS configuration |

### **`/scripts/utilities/`** - One-off Utilities & Fixes
General utility scripts and one-time fixes.

| Script | Purpose |
|--------|---------|
| `backfill_document_hashes.py` | Backfill document hashes |
| `check_neptune_loads.py` | Check Neptune load status |
| `convert_rdf_to_turtle.py` | Convert RDF to Turtle format |
| `fix_geonames_namespace.py` | Fix GeoNames namespace issues |
| `fix_geonames_trailing_slashes.py` | Fix GeoNames URI trailing slashes |
| `fix_import_issue.py` | Fix import issues |
| `fix_initialization.py` | Fix initialization problems |
| `fix_lambda_imports.py` | Fix Lambda import issues |
| `fix_method_name.py` | Fix method name issues |
| `fix_search_code.py` | Fix search code issues |
| `organize_scripts.py` | Script organization utility |
| `solution_ingestion_utility.py` | Solution ingestion utilities |
| `update_bulk_load_threshold.py` | Update bulk load threshold |
| `update_code_only.py` | Update code only |
| `update_kg_triple_loader_cdk.py` | Update KG triple loader CDK |
| `update_lambda_opensearch_config.py` | Update Lambda OpenSearch config |
| `update_search_code.py` | Update search code |

### **`/scripts/geonames/`** - GeoNames Processing
Scripts specifically for processing GeoNames data and geographic information.

| Script | Purpose |
|--------|---------|
| `create_geonames_sample.py` | Create GeoNames sample datasets |
| `examine_geonames.py` | Examine GeoNames data structure |
| `filter_geonames_adm4.py` | Filter GeoNames ADM4 data |
| `load_country_data_chunked_fixed.py` | Load country data (fixed version) |
| `load_country_data_chunked.py` | Load country data in chunks |
| `load_country_data_via_lambda.py` | Load country data via Lambda |
| `load_geonames_neptune_optimized.py` | Optimized GeoNames Neptune loading |
| `load_geonames_neptune.py` | Load GeoNames data to Neptune |
| `load_geonames_notebook_commands.py` | Jupyter notebook commands |
| `load_large_ttl_neptune.py` | Load large TTL files to Neptune |
| `load_ttl_to_neptune.py` | Load TTL files to Neptune |
| `load_ttl_via_lambda.py` | Load TTL via Lambda function |
| `load_ttl_via_sparql.py` | Load TTL via SPARQL |
| `process_geonames_rdf.py` | Process GeoNames RDF data |
| `split_and_load_countries.py` | Split and load country data |

### **`/scripts/proposals/`** - Historical Proposals & Prototypes
Prototype implementations and design proposals (historical reference).

| Script | Purpose |
|--------|---------|
| `contextual_entity_aligner_proposal.py` | Entity aligner design proposal |
| `contextual_scoring_engine_proposal.py` | Scoring engine design proposal |
| `entity_alignment_manager_proposal.py` | Alignment manager proposal |
| `fts_sparql_query_builder_proposal.py` | FTS query builder proposal |
| `integration_proposal.py` | System integration proposal |

### **Existing Directories** (Pre-organized)
- **`/scripts/database/`** - Database-related scripts and utilities
- **`/scripts/DEPRECATED/`** - Deprecated scripts (marked for removal)
- **`/scripts/infrastructure/`** - Infrastructure management scripts
- **`/scripts/lambda-updates/`** - Lambda function update scripts
- **`/scripts/maintenance/`** - System maintenance scripts
- **`/scripts/test-data/`** - Test data generation and management

## 🔍 Usage Guidelines

### **Frequently Used Scripts**
- **Main Testing**: Use `invoke_pipeline_test.py` from top level
- **Search Testing**: Use `scripts/testing/test_enhanced_search.py`
- **Data Analysis**: Use scripts in `scripts/analysis/` for exploration

### **Development Workflow**
1. **Testing**: Start with `scripts/testing/` for component validation
2. **Analysis**: Use `scripts/analysis/` for data exploration
3. **Utilities**: Use `scripts/utilities/` for one-off tasks
4. **Deployment**: Use `scripts/deployment/` for infrastructure changes

### **GeoNames Operations**
- All GeoNames-related scripts are in `scripts/geonames/`
- Use `load_geonames_neptune_optimized.py` for production loading
- Use `examine_geonames.py` for data exploration

### **Historical Reference**
- `scripts/proposals/` contains design prototypes and proposals
- `scripts/DEPRECATED/` contains scripts marked for removal
- These scripts may not be current but provide implementation context

## 📋 Maintenance Notes

### **Script Status**
- **Active**: Scripts in `analysis/`, `testing/`, `utilities/`, `deployment/`
- **Infrastructure**: Scripts in `deployment/`, `geonames/`, `infrastructure/`
- **Historical**: Scripts in `proposals/`, `DEPRECATED/`
- **Specialized**: Scripts in `database/`, `lambda-updates/`, `maintenance/`

### **Cleanup Considerations**
- Review `proposals/` and `DEPRECATED/` scripts for relevance
- Consolidate similar functionality in `utilities/`
- Update import paths if scripts reference moved files

### **Documentation**
- Each directory contains a README with specific details
- Update this table of contents when adding new scripts
- Reference the CODE_DEPRECATION_ANALYSIS document for cleanup guidance

---

**Last Updated**: 2025-11-20  
**Total Scripts Organized**: 60+ scripts across 10+ categories  
**Organization Status**: Complete - All top-level Python scripts organized
