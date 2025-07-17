# Climate Risk RAG System

A Retrieval-Augmented Generation (RAG) system for climate risk document processing and analysis.

## Overview

The Climate Risk RAG system processes climate risk documents, extracts meaningful information, and makes it available for search and analysis. The system uses a serverless event-driven architecture on AWS to process documents through various stages including text extraction, chunking, embedding, and indexing.

## Architecture

![Climate Risk RAG Architecture](docs/architecture_diagram.png)

The system follows a serverless event-driven architecture:

1. **Document Ingestion**:
   - Documents are uploaded to S3
   - S3 event triggers the document processing pipeline

2. **Processing Pipeline**:
   - Text extraction Lambda extracts text from documents using AWS Textract
   - Text chunker Lambda splits text into semantic chunks using smart structured chunking
   - Keyword indexer Lambda extracts keywords from chunks
   - Vector embeddings Lambda creates embeddings for chunks
   - Knowledge graph Lambda builds relationships between entities

3. **Storage**:
   - S3 for raw documents, extracted text, and chunks
   - PostgreSQL for metadata and processing status
   - OpenSearch for vector search
   - Neptune for knowledge graph

## Key Features

- **Smart Structured Chunking**: Respects document structure and uses sentence-based overlap
- **Hybrid Search**: Combines keyword and vector search for better results
- **Knowledge Graph**: Extracts entities and relationships for advanced analysis
- **Serverless Architecture**: Scales automatically based on demand
- **Event-Driven Processing**: Processes documents asynchronously through multiple stages

## Getting Started

### Prerequisites

- AWS Account
- AWS CLI configured
- Python 3.11+
- Node.js 18+ (for CDK)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/climate-risk-rag-aws.git
   cd climate-risk-rag-aws
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   npm install
   ```

3. Deploy the infrastructure:
   ```
   cdk deploy --all
   ```

### Running Tests

To run the end-to-end pipeline test:

```
python run_test_with_cleanup.py
```

This will:
1. Clean up all data from previous tests
2. Select a test document
3. Run the pipeline on the test document
4. Verify the results at each stage

## Project Structure

- `cdk/`: AWS CDK infrastructure code
- `lambda/`: Lambda function code
  - `text_extraction/`: Text extraction Lambda
  - `text_chunker/`: Text chunking Lambda
  - `keyword_indexer/`: Keyword indexing Lambda
  - `vector_embeddings/`: Vector embeddings Lambda
  - `knowledge_graph/`: Knowledge graph Lambda
  - `shared_layer/`: Shared Lambda layer code
- `docs/`: Documentation
- `tests/`: Test code

## Documentation

- [Project Context](PROJECT_CONTEXT.md): Current status and context
- [Next Steps](NEXT_STEPS.md): Planned future work
- [API Documentation](docs/API.md): API documentation

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
