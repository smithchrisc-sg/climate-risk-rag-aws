def handler(event, context):
    """
    Lambda function handler for entity_extractor
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
