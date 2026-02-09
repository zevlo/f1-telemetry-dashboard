"""WebSocket $disconnect handler

Removes connection ID from DynamoDB Connections table when a client disconnects.
"""

import json


def lambda_handler(event, context):
    # TODO: Week 3 - Remove connection_id from Connections table
    connection_id = event["requestContext"]["connectionId"]
    print(f"Disconnected: {connection_id}")

    return {"statusCode": 200, "body": "Disconnected"}
