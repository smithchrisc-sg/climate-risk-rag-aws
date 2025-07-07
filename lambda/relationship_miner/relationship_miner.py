def handler(event, context):
    """
    Lambda function handler for relationship_miner
    """
    print(f"Processing event: {event}")
    return {
        'statusCode': 200,
        'body': 'Function executed successfully'
    }
