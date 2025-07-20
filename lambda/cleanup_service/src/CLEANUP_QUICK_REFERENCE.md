# Cleanup Service Quick Reference

## Common Usage Patterns

### 1. Complete System Cleanup (Recommended)
```bash
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload '{
    "cleanup_scope": {
      "databases": {
        "postgresql": {
          "enabled": true,
          "tables": ["documents", "document_metadata", "document_processing_status"],
          "document_ids": []
        },
        "opensearch": {
          "enabled": true,
          "collections": ["solve-global-kr-vectors-v2", "solve-global-kr-search-v2"],
          "document_ids": []
        },
        "neptune": {"enabled": true}
      },
      "s3_data_lake": {
        "enabled": true,
        "buckets": ["solve-global-kr-dl-source-documents-861276078413-us-east-1"],
        "document_ids": [],
        "preserve_structure": true
      }
    },
    "safety_checks": {
      "require_confirmation": false,
      "dry_run": false,
      "max_documents_to_delete": 5000
    }
  }' \
  response.json
```

### 2. Dry Run (Always Run First!)
```bash
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload '{
    "cleanup_scope": {
      "databases": {
        "postgresql": {"enabled": true, "tables": ["documents", "document_metadata", "document_processing_status"]},
        "opensearch": {"enabled": true, "collections": ["solve-global-kr-vectors-v2", "solve-global-kr-search-v2"]},
        "neptune": {"enabled": true}
      },
      "s3_data_lake": {"enabled": true, "buckets": ["solve-global-kr-dl-source-documents-861276078413-us-east-1"]}
    },
    "safety_checks": {"dry_run": true, "max_documents_to_delete": 5000}
  }' \
  dry_run_response.json
```

### 3. Database Only Cleanup
```bash
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload '{
    "cleanup_scope": {
      "databases": {
        "postgresql": {
          "enabled": true,
          "tables": ["documents", "document_metadata", "document_processing_status"]
        },
        "opensearch": {"enabled": false},
        "neptune": {"enabled": false}
      },
      "s3_data_lake": {"enabled": false}
    },
    "safety_checks": {"dry_run": false}
  }' \
  db_cleanup_response.json
```

### 4. OpenSearch Only Cleanup
```bash
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload '{
    "cleanup_scope": {
      "databases": {
        "postgresql": {"enabled": false},
        "opensearch": {
          "enabled": true,
          "collections": ["solve-global-kr-search-v2"]
        },
        "neptune": {"enabled": false}
      },
      "s3_data_lake": {"enabled": false}
    },
    "safety_checks": {"dry_run": false}
  }' \
  opensearch_cleanup_response.json
```

### 5. Neptune Only Cleanup
```bash
aws lambda invoke \
  --function-name solve-global-kr-cleanup-service \
  --payload '{
    "cleanup_scope": {
      "databases": {
        "postgresql": {"enabled": false},
        "opensearch": {"enabled": false},
        "neptune": {"enabled": true}
      },
      "s3_data_lake": {"enabled": false}
    },
    "safety_checks": {"dry_run": false}
  }' \
  neptune_cleanup_response.json
```

## Expected Results

### Successful Complete Cleanup
```json
{
  "statusCode": 200,
  "body": {
    "success": true,
    "results": {
      "dry_run": false,
      "databases": {
        "postgresql": {
          "success": true,
          "records_affected": {
            "documents": 1007,
            "document_metadata": 1005,
            "document_processing_status": 27
          }
        },
        "opensearch": {
          "success": true,
          "documents_affected": {
            "solve-global-kr-vectors-v2": 0,
            "solve-global-kr-search-v2": 3
          }
        },
        "neptune": {
          "success": true,
          "triples_affected": 422
        }
      },
      "s3_data_lake": {
        "success": true,
        "total_objects_deleted": 1,
        "total_size_deleted": 1570490
      }
    },
    "cleanup_summary": {
      "overview": {
        "total_items_to_clean": 2465,
        "operations_count": 8,
        "estimated_impact": "HIGH"
      }
    }
  }
}
```

