# F1 Telemetry Dashboard

Real-time F1 telemetry visualization powered by AWS serverless architecture.

## Architecture

```
OpenF1 API → EventBridge → Lambda (Poller) → Kinesis → Lambda (Transformer) → DynamoDB
                                                                                  │
                                                              DynamoDB Streams → Lambda → WebSocket API → Dashboard
                                                                                  │
                                                              REST API Gateway → Lambda → DynamoDB (historical queries)
                                                                                  │
                                                              S3 + CloudFront → React Frontend
```

## Project Structure

```
├── terraform/          # Infrastructure as Code (modular)
├── lambdas/            # Python Lambda functions
├── frontend/           # React + Vite dashboard
├── scripts/            # Local development utilities
└── .github/workflows/  # CI/CD pipelines
```

## AWS Services

Lambda, DynamoDB, Kinesis Data Streams, API Gateway (REST + WebSocket), EventBridge, S3, CloudFront, CloudWatch

## Data Source

[OpenF1 API](https://openf1.org) - Free real-time F1 telemetry data

## Getting Started

```bash
# Explore the OpenF1 API data shapes
python3 scripts/explore_openf1.py

# Deploy infrastructure (after configuring AWS credentials)
cd terraform/environments/dev
terraform init && terraform plan && terraform apply

# Run frontend locally (after Week 4)
cd frontend
npm install && npm run dev
```

## Build Phases

1. **Week 1**: Ingestion pipeline (EventBridge → Lambda → Kinesis)
2. **Week 2**: Processing + storage (Kinesis → Lambda → DynamoDB)
3. **Week 3**: API layer (REST + WebSocket API Gateway)
4. **Week 4**: Frontend (React dashboard on S3 + CloudFront)
5. **Week 5**: Monitoring + hardening (CloudWatch, alarms, X-Ray)
6. **Week 6**: Polish + demo prep
