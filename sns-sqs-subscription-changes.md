# SNS-SQS Subscription Changes

## Vector Embeddings Initiator Queue Subscriptions

Added subscription from text-chunking-complete SNS topic to vector-embeddings-initiator-queue:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:861276078413:text-chunking-complete \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:861276078413:vector-embeddings-initiator-queue
```

## SQS Queue Policy Updates

Updated the vector-embeddings-initiator-queue policy to allow messages from both SNS topics:

```json
{
  "Version": "2012-10-17",
  "Id": "AllowSNSToSendMessage",
  "Statement": [
    {
      "Sid": "AllowSNSToSendMessage",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:861276078413:vector-embeddings-initiator-queue",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": [
            "arn:aws:sns:us-east-1:861276078413:chunks-ready",
            "arn:aws:sns:us-east-1:861276078413:text-chunking-complete"
          ]
        }
      }
    }
  ]
}
```
