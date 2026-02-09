"""REST API - GET /drivers/{id}

Queries DynamoDB for driver-specific data (positions, laps, telemetry).
"""

import json


def lambda_handler(event, context):
    # TODO: Week 3 - Query DynamoDB for driver data
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"message": "drivers stub"}),
    }
