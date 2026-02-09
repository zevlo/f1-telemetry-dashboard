"""Kinesis to DynamoDB Transformer Lambda

Consumes records from Kinesis Data Stream, normalizes telemetry data
(speed, position, gaps), detects events (overtakes, pit stops, flags),
and writes to DynamoDB tables.
"""

import json


def lambda_handler(event, context):
    # TODO: Week 2 - Implement Kinesis consumer + DynamoDB writer
    for record in event.get("Records", []):
        payload = json.loads(
            __import__("base64").b64decode(record["kinesis"]["data"])
        )
        print(json.dumps(payload))

    return {"statusCode": 200, "body": "processed"}
