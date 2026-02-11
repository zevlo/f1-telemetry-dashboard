"""OpenF1 API Poller Lambda

Triggered by EventBridge every 1 minute. Runs an internal loop of 11 cycles
(every 5 seconds) to poll OpenF1 endpoints and put records into Kinesis.

State (cursors, session_key) is persisted in SSM Parameter Store between cycles.
"""

import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import boto3
import requests

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
OPENF1_BASE_URL = os.environ.get("OPENF1_BASE_URL", "https://api.openf1.org/v1")
KINESIS_STREAM_NAME = os.environ.get("KINESIS_STREAM_NAME", "")
SSM_PARAM_NAME = os.environ.get("SSM_PARAM_NAME", "/f1-telemetry/dev/poller-state")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "5"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

POLL_INTERVAL = 5  # seconds between cycles
CYCLES_PER_INVOCATION = 11  # ~55s of a 60s EventBridge window
RATE_LIMIT_DELAY = 0.35  # seconds between API calls (stays under 3 req/s)
SESSION_GRACE_PERIOD_MINUTES = 5  # keep polling after session ends

logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Endpoint polling configuration
# tier: "high" = every cycle, "medium" = every 3rd, "low" = every 6th
ENDPOINT_CONFIGS = {
    "position": {
        "path": "/position",
        "tier": "high",
        "date_field": "date",
        "partition_key_field": "driver_number",
        "downsample": False,
    },
    "car_data": {
        "path": "/car_data",
        "tier": "high",
        "date_field": "date",
        "partition_key_field": "driver_number",
        "downsample": True,
    },
    "laps": {
        "path": "/laps",
        "tier": "medium",
        "date_field": "date_start",
        "partition_key_field": "driver_number",
        "downsample": False,
    },
    "race_control": {
        "path": "/race_control",
        "tier": "low",
        "date_field": "date",
        "partition_key_field": None,
        "downsample": False,
    },
    "weather": {
        "path": "/weather",
        "tier": "low",
        "date_field": "date",
        "partition_key_field": None,
        "downsample": False,
    },
    "pit": {
        "path": "/pit",
        "tier": "low",
        "date_field": "date",
        "partition_key_field": "driver_number",
        "downsample": False,
    },
}


# ──────────────────────────────────────────────
# AWS Client Singletons (warm start reuse)
# ──────────────────────────────────────────────
_kinesis_client = None
_ssm_client = None


def get_kinesis_client():
    global _kinesis_client
    if _kinesis_client is None:
        _kinesis_client = boto3.client("kinesis")
    return _kinesis_client


def get_ssm_client():
    global _ssm_client
    if _ssm_client is None:
        _ssm_client = boto3.client("ssm")
    return _ssm_client


# ──────────────────────────────────────────────
# State Management
# ──────────────────────────────────────────────
def load_state(ssm_client, param_name):
    """Load polling state from SSM Parameter Store."""
    try:
        response = ssm_client.get_parameter(Name=param_name)
        return json.loads(response["Parameter"]["Value"])
    except ssm_client.exceptions.ParameterNotFound:
        return None
    except Exception:
        logger.exception("Failed to load state from SSM")
        return None


def save_state(ssm_client, param_name, state):
    """Persist polling state to SSM Parameter Store."""
    try:
        ssm_client.put_parameter(
            Name=param_name,
            Value=json.dumps(state),
            Type="String",
            Overwrite=True,
        )
    except Exception:
        logger.exception("Failed to save state to SSM")


def get_initial_state(session_key):
    """Create fresh state for a new session."""
    return {
        "session_key": str(session_key),
        "invocation_count": 0,
        "cursors": {},
    }


