def handler(event, context):
    """
    Lambda function handler for bulk_processor
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
