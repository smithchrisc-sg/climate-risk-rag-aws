# Lambda Layer Build Scripts

This directory contains scripts and tools for building AWS Lambda layers following best practices.

## Quick Start

```bash
# Build a layer locally
./build-layer.sh database-core-layer

# Build and deploy to AWS
./build-layer.sh database-core-layer --deploy --profile solve-global

# Build with custom description
./build-layer.sh database-core-layer --description "Database utilities v2.1" --deploy
```

## Files

- `build-layer.sh` - Main build script
- `layer-config.json` - Configuration for different layers
- `README.md` - This documentation

## Layer Structure Requirements

Each layer must follow this structure:

```
layers/
├── <layer-name>/
│   ├── python/              # Required: Python code directory
│   │   ├── utils/           # Your modules
│   │   ├── __init__.py      # Package initialization
│   │   └── ...              # Other Python files
│   └── requirements.txt     # Optional: pip dependencies
└── scripts/
    └── build-layer.sh       # Build script
```

## Build Script Features

### Core Functionality
- ✅ Validates layer structure
- ✅ Cleans Python cache files (`__pycache__`, `*.pyc`)
- ✅ Installs dependencies from `requirements.txt`
- ✅ Creates timestamped zip files
- ✅ Verifies zip contents
- ✅ Optional AWS deployment
- ✅ Colored output for better UX

### Best Practices Implemented
- **Clean builds**: Removes all cache and temporary files
- **Timestamped artifacts**: Each build gets a unique timestamp
- **Content verification**: Validates zip contents before deployment
- **Symlink to latest**: Always maintains a `*_latest.zip` symlink
- **Deployment tracking**: Saves deployment info as JSON
- **Error handling**: Comprehensive error checking and reporting

### Command Line Options

```bash
./build-layer.sh <layer-name> [OPTIONS]

OPTIONS:
    --deploy           Deploy the layer to AWS after building
    --profile PROFILE  AWS profile to use (default: default)
    --region REGION    AWS region (default: us-east-1)
    --force           Force rebuild even if layer exists
    --runtime RUNTIME  Compatible runtime (default: python3.11)
    --description DESC Layer description for AWS
    --help            Show help message
```

## Examples

### Basic Build
```bash
# Build database-core-layer locally
./build-layer.sh database-core-layer
```

### Build and Deploy
```bash
# Build and deploy with solve-global profile
./build-layer.sh database-core-layer --deploy --profile solve-global
```

### Custom Configuration
```bash
# Build with custom runtime and description
./build-layer.sh database-core-layer \
  --runtime python3.12 \
  --description "Database utilities with new features" \
  --deploy \
  --profile solve-global
```

## Build Process

1. **Validation**: Checks layer structure and required directories
2. **Cleanup**: Removes previous build artifacts and Python cache
3. **Preparation**: Copies source files to build directory
4. **Dependencies**: Installs packages from `requirements.txt` if present
5. **Packaging**: Creates zip file with proper exclusions
6. **Verification**: Validates zip contents and required files
7. **Deployment**: Optionally deploys to AWS Lambda

## Output Files

Build artifacts are stored in `../build/`:

```
build/
├── <layer-name>/                    # Build directory
│   └── python/                      # Prepared layer contents
├── <layer-name>_YYYYMMDD_HHMMSS.zip # Timestamped zip file
├── <layer-name>_latest.zip          # Symlink to latest build
└── <layer-name>_deployment.json     # Deployment info (if deployed)
```

## Verification

The script automatically verifies:

- Layer structure is correct
- Required files are present
- No cache files in the zip
- For `database-core-layer`: Validates `set_processing_status` method exists

## Configuration

Edit `layer-config.json` to customize:

- Layer descriptions
- Compatible runtimes
- AWS layer names
- Required methods for validation
- Build settings

## Troubleshooting

### Common Issues

1. **Missing python directory**
   ```
   ERROR: Layer must contain a 'python' directory
   ```
   Solution: Ensure your layer has a `python/` subdirectory

2. **AWS CLI not found**
   ```
   ERROR: AWS CLI is required for deployment
   ```
   Solution: Install AWS CLI and configure credentials

3. **Missing required methods**
   ```
   ERROR: DatabaseManager.py missing set_processing_status method
   ```
   Solution: Verify your source code has the required methods

### Debug Mode

Add `set -x` to the script for verbose debugging:

```bash
# Edit the script temporarily
sed -i '3i set -x' build-layer.sh
./build-layer.sh database-core-layer
```

## Best Practices

1. **Always test locally first**: Build without `--deploy` to verify
2. **Use descriptive commit messages**: Include what changed in the layer
3. **Version your layers**: Use semantic versioning in descriptions
4. **Clean builds**: The script handles this automatically
5. **Verify contents**: Check the zip file before deploying
6. **Use profiles**: Always specify `--profile` for production deployments

## Integration with CI/CD

The script is designed to work in CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Build and Deploy Layer
  run: |
    cd layers/scripts
    ./build-layer.sh database-core-layer \
      --deploy \
      --profile ${{ secrets.AWS_PROFILE }} \
      --description "Built from commit ${{ github.sha }}"
```

## Maintenance

- Review and update `layer-config.json` when adding new layers
- Update compatible runtimes as needed
- Monitor AWS layer version limits (1000 versions per layer)
- Clean up old build artifacts periodically
