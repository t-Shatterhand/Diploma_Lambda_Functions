import json
import boto3


def lambda_handler(event, context):
    headers = event.get("headers")
    api_key = headers.get("x-api-key")

    dynamodb = boto3.client('dynamodb')

    dynamodb_record = dynamodb.get_item(
        Key={'api_key': {'S': str(api_key)}},
        TableName='Diploma_User_Table',
    )

    response = {}

    if 'Item' not in dynamodb_record:
        response['response'] = "You have no images deployed currently"
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(response)
        }

    port = dynamodb_record.get('Item').get('port').get('N')

    if port is None:
        response['response'] = "Your deployment is currently in process"
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(response)
        }

    response['response'] = "You have an image deployed by url loadbalancer.kostroba.pp.ua:" + str(port)

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response)
    }