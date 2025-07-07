#!/bin/bash
"""
Build Database Layer for AWS Lambda
Creates Linux-compatible psycopg2-binary layer
"""

echo "🔧 Building Database Layer for AWS Lambda"
echo "=========================================="

# Create layer directory
mkdir -p layers/build/database-layer/python

# Use Docker to build Linux-compatible psycopg2-binary
echo "Building psycopg2-binary for Linux x86_64..."

docker run --rm -v $(pwd)/layers/build/database-layer:/var/task \
  public.ecr.aws/lambda/python:3.11 \
  /bin/bash -c "pip install psycopg2-binary -t /var/task/python/"

if [ $? -eq 0 ]; then
    echo "✅ Database layer built successfully"
    echo "Contents:"
    ls -la layers/build/database-layer/python/
else
    echo "❌ Failed to build database layer with Docker"
    echo "Trying alternative approach..."
    
    # Alternative: Download pre-built psycopg2 for Lambda
    cd layers/build/database-layer/python
    
    # Download psycopg2 binary compatible with Lambda
    curl -L -o psycopg2.zip https://github.com/jkehler/awslambda-psycopg2/archive/refs/heads/master.zip
    unzip psycopg2.zip
    mv awslambda-psycopg2-master/psycopg2-3.11/* .
    rm -rf awslambda-psycopg2-master psycopg2.zip
    
    echo "✅ Alternative psycopg2 installation completed"
    ls -la
fi

echo "🎉 Database layer ready for deployment"
