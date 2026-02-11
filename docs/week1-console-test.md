# Week 1: Console-First Testing — Poller Lambda

Test the poller Lambda by manually creating AWS resources in the console, deploying the function, and verifying records flow into Kinesis. Terraform codifies this later.

---

## Prerequisites

- AWS account with console access
- AWS CLI v2 configured (`aws sts get-caller-identity` succeeds)
- Python 3.11+ locally (for packaging the Lambda zip)
- Region: `us-east-1` (or adjust all commands below)

---

## Step 1: Create the Kinesis Data Stream

1. Go to **Kinesis** → **Data streams** → **Create data stream**
2. Configure:
   - Stream name: `f1-telemetry-dev-ingest`
   - Capacity mode: **On-demand** (no shard management, scales automatically, fine for dev)
3. Click **Create data stream**
4. Wait for status: **Active**

**CLI alternative:**

```bash
aws kinesis create-stream \
  --stream-name f1-telemetry-dev-ingest \
  --stream-mode-summary StreamMode=ON_DEMAND \
  --region us-east-1
```

---

## Step 2: Create the SSM Parameter

1. Go to **Systems Manager** → **Parameter Store** → **Create parameter**
2. Configure:
   - Name: `/f1-telemetry/dev/poller-state`
   - Tier: **Standard**
   - Type: **String**
   - Value: `{}`
3. Click **Create parameter**

**CLI alternative:**

```bash
aws ssm put-parameter \
  --name "/f1-telemetry/dev/poller-state" \
  --type String \
  --value "{}" \
  --region us-east-1
```

---

## Step 3: Create the IAM Role

1. Go to **IAM** → **Roles** → **Create role**
2. Trusted entity: **AWS service** → **Lambda**
3. Attach these policies:

**Option A: Managed policies (quick but broad)**

- `AWSLambdaBasicExecutionRole` (CloudWatch Logs)

Then add an **inline policy** named `f1-poller-access`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KinesisWrite",
      "Effect": "Allow",
      "Action": "kinesis:PutRecords",
      "Resource": "arn:aws:kinesis:us-east-1:ACCOUNT_ID:stream/f1-telemetry-dev-ingest"
    },
    {
      "Sid": "SSMState",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:PutParameter"
      ],
      "Resource": "arn:aws:ssm:us-east-1:ACCOUNT_ID:parameter/f1-telemetry/dev/poller-state"
    }
  ]
}
```

Replace `ACCOUNT_ID` with your AWS account ID (`aws sts get-caller-identity --query Account --output text`).

4. Role name: `f1-telemetry-dev-poller-role`
5. Click **Create role**

---

## Step 4: Package the Lambda

From the project root:

```bash
cd lambdas/poller

# Create a temp build directory
rm -rf _build && mkdir _build

# Install dependencies into the build dir
pip install -r requirements.txt -t _build/

# Copy the handler
cp handler.py _build/

# Create the zip
cd _build
zip -r ../poller.zip .
cd ..

# Clean up
rm -rf _build

echo "Created lambdas/poller/poller.zip"
ls -lh poller.zip
```

The zip should be ~1-3 MB (mostly the `requests` library).

---

## Step 5: Create the Lambda Function

1. Go to **Lambda** → **Create function**
2. Configure:
   - Function name: `f1-telemetry-dev-poller`
   - Runtime: **Python 3.11**
   - Architecture: **arm64** (cheaper, faster for I/O-bound work)
   - Execution role: **Use an existing role** → `f1-telemetry-dev-poller-role`
3. Click **Create function**
4. In the **Code** tab → **Upload from** → **.zip file** → upload `poller.zip`
5. In **Runtime settings** → **Edit**:
   - Handler: `handler.lambda_handler`
6. In **Configuration** tab:

**General configuration → Edit:**
- Memory: **256 MB**
- Timeout: **1 min 5 sec** (65 seconds — allows 11 cycles of 5s + overhead)

**Environment variables → Edit:**

| Key | Value |
|-----|-------|
| `KINESIS_STREAM_NAME` | `f1-telemetry-dev-ingest` |
| `SSM_PARAM_NAME` | `/f1-telemetry/dev/poller-state` |
| `LOG_LEVEL` | `INFO` |

Leave `OPENF1_BASE_URL` and `REQUEST_TIMEOUT` unset (defaults are fine).

---

## Step 6: First Test — Short Run

Before letting the Lambda run all 11 cycles (~55s), do a quick smoke test. Temporarily override the cycle count by adding an environment variable:

| Key | Value |
|-----|-------|
| `CYCLES_OVERRIDE` | `1` |

> **Note:** The handler doesn't read this variable yet. For a quick test, just invoke it and cancel after ~10s using the console, or set the timeout to **15 seconds** temporarily to force it to stop after 1-2 cycles.

**Alternative — set timeout to 15s, invoke, then check:**

1. Set timeout to **15 seconds**
2. Go to **Test** tab → create test event:

```json
{}
```

Event name: `manual-test`

3. Click **Test**
4. Check the **Execution result** tab for the response and logs

**What to look for in the logs:**

```
No active session. Exiting.
```

This is expected if there's no live F1 session right now. That means session detection works.

If there IS an active session (during a race weekend), you'll see:

```
New session detected: 9839
Sent 21 one-time records (session + drivers)
Cycle 0: polling ['position', 'car_data', 'laps', 'race_control', 'weather', 'pit'] for session 9839
Cycle 0: sent 147 records to Kinesis
```

5. **Restore timeout to 65 seconds** after testing

---

## Step 7: Verify Kinesis Records

If the poller sent records (active session), check the Kinesis stream:

**Option A: Console Data Viewer**

1. Go to **Kinesis** → **f1-telemetry-dev-ingest** → **Data viewer** tab
2. Shard: pick any shard
3. Starting position: **Trim horizon** (read from beginning)
4. Click **Get records**
5. Expand a record — you should see the envelope:

```json
{
  "endpoint": "car_data",
  "session_key": 9839,
  "ingested_at": "2025-12-07T13:50:15.123456+00:00",
  "data": {
    "driver_number": 1,
    "speed": 312,
    "rpm": 11200,
    ...
  }
}
```

**Option B: CLI**

```bash
# Get the shard iterator
SHARD_ID=$(aws kinesis list-shards \
  --stream-name f1-telemetry-dev-ingest \
  --query 'Shards[0].ShardId' \
  --output text \
  --region us-east-1)

