# Comprehend Monitor - DEPRECATED

**Date Deprecated**: 2025-07-30  
**Reason**: Replaced with proper SNS-based event-driven architecture

## What This Was

The `comprehend-monitor` Lambda function was a **polling-based workaround** that:
- Ran every 2 minutes via EventBridge schedule
- Checked for recently completed Comprehend jobs
- Directly invoked `nlp-worker-entity` and `nlp-worker-keyphrase` functions

## Why It Was Needed (Originally)

This monitor existed because:
- Comprehend jobs were started **without** `NotificationConfig` parameter
- `comprehend-data-access-role` lacked SNS publish permissions
- Environment variables for SNS topic ARNs were missing
- No proper event-driven notification system was in place

## What Replaced It

**Proper SNS-based architecture**:
1. Comprehend jobs now include `NotificationConfig` with SNS topic ARNs
2. Jobs publish completion notifications to SNS topics
3. SNS topics deliver messages to SQS queues
4. NLP workers are triggered immediately via SQS event source mappings

## Architecture Comparison

### OLD (Polling-Based)
```
nlp-initiator → starts Comprehend jobs (no SNS)
                     ↓
comprehend-monitor (every 2 min) → polls → direct Lambda invocation
                     ↓
nlp-workers (delayed by up to 2 minutes)
```

### NEW (Event-Driven)
```
nlp-initiator → starts Comprehend jobs (with NotificationConfig)
                     ↓
Comprehend completes → SNS → SQS → nlp-workers (immediate)
```

## Resources Cleaned Up

- ✅ Lambda function: `comprehend-job-monitor` (deleted)
- ✅ EventBridge rule: `comprehend-job-monitor-schedule` (deleted)
- ✅ CloudWatch log group: `/aws/lambda/comprehend-job-monitor` (deleted)

## If Reversion Needed

If for any reason the SNS approach fails and this needs to be restored:

1. Deploy the `comprehend-monitor` Lambda from this directory
2. Create EventBridge rule to trigger it every 2 minutes
3. Temporarily disable SNS notifications in `nlp-initiator`
4. Investigate and fix the SNS issue
5. Re-enable SNS and remove monitor again

## Benefits of New Architecture

- ⚡ **Immediate processing** (no 2-minute delay)
- 💰 **Cost reduction** (no polling Lambda executions)
- 🏗️ **Architectural consistency** (event-driven like rest of pipeline)
- 🔄 **AWS best practices** (SNS/SQS pattern)
- 📊 **Better scalability** (handles concurrent jobs)
- 🛡️ **Built-in reliability** (SNS/SQS retry mechanisms)
