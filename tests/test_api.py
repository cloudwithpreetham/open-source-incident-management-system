import json
import os
import sys

import pytest

proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if proj_dir not in sys.path:
    sys.path.insert(0, proj_dir)

# Ensure fresh imports for Project 8
for mod_name in ['models', 'notifications', 'app', 'seed_data']:
    sys.modules.pop(mod_name, None)

os.environ["INCIDENT_DB_PATH"] = "test_incidents.db"
import app as flask_app
import models


@pytest.fixture
def client():
    # Use clean test database
    if os.path.exists("test_incidents.db"):
        os.remove("test_incidents.db")
    models.init_db()

    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as client:
        yield client

    if os.path.exists("test_incidents.db"):
        os.remove("test_incidents.db")

def test_health_check(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "healthy"

def test_create_and_get_incident(client):
    payload = {
        "title": "Database Read Replica Out of Sync",
        "description": "Replication lag exceeded 600s on replica-02",
        "service": "postgres-cluster",
        "severity": "P2 - High",
        "reporter_name": "Alertmanager",
        "reporter_email": "alerts@monitoring.internal"
    }
    create_res = client.post("/api/v1/incidents", json=payload)
    assert create_res.status_code == 201
    created_data = json.loads(create_res.data)
    inc_id = created_data["incident_id"]

    # Verify retrieval
    get_res = client.get(f"/api/v1/incidents/{inc_id}")
    assert get_res.status_code == 200
    incident = json.loads(get_res.data)
    assert incident["title"] == payload["title"]
    assert incident["status"] == "Open"
    assert len(incident["timeline"]) >= 1

def test_assign_and_resolve_incident(client):
    payload = {
        "title": "Ingress 502 Bad Gateway",
        "description": "Upstream backend connection refused",
        "service": "ingress-nginx",
        "severity": "P1 - Critical"
    }
    create_res = client.post("/api/v1/incidents", json=payload)
    inc_id = json.loads(create_res.data)["incident_id"]

    # Assign
    assign_res = client.post(f"/api/v1/incidents/{inc_id}/assign", json={
        "assigned_to": "david.m@ops.example.com"
    })
    assert assign_res.status_code == 200

    # Resolve
    resolve_res = client.post(f"/api/v1/incidents/{inc_id}/resolve", json={
        "resolution_notes": "Restarted target upstream pods and flushed ARP cache."
    })
    assert resolve_res.status_code == 200

    # Verify updated status
    verify_res = client.get(f"/api/v1/incidents/{inc_id}")
    updated_inc = json.loads(verify_res.data)
    assert updated_inc["status"] == "Resolved"
    assert updated_inc["assigned_to"] == "david.m@ops.example.com"
    assert "Restarted target" in updated_inc["resolution_notes"]

def test_metrics_endpoint(client):
    res = client.get("/api/v1/metrics")
    assert res.status_code == 200
    assert b"incident_total" in res.data

def test_web_views(client):
    # Dashboard view
    res = client.get("/")
    assert res.status_code == 200
    assert b"IncidentFlow" in res.data

    # Incidents list view
    res = client.get("/incidents")
    assert res.status_code == 200

    # New incident form view
    res = client.get("/incidents/new")
    assert res.status_code == 200

    # Create an incident and test detail view rendering
    post_res = client.post("/api/v1/incidents", json={
        "title": "Web UI Render Test Incident",
        "description": "Checking template compilation",
        "service": "frontend-ui",
        "severity": "P3 - Medium"
    })
    inc_id = json.loads(post_res.data)["incident_id"]

    detail_res = client.get(f"/incidents/{inc_id}")
    assert detail_res.status_code == 200
    assert b"Web UI Render Test Incident" in detail_res.data