ITERATOR=$(aws kinesis get-shard-iterator \
  --stream-name f1-telemetry-dev-ingest \
  --shard-id "$SHARD_ID" \
  --shard-iterator-type TRIM_HORIZON \
  --query 'ShardIterator' \
  --output text \
  --region us-east-1)

# Read records
aws kinesis get-records \
  --shard-iterator "$ITERATOR" \
  --limit 5 \
  --region us-east-1 \
  --query 'Records[].Data' \
  --output text | while read b64; do
    echo "$b64" | base64 -d | python3 -m json.tool
  done
```

---

## Step 8: Verify SSM State

Check that the poller persisted its cursor state:

```bash
aws ssm get-parameter \
  --name "/f1-telemetry/dev/poller-state" \
  --query 'Parameter.Value' \
  --output text \
  --region us-east-1 | python3 -m json.tool
```

Expected (after at least one successful cycle):

```json
{
  "session_key": "9839",
  "invocation_count": 1,
  "cursors": {
    "position": "2025-12-07T13:50:12.000000+00:00",
    "car_data": "2025-12-07T13:50:12.000000+00:00"
  }
}
```

---

## Step 9: Full Run (During Active Session)

If testing during a race weekend:

1. Restore timeout to **65 seconds**
2. Invoke the function and let it run to completion
3. Check logs in **CloudWatch** → **Log groups** → `/aws/lambda/f1-telemetry-dev-poller`
4. Verify all 11 cycles ran:
   - Cycles 0, 6: all 6 endpoints polled
   - Cycles 3, 9: position + car_data + laps
   - Other cycles: position + car_data only
5. Check Kinesis Data Viewer for a spread of endpoint types
6. Check SSM state shows advancing cursor timestamps

---

## Step 10: Break-It Testing

Once the happy path works, try these failure scenarios:

| Test | How | Expected behavior |
|------|-----|-------------------|
| **No active session** | Invoke when no race is happening | Logs "No active session. Exiting." Returns 200 |
| **Kinesis stream deleted** | Delete the stream, invoke | Logs Kinesis errors, does NOT crash. Cursors still advance (data lost but poller recovers) |
| **SSM parameter deleted** | Delete the parameter, invoke | Creates fresh state from scratch on next successful cycle |
| **API timeout** | Set `REQUEST_TIMEOUT=1` env var | Some endpoints may timeout. Logs errors, skips those endpoints, polls the rest |
| **Rate limiting** | Set `RATE_LIMIT_DELAY=0` env var | May trigger HTTP 429. Logs warning, skips remaining endpoints that cycle |
| **Invalid stream name** | Set `KINESIS_STREAM_NAME=nonexistent` | Kinesis PutRecords fails. Logs error. Cursors still advance |

---

## Cleanup

When done testing, delete the console-created resources (Terraform will recreate them properly):

```bash
# Delete Lambda
aws lambda delete-function \
  --function-name f1-telemetry-dev-poller \
  --region us-east-1

# Delete Kinesis stream
aws kinesis delete-stream \
  --stream-name f1-telemetry-dev-ingest \
  --region us-east-1

# Delete SSM parameter
aws ssm delete-parameter \
  --name "/f1-telemetry/dev/poller-state" \
  --region us-east-1

# Delete IAM role (must remove inline policies first)
aws iam delete-role-policy \
  --role-name f1-telemetry-dev-poller-role \
  --policy-name f1-poller-access

aws iam detach-role-policy \
  --role-name f1-telemetry-dev-poller-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam delete-role \
  --role-name f1-telemetry-dev-poller-role

# Delete the zip
rm lambdas/poller/poller.zip
```

---

## What's Next

After console testing validates the poller:
1. **Terraform the ingestion module** — codify Kinesis, Lambda, EventBridge (1-min rate), IAM, SSM into `terraform/modules/ingestion/`
2. **Wire up dev environment** — uncomment module call in `terraform/environments/dev/main.tf`
3. **Add EventBridge rule** — schedule the Lambda every 1 minute
4. **Break-it round 2** — test with Terraform-managed resources
