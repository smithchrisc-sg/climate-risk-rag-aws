# NLP Pipeline Setup

## Current Configuration

The NLP processing pipeline is set up with:

1. `nlp-processor` Lambda function (initiator)
2. `nlp-worker` Lambda function (processes results)
3. `nlp-worker-queue` SQS queue
4. Subscriptions:
   - `text-chunking-complete` SNS topic → `nlp-worker-queue` SQS queue
   - `nlp-worker` SNS topic → `nlp-worker-queue` SQS queue
5. Event source mapping:
   - `nlp-worker-queue` SQS queue → `nlp-worker` Lambda function

## Next Steps

1. Verify that the `nlp-processor` Lambda is correctly processing messages from the `text-chunking-complete` SNS topic
2. Ensure the IAM permissions are correctly set up for the NLP Lambda functions
3. Test the NLP pipeline with a sample document
4. Monitor the logs to ensure the pipeline is working correctly

## Similar to Vector Embeddings Pipeline

The NLP pipeline follows a similar pattern to the vector embeddings pipeline:
1. SNS topic for chunking completion
2. SQS queue for buffering messages
3. Lambda function for processing