### Clean System (No Data to Clean)
```json
{
  "cleanup_summary": {
    "overview": {
      "total_items_to_clean": 0,
      "estimated_impact": "NONE"
    }
  }
}
```

## Verification Commands

### Check PostgreSQL
```sql
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM document_metadata;
SELECT COUNT(*) FROM document_processing_status;
-- All should return 0 after cleanup
```

### Check OpenSearch
```bash
# Check vector collection
curl -X GET "https://rui72a7agqnqo77vk34b.us-east-1.aoss.amazonaws.com/_cat/indices?format=json"

# Check search collection  
curl -X GET "https://i7dzyfap1fe42z9delui.us-east-1.aoss.amazonaws.com/_cat/indices?format=json"
# Should return empty array [] or indices with 0 docs.count
```

### Check Neptune
```sparql
SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }
-- Should return 0 after cleanup
```

### Check S3
```bash
aws s3 ls s3://solve-global-kr-dl-source-documents-861276078413-us-east-1/ --recursive
# Should return no objects
```

## Troubleshooting

### Common Issues & Solutions

#### "OpenSearch 404 errors"
- **Cause**: Collection or index doesn't exist
- **Solution**: This is normal - means already clean

#### "Neptune connection timeout"
- **Cause**: VPC/Security group issue
- **Solution**: Ensure Lambda uses security group `sg-0c043bcb40f656321`

#### "PostgreSQL connection failed"
- **Cause**: Database connectivity or credentials
- **Solution**: Check DATABASE_URL environment variable

#### "S3 access denied"
- **Cause**: IAM permissions
- **Solution**: Ensure cleanup role has s3:DeleteObject permissions

### Debug Commands

#### Check CloudWatch Logs
```bash
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/solve-global-kr-cleanup-service" \
  --order-by LastEventTime --descending --limit 1

aws logs get-log-events \
  --log-group-name "/aws/lambda/solve-global-kr-cleanup-service" \
  --log-stream-name "STREAM_NAME_FROM_ABOVE"
```

#### Test Lambda Function
```bash
aws lambda get-function --function-name solve-global-kr-cleanup-service
```

#### Check IAM Permissions
```bash
aws iam get-role-policy \
  --role-name CleanupServiceStack-CleanupServiceRole2E37FBF7-WsqIJNXJNz85 \
  --policy-name CleanupServicePolicy
```

## File Shortcuts

Save these as files for easy reuse:

### complete_cleanup.json
```json
{
  "cleanup_scope": {
    "databases": {
      "postgresql": {"enabled": true, "tables": ["documents", "document_metadata", "document_processing_status"]},
      "opensearch": {"enabled": true, "collections": ["solve-global-kr-vectors-v2", "solve-global-kr-search-v2"]},
      "neptune": {"enabled": true}
    },
    "s3_data_lake": {"enabled": true, "buckets": ["solve-global-kr-dl-source-documents-861276078413-us-east-1"]}
  },
  "safety_checks": {"dry_run": false, "max_documents_to_delete": 5000}
}
```

### dry_run.json
```json
{
  "cleanup_scope": {
    "databases": {
      "postgresql": {"enabled": true, "tables": ["documents", "document_metadata", "document_processing_status"]},
      "opensearch": {"enabled": true, "collections": ["solve-global-kr-vectors-v2", "solve-global-kr-search-v2"]},
      "neptune": {"enabled": true}
    },
    "s3_data_lake": {"enabled": true, "buckets": ["solve-global-kr-dl-source-documents-861276078413-us-east-1"]}
  },
  "safety_checks": {"dry_run": true}
}
```

### Usage
```bash
aws lambda invoke --function-name solve-global-kr-cleanup-service --payload fileb://dry_run.json response.json
aws lambda invoke --function-name solve-global-kr-cleanup-service --payload fileb://complete_cleanup.json response.json
```

## Success Indicators

### Complete Clean Slate Achieved When:
- ✅ PostgreSQL: All tables return COUNT(*) = 0
- ✅ OpenSearch: `_cat/indices` returns empty or 0 docs.count
- ✅ Neptune: `SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o }` returns 0
- ✅ S3: `aws s3 ls` returns no objects
- ✅ Cleanup response shows `"success": true` for all components
