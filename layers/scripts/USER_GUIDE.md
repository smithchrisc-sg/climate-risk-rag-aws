# Layer Build Scripts - User Guide

## Quick Start

### Build a Layer Locally
```bash
cd /Users/chris/climate-risk-rag-aws/layers/scripts
./build-layer-simple.sh database-core-layer
```

### Build and Deploy to AWS
```bash
./build-layer-simple.sh database-core-layer --deploy --profile solve-global
```

## Available Scripts

- **`build-layer-simple.sh`** - Production-ready build script (recommended)
- **`build-layer.sh`** - Advanced script with more features (experimental)

## Command Options

```bash
./build-layer-simple.sh <layer-name> [OPTIONS]

OPTIONS:
  --deploy           Deploy to AWS after building
  --profile PROFILE  AWS profile to use (default: default)
  --help            Show help message
```

## What the Script Does

1. ✅ Validates layer structure (`python/` directory exists)
2. ✅ Cleans previous builds and Python cache files
3. ✅ Creates timestamped zip file
4. ✅ Verifies required methods exist (for database-core-layer)
5. ✅ Optionally deploys to AWS Lambda
6. ✅ Creates `*_latest.zip` symlink for easy access

## Output Files

Build artifacts are stored in `../build/`:
```
build/
├── database-core-layer_YYYYMMDD_HHMMSS.zip  # Timestamped build
├── database-core-layer_latest.zip           # Symlink to latest
└── database-core-layer_deployment.json      # AWS deployment info
```

## Layer Requirements

Your layer must have this structure:
```
layers/
└── <layer-name>/
    └── python/          # Required directory
        ├── utils/       # Your Python modules
        └── ...
```

## Examples

### Database Core Layer
```bash
# Build only
./build-layer-simple.sh database-core-layer

# Build and deploy with solve-global profile
./build-layer-simple.sh database-core-layer --deploy --profile solve-global
```

### OpenSearch Layer
```bash
# Build opensearch layer
./build-layer-simple.sh opensearch-layer --deploy --profile solve-global
```

## Verification

The script automatically verifies:
- Layer structure is correct
- No Python cache files in zip
- For `database-core-layer`: `set_processing_status` method exists

## Troubleshooting

### Common Issues

**Layer directory not found**
```
[ERROR] Layer directory not found: /path/to/layer
```
→ Check layer name spelling and ensure directory exists

**Missing python directory**
```
[ERROR] Layer must contain a 'python' directory
```
→ Create `python/` subdirectory in your layer

**AWS CLI not found**
```
[ERROR] AWS CLI is required for deployment
```
→ Install AWS CLI and configure credentials

**Missing required method**
```
[ERROR] DatabaseManager.py missing set_processing_status method
```
→ Verify your source code has the required methods

### Getting Help
```bash
./build-layer-simple.sh --help
```

## Best Practices

1. **Always test locally first** - Build without `--deploy` to verify
2. **Use descriptive names** - Layer names should be clear and consistent
3. **Verify contents** - Check the zip file before deploying to production
4. **Use profiles** - Always specify `--profile` for production deployments
5. **Clean builds** - The script handles this automatically

## Current Production Layer

- **Name**: `database-core-layer`
- **Latest Version**: 12
- **ARN**: `arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:12`
- **Status**: ✅ Verified with `set_processing_status` method

## Updating Lambda Functions

After deploying a new layer version, update your Lambda functions:
```bash
aws lambda update-function-configuration \
  --function-name your-function-name \
  --layers arn:aws:lambda:us-east-1:861276078413:layer:database-core-layer:12 \
  --profile solve-global
```

---

**Need more details?** See `README.md` for comprehensive documentation.
