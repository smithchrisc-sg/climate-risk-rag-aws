def handler(event, context):
    """
    Lambda function handler for query_handler
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
