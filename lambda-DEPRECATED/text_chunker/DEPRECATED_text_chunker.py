def handler(event, context):
    """
    Lambda function handler for text_chunker
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
