# CLAUDE.md

## Project Overview

Real-time F1 telemetry dashboard built on AWS serverless architecture. Ingests live race data from the OpenF1 API during race weekends and displays car positions, speeds, lap times, and session status via a React dashboard with WebSocket real-time updates.

## Architecture Pattern

Event-driven, serverless pipeline:
- **Ingestion**: EventBridge (5s schedule) → Lambda poller → Kinesis Data Stream
- **Processing**: Kinesis → Lambda transformer → DynamoDB
- **Delivery**: DynamoDB Streams → Lambda → WebSocket API Gateway (real-time push)
- **Historical**: REST API Gateway → Lambda → DynamoDB (query)
- **Frontend**: React (Vite) → S3 + CloudFront

## Repository Structure

- `terraform/` — Modular Terraform (ingestion, processing, storage, api, frontend, monitoring)
- `terraform/environments/dev/` — Dev environment configuration
- `lambdas/` — Python Lambda functions (poller, transformer, api_sessions, api_drivers, ws_connect, ws_disconnect, ws_push)
- `frontend/` — React + Vite dashboard
- `scripts/` — Local dev utilities (API exploration)
- `.github/workflows/` — CI/CD (deploy-infra.yml, deploy-frontend.yml)

## Code Conventions

- **Terraform**: main.tf / variables.tf / outputs.tf per module, AWS provider ~> 5.0
- **Lambda runtime**: Python 3.11+, handler function named `lambda_handler`
- **Lambda dependencies**: requirements.txt per function directory
- **Frontend**: React + Vite, no CSS framework decided yet
- **IAM**: Least privilege, one role per Lambda function
- **Tags**: All resources tagged with Project, Environment, ManagedBy

## Data Source

OpenF1 API (https://api.openf1.org/v1) — free tier, 3 req/s, 30 req/min.
Key endpoints: /sessions, /position, /car_data, /laps, /pit, /race_control, /weather, /drivers

## Build Order

Week 1: Ingestion → Week 2: Processing + Storage → Week 3: API → Week 4: Frontend → Week 5: Monitoring → Week 6: Polish

Each week follows: Console-first → Terraform-after → Break-it

## When Helping with This Project

- Follow the modular Terraform pattern (don't put everything in one file)
- Lambda functions should be small and single-purpose
- DynamoDB access patterns drive key design (see f1-telemetry-dashboard.md in the dev/ repo for full data model)
- Prefer on-demand DynamoDB capacity for dev
- Always include CORS headers in API Lambda responses
- Use environment variables for table names, stream ARNs — never hardcode
