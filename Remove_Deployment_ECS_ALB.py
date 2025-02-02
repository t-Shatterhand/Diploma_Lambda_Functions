import json
import boto3


def lambda_handler(event, context):
    ecs = boto3.client('ecs')
    elb = boto3.client('elbv2')
    dynamodb = boto3.client('dynamodb')

    cluster_arn = 'arn:aws:ecs:eu-north-1:123456789012:cluster/Diploma_cluster'

    is_service_active = True
    is_alb_active = True
    is_db_record_present = True

    dynamodb_record = dynamodb.get_item(
        TableName='Diploma_User_Table',
        Key={'api_key': {'S': event['api_key']}}
    )

    if 'Item' not in dynamodb_record:
        return {"message": "No db record found, aborting"}

    service_id = dynamodb_record.get('Item', "").get('service_id', "").get('S', "")

    if service_id == "":
        return {"message": "Not a full db record, aborting"}

    saved_service_id = event['service_id']

    if service_id != saved_service_id:  # means the user is same, but the service execution changed
        return {"message": "Execution id changed, aborting"}

    listener_arn = dynamodb_record['Item']['listener_arn']['S']
    target_group_arn = dynamodb_record['Item']['target_group_arn']['S']

    try:
        listener_delete_response = elb.delete_listener(ListenerArn=listener_arn)
    except Exception:
        is_alb_active = False

    try:
        target_group_delete_response = elb.delete_target_group(TargetGroupArn=target_group_arn)
    except Exception:
        is_alb_active = False

    try:
        service_delete_response = ecs.delete_service(
            cluster=cluster_arn,
            service=service_id,
            force=True
        )
    except Exception:
        is_service_active = False

    try:
        record_delete_response = dynamodb.delete_item(
            TableName='Diploma_User_Table',
            Key={'api_key': {'S': event['api_key']}}
        )
    except Exception:
        is_db_record_present = False

    response = {}
    response['message'] = "Execution successful"
    response['is_alb_deleted'] = is_alb_active
    response['is_service_deleted'] = is_service_active
    response['is_db_record_deleted'] = is_db_record_present

    return response
