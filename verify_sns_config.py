#!/usr/bin/env python3
"""
Verify SNS Configuration for Comprehend Jobs
"""
import boto3
import json

def verify_configuration():
    """Verify that all components are properly configured for SNS notifications"""
    
    print("🔍 VERIFYING SNS CONFIGURATION FOR COMPREHEND JOBS")
    print("=" * 60)
    
    # Check Lambda environment variables
    lambda_client = boto3.client('lambda')
    try:
        response = lambda_client.get_function_configuration(FunctionName='nlp-initiator')
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        print("✅ Lambda Environment Variables:")
        entity_topic = env_vars.get('ENTITY_COMPLETION_TOPIC_ARN')
        keyphrase_topic = env_vars.get('KEYPHRASE_COMPLETION_TOPIC_ARN')
        
        if entity_topic:
            print(f"   - ENTITY_COMPLETION_TOPIC_ARN: {entity_topic}")
        else:
            print("   ❌ ENTITY_COMPLETION_TOPIC_ARN: Missing")
            
        if keyphrase_topic:
            print(f"   - KEYPHRASE_COMPLETION_TOPIC_ARN: {keyphrase_topic}")
        else:
            print("   ❌ KEYPHRASE_COMPLETION_TOPIC_ARN: Missing")
            
    except Exception as e:
        print(f"❌ Error checking Lambda config: {e}")
        return False
    
    # Check SNS topics exist
    sns_client = boto3.client('sns')
    topics_to_check = [
        'arn:aws:sns:us-east-1:861276078413:comprehend-entity-completion',
        'arn:aws:sns:us-east-1:861276078413:comprehend-keyphrase-completion'
    ]
    
    print("\n✅ SNS Topics:")
    for topic_arn in topics_to_check:
        try:
            sns_client.get_topic_attributes(TopicArn=topic_arn)
            print(f"   - {topic_arn.split(':')[-1]}: EXISTS")
        except Exception as e:
            print(f"   ❌ {topic_arn.split(':')[-1]}: {e}")
    
    # Check SQS subscriptions
    print("\n✅ SQS Subscriptions:")
    for topic_arn in topics_to_check:
        try:
            response = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
            subscriptions = response.get('Subscriptions', [])
            topic_name = topic_arn.split(':')[-1]
            
            if subscriptions:
                for sub in subscriptions:
                    endpoint = sub['Endpoint'].split(':')[-1]
                    print(f"   - {topic_name} → {endpoint}")
            else:
                print(f"   ❌ {topic_name}: No subscriptions")
                
        except Exception as e:
            print(f"   ❌ Error checking subscriptions for {topic_arn}: {e}")
    
    # Check IAM permissions
    iam_client = boto3.client('iam')
    print("\n✅ IAM Permissions:")
    try:
        response = iam_client.list_attached_role_policies(RoleName='comprehend-data-access-role')
        policies = response.get('AttachedPolicies', [])
        
        sns_policy_found = False
        for policy in policies:
            print(f"   - {policy['PolicyName']}")
            if 'sns' in policy['PolicyName'].lower():
                sns_policy_found = True
        
        if not sns_policy_found:
            print("   ⚠️  No SNS policy found - may need to check inline policies")
            
    except Exception as e:
        print(f"   ❌ Error checking IAM policies: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("1. Run a document through the pipeline")
    print("2. Check CloudWatch logs for nlp-initiator")
    print("3. Verify Comprehend jobs include NotificationConfig")
    print("4. Monitor SQS queues for SNS messages")
    print("5. If working, disable comprehend-monitor polling")

if __name__ == "__main__":
    verify_configuration()
