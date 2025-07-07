def handler(event, context):
    """
    Lambda function handler for graph_updater
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
