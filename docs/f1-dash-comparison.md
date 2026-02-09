# f1-dash.com vs. F1 Telemetry Dashboard — Competitive Analysis

**Date:** 2026-02-09
**Source:** https://f1-dash.com | https://github.com/slowlydev/f1-dash

---

## What f1-dash.com Is

An open-source (~1,700 GitHub stars) real-time F1 live timing dashboard built by a solo dev (Slowlydev). Connects directly to F1's official live timing feed and displays race data in a clean dark-themed UI. Currently on v4.0.2, AGPL-3.0 licensed, in maintenance mode.

---

## Tech Stack Comparison

| | **f1-dash.com** | **This Project** |
|---|---|---|
| **Frontend** | Next.js (SSR) + TypeScript | React + Vite (SPA) |
| **Backend** | Rust microservices | Python Lambdas (serverless) |
| **Real-time** | SignalR (WebSockets) | API Gateway WebSocket API |
| **Data source** | F1 official live timing feed | OpenF1 API (free, public) |
| **Infrastructure** | Docker + Kubernetes | AWS serverless (Kinesis, DynamoDB, Lambda) |
| **IaC** | Kubernetes manifests | Terraform (modular) |
| **CI/CD** | GitHub Actions | GitHub Actions |
| **Hosting** | Self-hosted (K8s) | S3 + CloudFront |

---

## Feature Comparison

| Feature | **f1-dash** | **This Project** |
|---------|:-----------:|:----------------:|
| Live position tower | Yes | Planned (Week 4) |
| Lap times / sector times | Yes | Planned (Week 4) |
| Tire compound indicators | Yes | Planned (compound data sourcing TBD) |
| Track map with car positions | Approximate (minisectors) | Stretch goal (AWS Location Service) |
| Weather widget | Yes | Planned |
| Race control feed (flags) | Yes | Planned (Week 4) |
| Team radio | Basic | Not planned |
| Championship standings | Yes | Not planned |
| Historical analytics | Yes (multiple dashboards) | Stretch goal (S3 data lake + Glue) |
| Speed/throttle/brake telemetry | No (paywalled by F1) | Planned via OpenF1 `/car_data` |
| Sentiment analysis (NLP) | No | Stretch goal (Comprehend) |
| CloudWatch observability | N/A | Planned (Week 5) |
| Replay/simulator mode | Yes | Not yet planned (should add) |

---

## Key Similarities

1. **Same core goal** — real-time race dashboard with position tower, lap times, flags, weather
2. **WebSocket-based real-time push** to connected browser clients
3. **Open source** with GitHub Actions CI/CD
4. **Dark-themed dashboard UI** with color-coded timing data

---

## Key Differences

1. **Data source is the biggest difference.** f1-dash connects to F1's official timing feed (higher fidelity but legally gray). This project uses OpenF1's free public API — fewer restrictions but lower resolution and some missing data (tire compounds).

2. **Architecture philosophy.** f1-dash is traditional microservices on Kubernetes (Rust + Next.js). This project is fully serverless on AWS — the architecture itself is the portfolio piece, demonstrating Kinesis, Lambda, DynamoDB, API Gateway patterns that transfer to defense/enterprise work.

3. **f1-dash can't show detailed car telemetry** (speed, throttle, brake, DRS) because F1 paywalled that data. The OpenF1-based approach *can* via `/car_data` — this is an advantage.

4. **This project has an observability story** (CloudWatch dashboards, alarms, X-Ray) that f1-dash doesn't emphasize. This matters for interviews.

5. **IaC depth.** f1-dash has K8s manifests. This project has modular Terraform with full deploy/destroy lifecycle — stronger story for DevOps roles.

6. **f1-dash has a simulator** for testing without a live session. This project will need the same — replaying historical OpenF1 data during non-race weekends.

---

## Takeaways for This Project

| Insight | Action |
|---------|--------|
| Telemetry advantage | Lean into `/car_data` (speed, throttle, brake, gear, DRS) as a differentiator — f1-dash can't show this |
| Tire compound gap | Neither project has a clean source. Investigate FastF1 Python library as a supplement |
| Replay/simulator mode | Add to build plan — needed for demos and dev during non-race weekends |
| Architecture IS the demo | f1-dash is a better consumer product; this project tells a stronger infrastructure story. Different purposes |
| f1-dash architecture reference | Study their SignalR real-time pattern and minisector track map approach for inspiration |
