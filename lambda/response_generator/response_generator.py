def handler(event, context):
    """
    Lambda function handler for response_generator
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
