# Lambda Layers for Climate Risk RAG System

This directory contains all artifacts for building, deploying, and managing Lambda layers.

## Directory Structure

```
layers/
├── requirements/           # Requirements files for each layer
├── build-scripts/         # Build automation scripts
├── infrastructure/        # CDK infrastructure code
├── management/           # Layer management tools
├── app-source/           # Application-specific source code
├── built-layers/         # Generated layer packages
└── tests/               # Layer testing utilities
```

## Quick Start

1. **Build all layers**: `./build-scripts/build-all-layers.sh`
2. **Deploy infrastructure**: `cd infrastructure && cdk deploy`
3. **Test layers**: `./tests/test-all-layers.sh`
4. **Manage layers**: Use tools in `management/` directory

## Layer Overview

- **Foundation Layers (1-8)**: Third-party dependencies
- **Application Layers (9-11)**: Shared application code
- **Total Size**: ~1.8GB across all layers
- **Functions Supported**: 17 Lambda functions
