import boto3
import json
import requests
import re


def dynamodb_delete(api_key):
    dynamodb = boto3.client('dynamodb')

    record_delete_response = dynamodb.delete_item(
        TableName='Diploma_User_Table',
        Key={'api_key': {'S': api_key}}
    )
    return record_delete_response


def create_response(text, status_code):
    response = {}
    response['statusCode'] = status_code
    response['headers'] = {'Content-Type': 'application/json'}
    response['body'] = json.dumps({"response": text})
    return response


def lambda_handler(event, context):
    headers = event.get("headers")
    api_key = headers.get("x-api-key")

    state_machine_arn = 'arn:aws:states:eu-north-1:123456789012:stateMachine:Diploma_Main_State_Function'

    dynamodb = boto3.client('dynamodb')

    dynamodb_record = dynamodb.get_item(
        Key={
            'api_key': {
                'S': str(api_key),
            },
        },
        TableName='Diploma_User_Table',
    )

    if dynamodb_record.get("Item") is not None:
        port = dynamodb_record["Item"].get("port", {}).get("N", "0")
        if port == "0":
            text = "Image is currently being deployed. Check /GET endpoint later to find out url"
        else:
            text = "Image deployment already exists by url loadbalancer.kostroba.pp.ua:" + port
        return create_response(text, 409)

    dynamodb.put_item(
        Item={
            'api_key':
                {'S': api_key}
        },
        TableName='Diploma_User_Table'
    )

    body = json.loads(event.get("body"))

    container_port = int(body["port"])
    deploy_time_secs = int(body.get("time", 60)) * 60
    variables = body.get("variables", {})
    image = body.get("image")
    namespace = body.get("namespace", "library")
    tag = body.get("tag", "latest")
    image_full_name = "{}/{}:{}".format(namespace, image, tag)

    if not re.match(r"^[a-zA-Z0-9_-]+$", namespace):
        dynamodb_delete(api_key)
        return create_response("Namespace is not a valid string", 400)

    if not re.match(r"^[a-zA-Z0-9_-]+$", image):
        dynamodb_delete(api_key)
        return create_response("Image name is not a valid string", 400)

    if not re.match(r"^[a-zA-Z0-9_-]+$", tag):
        dynamodb_delete(api_key)
        return create_response("Tag is not a valid string", 400)

    if type(variables) != type({}):
        dynamodb_delete(api_key)
        return create_response("Variables is not a dictionary", 400)

    if not all(type(value) == type("") for value in variables.values()):
        dynamodb_delete(api_key)
        return create_response("All variable values must be strings", 400)

    if not all(type(key) == type("") for key in variables.keys()):
        dynamodb_delete(api_key)
        return create_response("All variable keys must be strings", 400)

    docker_api_url = 'https://hub.docker.com/v2/namespaces/{}/repositories/{}/tags/{}'.format(namespace, image, tag)
    docker_api_resp_code = requests.head(docker_api_url).status_code

    if docker_api_resp_code == 404:
        dynamodb_delete(api_key)
        text = "No image can be found by name " + image_full_name
        return create_response(text, 404)

    if docker_api_resp_code == 403:
        dynamodb_delete(api_key)
        return create_response("Provided DockerHub image is private", 400)

    if docker_api_resp_code != 200:
        dynamodb_delete(api_key)
        return create_response("Something is wrong with DockerHub", 503)

    sf = boto3.client('stepfunctions')
    sf_input = {}
    sf_input['image'] = image_full_name
    sf_input['in_port'] = container_port
    sf_input['time'] = deploy_time_secs
    sf_input['api_key'] = api_key
    sf_input['variables'] = variables
    response = sf.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(sf_input)
    )

    answer = {}
    answer['response'] = "Your image " + image_full_name + " is being deployed. Check /GET endpoint to find out url"
    return {
        'statusCode': 201,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(answer)
    }
