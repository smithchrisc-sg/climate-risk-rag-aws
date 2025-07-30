# IAM Policy Changes

## document-processing-lambda-role Policy Updates

Added OpenSearch Serverless permissions to the document-processing-lambda-role policy:

```json
{
    "Effect": "Allow",
    "Action": [
        "aoss:*"
    ],
    "Resource": [
        "arn:aws:aoss:us-east-1:861276078413:collection/*"
    ]
}
```

## OpenSearch Serverless Access Policy Updates

Updated the kr-vectors-v2-data-access policy to use broader permissions:

```json
{
  "Rules": [
    {
      "Resource": ["index/solve-global-kr-vectors-v2/*"],
      "Permission": ["aoss:*"],
      "ResourceType": "index"
    },
    {
      "Resource": ["collection/solve-global-kr-vectors-v2"],
      "Permission": ["aoss:*"],
      "ResourceType": "collection"
    }
  ],
  "Principal": [
    "arn:aws:iam::861276078413:role/document-processing-lambda-role",
    "arn:aws:iam::861276078413:role/vector-embeddings-pipelin-VectorEmbeddingsWorkerSer-RUmUT934UY9t",
    "arn:aws:iam::861276078413:role/CleanupServiceStack-CleanupServiceRole2E37FBF7-WsqIJNXJNz85"
  ]
}
```
