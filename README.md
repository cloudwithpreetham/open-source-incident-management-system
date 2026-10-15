# Project 8: Open-Source Incident Management System (IncidentFlow)

[![Elevate Labs DevOps Internship](https://img.shields.io/badge/Elevate_Labs-DevOps_Internship-blue.svg)](https://elevatelabs.tech)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)
[![Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)](#)

A production-grade, open-source Incident Management Portal engineered for Site Reliability Engineering (SRE) and DevOps teams to triage, assign, mitigate, and resolve critical infrastructure and application incidents.

---

## 📌 Project Overview & Objectives

- **Core Objective:** Build a lightweight, high-availability incident management portal to record and track production alerts, enforce MTTR (Mean Time to Resolution) visibility, assign on-call responders, and log immutable root cause analyses (RCA).
- **Role-Based Access Control (RBAC):** Supports `Admin`, `DevOps Engineer`, `SRE`, and `Viewer` personas.
- **Notification System:** Integrated SMTP email notifications with fallback event logging for zero downtime.
- **Observability Integration:** Built-in Prometheus `/api/v1/metrics` exporter for scraping incident gauges.

---

## 🏗️ Architecture & Technology Stack

```
   ┌──────────────────────────────────────────────────────────────┐
   │                    IncidentFlow Portal                       │
   │                                                              │
   │  ┌─────────────────────────┐     ┌────────────────────────┐  │
   │  │   Bootstrap 5 UI        │     │  REST API Endpoints    │  │
   │  │   - Ops Dashboard       │     │  - /api/v1/incidents   │  │
   │  │   - Incident Modals     │     │  - /api/v1/metrics     │  │
   │  │   - Audit Timeline      │     │  - /api/v1/assign      │  │
   │  └───────────┬─────────────┘     └───────────┬────────────┘  │
   │              │                               │               │
   │              └──────────────┬────────────────┘               │
   │                             ▼                                │
   │                  Flask Application Core                      │
   │                  (Controllers & Routing)                     │
   │                             │                                │
   │             ┌───────────────┴───────────────┐                │
   │             ▼                               ▼                │
   │    ┌──────────────────┐           ┌──────────────────┐       │
   │    │  SQLite Engine   │           │ Notification Hub │       │
   │    │ (Audit & State)  │           │  (SMTP & Alert)  │       │
   │    └──────────────────┘           └──────────────────┘       │
   └──────────────────────────────────────────────────────────────┘
```

- **Backend:** Python 3.11+ / Flask
- **Database:** SQLite with foreign keys & WAL journaling
- **Frontend:** Responsive Bootstrap 5, Bootstrap Icons, Jinja2
- **Containerization:** Docker multi-stage build, Docker Compose
- **Testing:** Pytest automated integration test suite

---

## 🚀 Quickstart Guide

### 1. Local Setup (Without Docker)

```powershell
# Navigate into the project directory
cd "d:\Elevate Labs\Projects\project-8-incident-management"

# Install required dependencies
pip install -r requirements.txt

# Seed the database with sample production incidents
python seed_data.py

# Launch the portal
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

### 2. Running with Docker & Docker Compose

```bash
docker-compose up --build -d
```

- **Incident Portal:** [http://localhost:5000](http://localhost:5000)
- **Mailpit Web UI (Email Inbox):** [http://localhost:8025](http://localhost:8025)

---

## 📡 REST API Specification

| Method | Endpoint                         | Description                                                         |
| ------ | -------------------------------- | ------------------------------------------------------------------- |
| `GET`  | `/api/v1/health`                 | Service health status check                                         |
| `GET`  | `/api/v1/incidents`              | List all incidents (supports `?status=`, `?severity=`, `?service=`) |
| `POST` | `/api/v1/incidents`              | Create a new incident                                               |
| `GET`  | `/api/v1/incidents/<id>`         | Get incident details & timeline logs                                |
| `POST` | `/api/v1/incidents/<id>/assign`  | Assign incident to an engineer                                      |
| `POST` | `/api/v1/incidents/<id>/resolve` | Resolve incident with RCA notes                                     |
| `GET`  | `/api/v1/metrics`                | Prometheus metrics scrape target                                    |

---

## 🧪 Automated Testing

Run the test suite using `pytest`:

```powershell
pytest -v
```

---

## 📝 Pre-Seeded Sample Incidents

1. **#1 - P1 Critical:** API Gateway 504 Gateway Timeout Spikes (`api-gateway-prod`) - _Resolved_
2. **#2 - P2 High:** Kubernetes Ingress SSL/TLS Certificate Expiration Warning (`k8s-ingress-controller`) - _Mitigated_
3. **#3 - P1 Critical:** Payment Microservice Pod CrashLoopBackOff (`payment-service`) - _Investigating_
4. **#4 - P3 Medium:** High Disk Space Utilization on ElasticSearch Data Node 03 (`logging-elasticsearch`) - _Open_
5. **#5 - P3 Medium:** Nightly Backup CronJob Failed to Upload to S3 (`postgres-backup-cron`) - _Resolved_
