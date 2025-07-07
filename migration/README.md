# Climate Risk RAG - Migration Scripts (NER-Based Approach)

This directory contains scripts for migrating climate risk documents from local storage to AWS S3, using a **NER-based sampling approach** to ensure data consistency and quality.

## 🔄 Updated Approach (NER-Based)

**Key Change:** We now base our sampling on documents that have completed NER processing, ensuring all selected documents have gone through the complete processing pipeline.

### Why NER-Based Sampling?
- **Data Consistency:** All sampled documents have corresponding files in every processing stage
- **Quality Assurance:** NER completion indicates successful full pipeline processing  
- **Realistic Scope:** Based on actual processed documents (~5K) rather than metadata estimates
- **Cost Accuracy:** Better cost estimates based on real processed data

## 📁 Correct Folder Structure

```
/Volumes/G-RAID Photo 24TB/climate_risk_rag/
├── data/
│   ├── raw/                    # PDFs (source documents)
│   ├── processed/
│   │   └── text/              # Extracted text files
│   ├── chunks/                # Document chunks (by doc_id folders)
│   ├── embeddings/            # Vector embeddings (by doc_id folders)
│   └── ner_results/           # NER results (5K files - our sampling base)
```

## 🛠️ Core Migration Scripts

### **NER-Based Scripts (Current)**
- **`generate_sample_selection_ner.py`** - Generates stratified sample based on NER results
- **`selective_migration_ner.py`** - Migrates only the selected sample documents and artifacts
- **`validate_sample_ner.py`** - Validates the quality and representativeness of NER-based samples

### **Legacy Scripts (Deprecated)**
- **`generate_sample_selection.py`** - Original metadata-based sampling (inconsistent results)
- **`selective_migration.py`** - Original migration script (path issues)
- **`validate_sample.py`** - Original validation script

## 🚀 Usage Instructions

### 1. Generate NER-Based Sample

```bash
python generate_sample_selection_ner.py \
  --local-path "/Volumes/G-RAID Photo 24TB/climate_risk_rag" \
  --sample-size 1000 \
  --strategy balanced \
  --output sample_documents_1000_ner.json
```

**Parameters:**
- `--local-path`: Path to your local climate risk data
- `--sample-size`: Number of documents to sample (default: 1000)
- `--strategy`: Sampling strategy (`balanced` or `diverse`)
- `--output`: Output JSON file for sample selection
- `--min-completeness`: Minimum completeness score (default: 0.8)

### 2. Validate Sample Quality

```bash
python validate_sample_ner.py \
  --sample-file sample_documents_1000_ner.json \
  --report sample_validation_report.json
```

**Parameters:**
- `--sample-file`: Sample selection JSON file to validate
- `--local-path`: Path to local data (optional, can be read from sample file)
- `--report`: Output validation report file

### 3. Run Selective Migration

```bash
python selective_migration_ner.py \
  --local-path "/Volumes/G-RAID Photo 24TB/climate_risk_rag" \
  --documents-bucket "solve-global-kr-documents-861276078413-us-west-2" \
  --chunks-bucket "solve-global-kr-chunks-861276078413-us-west-2" \
  --embeddings-bucket "solve-global-kr-embeddings-861276078413-us-west-2" \
  --ner-results-bucket "solve-global-kr-ner-861276078413-us-west-2" \
  --extracted-text-bucket "solve-global-kr-text-861276078413-us-west-2" \
  --region us-west-2 \
  --profile solve-global \
  --sample-file sample_documents_1000_ner.json \
  --max-workers 4
```

**Parameters:**
- `--local-path`: Path to your local climate risk data
- `--*-bucket`: S3 bucket names for different data types
- `--region`: AWS region
- `--profile`: AWS profile name
- `--sample-file`: Sample selection JSON file
- `--max-workers`: Number of concurrent upload threads
- `--dry-run`: Perform dry run without actual uploads

## 📊 Expected Data Volumes (NER-Based)

**Total Available (5K NER-processed documents):**
- Documents: 5,000 PDFs (~15GB)
- Chunks: ~1.4M files (~40GB)
- Embeddings: ~1.4M files (~45GB)
- Text files: 5,000 files (~250MB)
- NER results: 5,000 files (~25MB)

**Sample (1K documents):**
- Documents: 1,000 PDFs (~3GB)
- Chunks: ~280K files (~8GB)
- Embeddings: ~280K files (~9GB)
- Text files: 1,000 files (~50MB)
- NER results: 1,000 files (~5MB)
- **Total sample: ~20GB**

## 💰 Cost Estimates (Updated)

**One-time Migration Costs:**
- Textract processing: ~$15 (1,000 documents)
- Lambda executions: ~$5
- Data transfer: ~$5
- **Total setup: ~$25**

**Monthly Operational Costs:**
- S3 storage (20GB): ~$0.50
- OpenSearch: ~$8
- Neptune: ~$7
- RDS: ~$3
- Lambda: ~$2
- **Total monthly: ~$20**

## 🔍 Sample Quality Metrics

The NER-based approach provides better quality metrics:

- **Completeness Score:** Percentage of processing stages completed
- **File Availability:** Actual file existence across all stages
- **Size Distribution:** Balanced representation of document sizes
- **Type Diversity:** Coverage of different document types
- **Processing Balance:** Even distribution across processing dates

## 🛡️ Data Validation

Each sample undergoes comprehensive validation:

1. **Structure Validation:** Correct JSON format and required fields
2. **Distribution Validation:** Balanced representation across dimensions
3. **Coverage Validation:** Adequate file availability (>80% per stage)
4. **Quality Validation:** Overall quality score and recommendations

## 📋 Migration Process

1. **Sample Generation:** Create representative sample from NER results
2. **Sample Validation:** Ensure quality and representativeness
3. **Infrastructure Setup:** Deploy S3 buckets and AWS resources
4. **Selective Migration:** Upload only sampled documents and artifacts
5. **Migration Validation:** Verify successful upload and data integrity

## 🔧 Troubleshooting

### Common Issues:

**"NER results directory not found"**
- Verify the correct path: `data/ner_results/`
- Ensure NER processing has been completed

**"Low file availability"**
- Some documents may not have completed all processing stages
- Adjust `--min-completeness` parameter to be more selective

**"Sample lacks diversity"**
- Increase `--sample-size` for better representation
- Use `diverse` strategy instead of `balanced`

### File Path Issues:
- Ensure folder structure matches the documented layout
- Check that document IDs are consistent across processing stages
- Verify file naming conventions match expected patterns

## 📈 Performance Optimization

- **Concurrent Uploads:** Use `--max-workers` to control parallelism
- **Dry Run Testing:** Always test with `--dry-run` first
- **Incremental Migration:** Can resume interrupted migrations
- **Error Handling:** Comprehensive error logging and recovery

## 🔄 Migration Workflow Integration

This NER-based approach integrates with the broader migration workflow:

1. **POC Analysis** → 2. **NER-Based Sampling** → 3. **AWS Migration** → 4. **Performance Comparison**

The NER-based sampling ensures that comparison testing between POC and AWS implementations uses consistent, high-quality data that has completed the full processing pipeline.
