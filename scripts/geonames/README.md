# GeoNames Processing Scripts
**Purpose**: GeoNames data processing and geographic information management

## Scripts in this directory:
- `create_geonames_sample.py` - Create GeoNames sample datasets
- `examine_geonames.py` - Examine GeoNames data structure
- `filter_geonames_adm4.py` - Filter GeoNames ADM4 data
- `load_country_data_chunked_fixed.py` - Load country data (fixed version)
- `load_country_data_chunked.py` - Load country data in chunks
- `load_country_data_via_lambda.py` - Load country data via Lambda
- `load_geonames_neptune_optimized.py` - Optimized GeoNames Neptune loading
- `load_geonames_neptune.py` - Load GeoNames data to Neptune
- `load_geonames_notebook_commands.py` - Jupyter notebook commands
- `load_large_ttl_neptune.py` - Load large TTL files to Neptune
- `load_ttl_to_neptune.py` - Load TTL files to Neptune
- `load_ttl_via_lambda.py` - Load TTL via Lambda function
- `load_ttl_via_sparql.py` - Load TTL via SPARQL
- `process_geonames_rdf.py` - Process GeoNames RDF data
- `split_and_load_countries.py` - Split and load country data

## Usage:
These scripts handle all aspects of GeoNames data processing, from downloading and filtering to loading into Neptune. Use `load_geonames_neptune_optimized.py` for production loading.
