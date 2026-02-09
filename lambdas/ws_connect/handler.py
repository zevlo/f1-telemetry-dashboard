"""WebSocket $connect handler

Stores connection ID in DynamoDB Connections table when a client connects.
"""

import json


def lambda_handler(event, context):
    # TODO: Week 3 - Store connection_id in Connections table
    connection_id = event["requestContext"]["connectionId"]
    print(f"Connected: {connection_id}")

    return {"statusCode": 200, "body": "Connected"}
