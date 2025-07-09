#!/usr/bin/env python3
"""
Update Lambda environment variables for standardized messaging
"""

import boto3
import time

def update_lambda_env_vars():
    """Update environment variables for all Lambda functions"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    env_updates = [
        {
            'function_name': 'solve-global-kr-textextractor-processor',
            'env_vars': {
                'TEXT_EXTRACTION_COMPLETE_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:text-extraction-complete',
                'STANDARDIZED_MESSAGING_ENABLED': 'true'
            }
        },
        {
            'function_name': 'text-chunker-pipeline',
            'env_vars': {
                'CHUNKS_READY_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:chunks-ready',
                'STANDARDIZED_MESSAGING_ENABLED': 'true'
            }
        },
        {
            'function_name': 'nlp-processor',
            'env_vars': {
                'NLP_WORKER_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:nlp-worker',
                'STANDARDIZED_MESSAGING_ENABLED': 'true'
            }
        },
        {
            'function_name': 'nlp-worker',
            'env_vars': {
                'NLP_COMPLETION_TOPIC_ARN': 'arn:aws:sns:us-east-1:861276078413:nlp-processing-complete',
                'STANDARDIZED_MESSAGING_ENABLED': 'true'
            }
        }
    ]
    
    successful_updates = 0
    
    for update in env_updates:
        try:
            # Get current environment
            current_config = lambda_client.get_function_configuration(FunctionName=update['function_name'])
            current_env = current_config.get('Environment', {}).get('Variables', {})
            
            # Merge with updates
            updated_env = {**current_env, **update['env_vars']}
            
            # Update environment variables
            lambda_client.update_function_configuration(
                FunctionName=update['function_name'],
                Environment={'Variables': updated_env}
            )
            
            print(f"✅ Updated environment variables for {update['function_name']}")
            successful_updates += 1
            
            # Small delay between updates
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error updating {update['function_name']}: {e}")
    
    print(f"\n📊 Environment Variable Updates: {successful_updates}/{len(env_updates)} successful")
    return successful_updates == len(env_updates)

if __name__ == "__main__":
    print("🔧 Updating Lambda environment variables for standardized messaging...")
    success = update_lambda_env_vars()
    
    if success:
        print("\n🎉 All environment variables updated successfully!")
        print("✅ Standardized messaging deployment is now complete")
    else:
        print("\n⚠️  Some environment variable updates failed")
    
    exit(0 if success else 1)