# ──────────────────────────────────────────────
# OpenF1 API
# ──────────────────────────────────────────────
def detect_active_session():
    """Check for an active F1 session.

    Returns (session_key, session_data) if active, (None, None) if not.
    """
    try:
        resp = requests.get(
            f"{OPENF1_BASE_URL}/sessions",
            params={"session_key": "latest"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to fetch sessions")
        return None, None

    sessions = resp.json()
    if not sessions:
        return None, None

    session = sessions[0]
    session_key = session["session_key"]

    # Check if session ended more than GRACE_PERIOD ago
    date_end = session.get("date_end")
    if date_end:
        try:
            end_dt = datetime.fromisoformat(date_end)
            now = datetime.now(timezone.utc)
            if (now - end_dt) > timedelta(minutes=SESSION_GRACE_PERIOD_MINUTES):
                logger.info(
                    "Session %s ended at %s (>%dm ago). No active session.",
                    session_key,
                    date_end,
                    SESSION_GRACE_PERIOD_MINUTES,
                )
                return None, None
        except ValueError:
            pass  # If we can't parse date_end, treat session as active

    return session_key, session


def fetch_endpoint(endpoint_name, session_key, cursor=None):
    """Fetch new records from an OpenF1 endpoint since the cursor timestamp.

    Returns list of records on success, None on failure.
    """
    config = ENDPOINT_CONFIGS[endpoint_name]
    params = {"session_key": session_key}

    if cursor:
        date_field = config["date_field"]
        params[f"{date_field}>"] = cursor

    try:
        resp = requests.get(
            f"{OPENF1_BASE_URL}{config['path']}",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 429:
            logger.warning("Rate limited on %s", endpoint_name)
            return "rate_limited"

        resp.raise_for_status()
        records = resp.json()

        if not isinstance(records, list):
            logger.warning("Unexpected response type from %s: %s", endpoint_name, type(records))
            return None

        return records

    except requests.RequestException:
        logger.exception("Failed to fetch %s", endpoint_name)
        return None


def fetch_drivers(session_key):
    """Fetch driver list for a session (one-time per session)."""
    try:
        resp = requests.get(
            f"{OPENF1_BASE_URL}/drivers",
            params={"session_key": session_key},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        logger.exception("Failed to fetch drivers")
        return None


# ──────────────────────────────────────────────
# Data Processing
# ──────────────────────────────────────────────
def downsample_car_data(records):
    """Keep one record per driver per 1-second bucket.

    Groups by driver_number, truncates timestamp to second precision,
    and keeps the last record in each bucket.
    """
    buckets = defaultdict(dict)

    for record in records:
        driver = record.get("driver_number")
        date_str = record.get("date", "")
        if not driver or not date_str:
            continue
        # Truncate to second precision: "2025-12-07T13:50:12"
        bucket_key = date_str[:19]
        buckets[driver][bucket_key] = record

    result = []
    for driver_records in buckets.values():
        result.extend(driver_records.values())
    return result


def advance_cursor(records, date_field="date"):
    """Return the maximum date string from returned records."""
    if not records:
        return None
    dates = [r[date_field] for r in records if r.get(date_field)]
    return max(dates) if dates else None


# ──────────────────────────────────────────────
# Kinesis
# ──────────────────────────────────────────────
def build_kinesis_records(endpoint_name, session_key, records):
    """Wrap raw API records in the Kinesis envelope format.

    Each Kinesis record contains:
    - endpoint: the source endpoint name
    - session_key: the F1 session
    - ingested_at: poller-side timestamp
    - data: the raw OpenF1 record
    """
    config = ENDPOINT_CONFIGS.get(endpoint_name, {})
    pk_field = config.get("partition_key_field")
    now = datetime.now(timezone.utc).isoformat()

    kinesis_records = []
    for record in records:
        envelope = {
            "endpoint": endpoint_name,
            "session_key": session_key,
            "ingested_at": now,
            "data": record,
        }
        partition_key = str(record.get(pk_field, "global")) if pk_field else "global"

        kinesis_records.append({
            "Data": json.dumps(envelope).encode("utf-8"),
            "PartitionKey": partition_key,
        })

    return kinesis_records


def build_kinesis_records_oneshot(endpoint_name, session_key, records):
    """Build Kinesis records for one-time endpoints (sessions, drivers)."""
    now = datetime.now(timezone.utc).isoformat()
    kinesis_records = []
    for record in records:
        envelope = {
            "endpoint": endpoint_name,
            "session_key": session_key,
            "ingested_at": now,
            "data": record,
        }
        pk = str(record.get("driver_number", "global"))
        kinesis_records.append({
            "Data": json.dumps(envelope).encode("utf-8"),
            "PartitionKey": pk,
        })
    return kinesis_records


def put_records_batch(kinesis_client, stream_name, records):
    """Send records to Kinesis in batches of up to 500.

    Returns total number of successfully sent records.
    """
    if not records:
        return 0

    total_sent = 0
    for i in range(0, len(records), 500):
        chunk = records[i : i + 500]
        try:
            response = kinesis_client.put_records(
                StreamName=stream_name,
                Records=chunk,
            )
            failed = response.get("FailedRecordCount", 0)
            if failed > 0:
                logger.warning(
                    "Kinesis PutRecords: %d/%d failed", failed, len(chunk)
                )
            total_sent += len(chunk) - failed
        except Exception:
            logger.exception("Kinesis PutRecords failed for batch starting at %d", i)

    return total_sent


# ──────────────────────────────────────────────
# Orchestration
# ──────────────────────────────────────────────
def select_endpoints(invocation_count):
    """Choose which endpoints to poll this cycle based on rotation schedule."""
    endpoints = []
    for name, config in ENDPOINT_CONFIGS.items():
        tier = config["tier"]
        if tier == "high":
            endpoints.append(name)
        elif tier == "medium" and invocation_count % 3 == 0:
            endpoints.append(name)
        elif tier == "low" and invocation_count % 6 == 0:
            endpoints.append(name)
    return endpoints


def run_poll_cycle(state):
    """Execute a single poll cycle. Mutates state in place.

    Returns the number of records sent to Kinesis.
    """
    session_key = state["session_key"]
    count = state["invocation_count"]
    cursors = state["cursors"]

    endpoints = select_endpoints(count)
    logger.info(
        "Cycle %d: polling %s for session %s",
        count,
        endpoints,
        session_key,
    )

    all_kinesis_records = []

    for endpoint_name in endpoints:
        config = ENDPOINT_CONFIGS[endpoint_name]
        date_field = config["date_field"]
        cursor = cursors.get(endpoint_name)

        result = fetch_endpoint(endpoint_name, session_key, cursor)

        # Rate limited — stop polling remaining endpoints this cycle
        if result == "rate_limited":
            logger.warning("Rate limited — skipping remaining endpoints this cycle")
            break

        # Fetch failed — skip but don't advance cursor
        if result is None:
            continue

        records = result

        if not records:
            continue

        # Downsample car_data
        if config["downsample"]:
            original_count = len(records)
            records = downsample_car_data(records)
            logger.info(
                "%s: downsampled %d → %d records",
                endpoint_name,
                original_count,
                len(records),
            )

        # Build Kinesis records
        kinesis_records = build_kinesis_records(endpoint_name, session_key, records)
        all_kinesis_records.extend(kinesis_records)

        # Advance cursor to max date in returned records
        new_cursor = advance_cursor(records, date_field)
        if new_cursor:
            cursors[endpoint_name] = new_cursor

        # Rate limit spacing between API calls
        time.sleep(RATE_LIMIT_DELAY)

    # Flush to Kinesis
    total_sent = 0
    if all_kinesis_records and KINESIS_STREAM_NAME:
        kinesis = get_kinesis_client()
        total_sent = put_records_batch(kinesis, KINESIS_STREAM_NAME, all_kinesis_records)

    logger.info("Cycle %d: sent %d records to Kinesis", count, total_sent)

    state["invocation_count"] = count + 1
    return total_sent


def lambda_handler(event, context):
    """Entry point. Runs CYCLES_PER_INVOCATION poll cycles (~55s)."""
    ssm = get_ssm_client()
    state = load_state(ssm, SSM_PARAM_NAME)

    # Detect active session
    session_key, session_data = detect_active_session()
    if session_key is None:
        logger.info("No active session. Exiting.")
        return {"statusCode": 200, "body": json.dumps({"message": "no active session"})}

    session_changed = False

    if state is None or str(state.get("session_key")) != str(session_key):
        # First run or session changed — initialize fresh state
        logger.info("New session detected: %s", session_key)
        state = get_initial_state(session_key)
        session_changed = True

    # On new session: send session metadata and driver list as one-time records
    if session_changed and KINESIS_STREAM_NAME:
        kinesis = get_kinesis_client()
        oneshot_records = []

        # Session data
        if session_data:
            oneshot_records.extend(
                build_kinesis_records_oneshot("sessions", session_key, [session_data])
            )

        # Driver data
        time.sleep(RATE_LIMIT_DELAY)
        drivers = fetch_drivers(session_key)
        if drivers:
            oneshot_records.extend(
                build_kinesis_records_oneshot("drivers", session_key, drivers)
            )

        if oneshot_records:
            sent = put_records_batch(kinesis, KINESIS_STREAM_NAME, oneshot_records)
            logger.info("Sent %d one-time records (session + drivers)", sent)

    # Run poll cycles
    total_records = 0
    for cycle in range(CYCLES_PER_INVOCATION):
        total_records += run_poll_cycle(state)
        save_state(ssm, SSM_PARAM_NAME, state)

        if cycle < CYCLES_PER_INVOCATION - 1:
            time.sleep(POLL_INTERVAL)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "session_key": session_key,
            "cycles": CYCLES_PER_INVOCATION,
            "total_records_sent": total_records,
        }),
    }
