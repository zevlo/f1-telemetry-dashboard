"""DynamoDB Streams → WebSocket fanout Lambda

Triggered by DynamoDB Streams on the Positions table.
Reads all active connections from Connections table and pushes
updated position data to each connected WebSocket client.
"""

import json


def lambda_handler(event, context):
    # TODO: Week 3 - Fan out DynamoDB stream events to WebSocket clients
    for record in event.get("Records", []):
        if record["eventName"] in ("INSERT", "MODIFY"):
            print(json.dumps(record["dynamodb"]))

    return {"statusCode": 200, "body": "pushed"}
