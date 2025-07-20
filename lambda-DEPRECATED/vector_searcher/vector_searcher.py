def handler(event, context):
    """
    Lambda function handler for vector_searcher
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
