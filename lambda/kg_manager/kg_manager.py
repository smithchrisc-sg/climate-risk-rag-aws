def handler(event, context):
    """
    Lambda function handler for kg_manager
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
