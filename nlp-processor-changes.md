# NLP Processor Changes

## SQS Queue and Event Source Mapping

Created a new SQS queue for the NLP processor:

```bash
aws sqs create-queue \
  --queue-name nlp-processor-queue \
  --attributes '{
    "VisibilityTimeout": "300",
    "MessageRetentionPeriod": "86400"
  }'
```

Created a dead-letter queue for the NLP processor:

```bash
aws sqs create-queue \
  --queue-name nlp-processor-dlq \
  --attributes '{
    "MessageRetentionPeriod": "1209600"
  }'
```

Configured the NLP processor queue with the DLQ:

```bash
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/861276078413/nlp-processor-queue \
  --attributes '{
    "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:861276078413:nlp-processor-dlq\",\"maxReceiveCount\":5}"
  }'
```

## SNS Subscription

Subscribed the NLP processor queue to the text-chunking-complete SNS topic:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:861276078413:text-chunking-complete \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:861276078413:nlp-processor-queue
```

Updated the SQS queue policy for the NLP processor queue:

```bash
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/861276078413/nlp-processor-queue \
  --attributes '{
    "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"sqs:SendMessage\",\"Resource\":\"arn:aws:sqs:us-east-1:861276078413:nlp-processor-queue\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"arn:aws:sns:us-east-1:861276078413:text-chunking-complete\"}}}]}"
  }'
```

## IAM Role Updates

Added SQS permissions to the NLP processor Lambda role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes",
                "sqs:ChangeMessageVisibility"
            ],
            "Resource": "arn:aws:sqs:us-east-1:861276078413:nlp-processor-queue"
        }
    ]
}
```

## Event Source Mapping

Created an event source mapping for the NLP processor Lambda:

```bash
aws lambda create-event-source-mapping \
  --function-name nlp-processor \
  --event-source-arn arn:aws:sqs:us-east-1:861276078413:nlp-processor-queue \
  --batch-size 1
```

## Code Changes

1. Updated the NLP processor to handle SQS-wrapped SNS messages
2. Added logic to derive the text location from the chunks location
3. Fixed the path construction to look for raw_text.txt in the text bucket
