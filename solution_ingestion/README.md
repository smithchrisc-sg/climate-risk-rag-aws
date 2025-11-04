# Solution Ingestion Utility

CLI application to ingest solutions from CSV into GAIP Knowledge Repository system.

## Quick Start

1. **Deploy**: `./deploy.sh`
2. **Run**: `python3 main.py --csv-path input_data/solutions.csv`

## Directory Structure

- `config/` - Environment configuration
- `models/` - Data models (Solution, IngestionResult)
- `parsers/` - CSV and data parsing
- `generators/` - Content generation (pseudo-docs, chunks, triples)
- `indexers/` - OpenSearch indexing (keyword, vector)
- `processors/` - Database and Neptune operations
- `layers/` - Clean copies of production layer code
- `input_data/` - CSV input files
- `output_data/` - Local data lake output for debugging

## Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
OPENSEARCH_ENDPOINT=https://vpc-solve-global-kr-search-*.us-east-1.es.amazonaws.com
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=veqpat-kegba2-zapbyZ
NEPTUNE_ENDPOINT=solve-global-kr-neptune-cluster.cluster-*.neptune.amazonaws.com
AWS_REGION=us-east-1
```

## Data Flow

CSV → Solution Objects → PostgreSQL + OpenSearch + Neptune + Data Lake Files
