"""REST API - GET /sessions and GET /sessions/{id}

Queries DynamoDB Sessions table and returns session metadata.
"""

import json


def lambda_handler(event, context):
    # TODO: Week 3 - Query DynamoDB Sessions table
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"message": "sessions stub"}),
    }
