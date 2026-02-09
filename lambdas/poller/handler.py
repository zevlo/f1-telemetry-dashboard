"""OpenF1 API Poller Lambda

Triggered by EventBridge every 5 seconds during active sessions.
Polls OpenF1 endpoints (/position, /car_data, /laps, /race_control, /weather)
and puts records into Kinesis Data Stream.
"""

import json


def lambda_handler(event, context):
    # TODO: Week 1 - Implement OpenF1 polling
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "poller stub"}),
    }
