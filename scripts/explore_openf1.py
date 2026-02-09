#!/usr/bin/env python3
"""OpenF1 API Explorer

Run this locally to understand the data shapes before building Lambda functions.
Usage: python3 scripts/explore_openf1.py
"""

import json
import urllib.request
import urllib.error

BASE_URL = "https://api.openf1.org/v1"

ENDPOINTS = [
    "/sessions?year=2025&session_type=Race",
    "/drivers?session_key=latest",
    "/position?session_key=latest&driver_number=1",
    "/car_data?session_key=latest&driver_number=1",
    "/laps?session_key=latest&driver_number=1",
    "/race_control?session_key=latest",
    "/weather?session_key=latest",
    "/pit?session_key=latest",
]


def fetch(endpoint):
    """Fetch an endpoint and return parsed JSON."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"GET {url}")
    print("=" * 60)

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            count = len(data) if isinstance(data, list) else 1
            print(f"Records returned: {count}")

            # Show first record as a sample
            if isinstance(data, list) and len(data) > 0:
                print(f"\nSample record keys: {list(data[0].keys())}")
                print(f"\nFirst record:")
                print(json.dumps(data[0], indent=2))
            elif isinstance(data, dict):
                print(json.dumps(data, indent=2))

            return data

    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return None


def main():
    print("OpenF1 API Explorer")
    print("Exploring data shapes for F1 Telemetry Dashboard\n")

    for endpoint in ENDPOINTS:
        fetch(endpoint)
        print()

    print("\nDone! Review the output above to understand each endpoint's data shape.")
    print("These shapes will inform your DynamoDB table design and Lambda transformers.")


if __name__ == "__main__":
    main()
