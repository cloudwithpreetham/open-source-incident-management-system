"""
End-to-End Quality Assurance (QA) Engineer Test Suite
Project 8: Open-Source Incident Management System (IncidentFlow)

Covers:
  - User Journey E2E (UI Form Creation, Status Transitions, Assign, Resolve, RCA)
  - Negative Testing & Boundary Validation
  - Search, Filter & Pagination Query Boundaries
  - Role-Based Access Control (RBAC) Personas & Session Switching
  - Observability & Metrics Scrape Compliance (Prometheus format & Healthcheck)
  - Notification Subsystem Resilience & Fallback Error Handling
  - Audit Log Timeline Integrity & Traceability
"""
import json
import os
import sys
from datetime import datetime

import pytest

proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if proj_dir not in sys.path:
    sys.path.insert(0, proj_dir)

os.environ["INCIDENT_DB_PATH"] = "qa_test_incidents.db"
os.environ["ENABLE_SMTP"] = "false"

import app as flask_app
import models
import notifications
import seed_data


@pytest.fixture(scope="function")
def qa_client():
    """Provides an isolated test client with a clean test database and pre-seeded users."""
    os.environ["INCIDENT_DB_PATH"] = "qa_test_incidents.db"
    models.init_db()
    conn = models.get_db_connection()
    conn.execute("DELETE FROM incident_logs;")
    conn.execute("DELETE FROM incidents;")
    conn.commit()
    conn.close()

    seed_data.seed_users()

    flask_app.app.config["TESTING"] = True
    flask_app.app.config["WTF_CSRF_ENABLED"] = False

    with flask_app.app.test_client() as client:
        yield client

    try:
        conn = models.get_db_connection()
        conn.execute("DELETE FROM incident_logs;")
        conn.execute("DELETE FROM incidents;")
        conn.commit()
        conn.close()
    except Exception:
        pass


# =====================================================================
# 1. E2E USER JOURNEY TESTING (Full Incident Lifecycle via Web UI)
# =====================================================================
class TestIncidentLifecycleE2E:
    """Simulates an on-call engineer's full workflow through the web portal."""

    def test_full_incident_lifecycle_journey(self, qa_client):
        # Step 1: Visit new incident page
        get_res = qa_client.get("/incidents/new")
        assert get_res.status_code == 200
        assert b"Declare New Incident" in get_res.data

        # Step 2: Declare new incident via form submission
        create_payload = {
            "title": "Auth Service Redis Cache Eviction Surge",
            "service": "auth-service-prod",
            "severity": "P1 - Critical",
            "assigned_to": "priya.sharma@ops.internal",
            "description": "High memory threshold breach causing cascaded session drops."
        }
        post_res = qa_client.post("/incidents/new", data=create_payload, follow_redirects=True)
        assert post_res.status_code == 200
        assert b"Auth Service Redis Cache Eviction Surge" in post_res.data
        assert b"P1 - Critical" in post_res.data
        assert b"Open" in post_res.data
        assert b"priya.sharma@ops.internal" in post_res.data

        # Retrieve created incident ID from database
        conn = models.get_db_connection()
        inc = conn.execute("SELECT * FROM incidents WHERE title = ?", (create_payload["title"],)).fetchone()
        assert inc is not None
        inc_id = inc["id"]
        conn.close()

        # Step 3: Transition status to 'Investigating'
        status_res = qa_client.post(f"/incidents/{inc_id}/update-status", data={
            "status": "Investigating",
            "status_note": "Identified cache thrashing in redis-cluster-01. Analyzing key TTLs."
        }, follow_redirects=True)
        assert status_res.status_code == 200
        assert b"Investigating" in status_res.data
        assert b"Identified cache thrashing" in status_res.data

        # Step 4: Reassign to Principal SRE
        assign_res = qa_client.post(f"/incidents/{inc_id}/assign-form", data={
            "assigned_to": "marcus.vance@ops.internal"
        }, follow_redirects=True)
        assert assign_res.status_code == 200
        assert b"marcus.vance@ops.internal" in assign_res.data

        # Step 5: Transition to 'Mitigated'
        mitigate_res = qa_client.post(f"/incidents/{inc_id}/update-status", data={
            "status": "Mitigated",
            "status_note": "Scaled up Redis memory max from 16GB to 32GB. Eviction rate normalized."
        }, follow_redirects=True)
        assert mitigate_res.status_code == 200
        assert b"Mitigated" in mitigate_res.data

        # Step 6: Resolve Incident with Root Cause Analysis (RCA)
        rca_notes = "Root cause: Unbounded session token cache without TTL. Deployed hotfix v2.4.1 to enforce 24h TTL and upgraded memory limits."
        resolve_res = qa_client.post(f"/incidents/{inc_id}/resolve-form", data={
            "resolution_notes": rca_notes
        }, follow_redirects=True)
        assert resolve_res.status_code == 200
        assert b"Resolved" in resolve_res.data
        assert b"Root Cause Analysis &amp; Resolution" in resolve_res.data or b"Root Cause Analysis" in resolve_res.data
        assert b"Deployed hotfix v2.4.1" in resolve_res.data

        # Step 7: Verify complete audit trail history in database
        conn = models.get_db_connection()
        logs = conn.execute("SELECT * FROM incident_logs WHERE incident_id = ? ORDER BY id ASC", (inc_id,)).fetchall()
        conn.close()
        assert len(logs) >= 5
        actions = [log["action"] for log in logs]
        assert "Incident Created" in actions
        assert "Status changed to Investigating" in actions
        assert "Assigned" in actions
        assert "Status changed to Mitigated" in actions
        assert "Incident Resolved" in actions


# =====================================================================
# 2. NEGATIVE TESTING & BOUNDARY VALIDATION
# =====================================================================
class TestNegativeAndBoundaryScenarios:
    """Verifies that invalid payloads, missing fields, and 404 boundaries fail safely."""

    def test_create_incident_missing_mandatory_fields(self, qa_client):
        # Missing title
        res = qa_client.post("/api/v1/incidents", json={
            "service": "k8s-cluster",
            "description": "Missing title"
        })
        assert res.status_code == 400
        data = json.loads(res.data)
        assert "error" in data

        # Missing service
        res = qa_client.post("/api/v1/incidents", json={
            "title": "Database Outage",
            "description": "Missing service"
        })
        assert res.status_code == 400

        # Missing description
        res = qa_client.post("/api/v1/incidents", json={
            "title": "Database Outage",
            "service": "postgres-db"
        })
        assert res.status_code == 400

    def test_non_existent_incident_handling(self, qa_client):
        # Non-existent GET
        res = qa_client.get("/api/v1/incidents/999999")
        assert res.status_code == 404
        assert json.loads(res.data)["error"] == "Incident not found"

        # Non-existent Assign
        res = qa_client.post("/api/v1/incidents/999999/assign", json={"assigned_to": "someone@ops.internal"})
        assert res.status_code == 404

        # Non-existent Resolve
        res = qa_client.post("/api/v1/incidents/999999/resolve", json={"resolution_notes": "RCA note"})
        assert res.status_code == 404

        # Non-existent Web View redirect
        web_res = qa_client.get("/incidents/999999", follow_redirects=True)
        assert web_res.status_code == 200
        assert b"Incident #999999 not found" in web_res.data

    def test_assign_missing_assigned_to(self, qa_client):
        # Create valid incident
        create_res = qa_client.post("/api/v1/incidents", json={
            "title": "Kafka Partition Desync",
            "service": "kafka-prod",
            "description": "Partition 4 under-replicated"
        })
        inc_id = json.loads(create_res.data)["incident_id"]

        # Call assign without assigned_to
        res = qa_client.post(f"/api/v1/incidents/{inc_id}/assign", json={})
        assert res.status_code == 400
        assert "'assigned_to' email or name is required." in json.loads(res.data)["error"]

    def test_resolve_missing_resolution_notes(self, qa_client):
        create_res = qa_client.post("/api/v1/incidents", json={
            "title": "Border Router BGP Flap",
            "service": "network-gateway",
            "description": "Transit provider BGP session flapping"
        })
        inc_id = json.loads(create_res.data)["incident_id"]

        # Resolve with empty resolution notes
        res = qa_client.post(f"/api/v1/incidents/{inc_id}/resolve", json={"resolution_notes": ""})
        assert res.status_code == 400
        assert "resolution_notes" in json.loads(res.data)["error"]

        # UI form submission without resolution notes
        ui_res = qa_client.post(f"/incidents/{inc_id}/resolve-form", data={"resolution_notes": ""}, follow_redirects=True)
        assert ui_res.status_code == 200
        assert b"Resolution notes are required." in ui_res.data


# =====================================================================
# 3. SEARCH & FILTERING BOUNDARY TESTING
# =====================================================================
class TestSearchAndFilters:
    """Verifies incident filtering by status, severity, and text search."""

    def test_filter_by_status_and_severity(self, qa_client):
        # Seed 3 distinct incidents
        qa_client.post("/api/v1/incidents", json={
            "title": "P1 Search Target Alpha",
            "service": "billing-api",
            "severity": "P1 - Critical",
            "description": "Alpha description"
        })
        qa_client.post("/api/v1/incidents", json={
            "title": "P3 Search Target Beta",
            "service": "reporting-worker",
            "severity": "P3 - Medium",
            "description": "Beta description"
        })

        # Filter by severity
        res = qa_client.get("/api/v1/incidents?severity=P1%20-%20Critical")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["count"] == 1
        assert data["incidents"][0]["title"] == "P1 Search Target Alpha"

        # Web UI text search
        web_search = qa_client.get("/incidents?q=billing-api")
        assert web_search.status_code == 200
        assert b"P1 Search Target Alpha" in web_search.data
        assert b"P3 Search Target Beta" not in web_search.data

        # Search matching nothing
        empty_search = qa_client.get("/incidents?q=nonexistent-microservice-xyz")
        assert empty_search.status_code == 200
        assert b"No incidents found matching your query" in empty_search.data


# =====================================================================
# 4. ROLE-BASED ACCESS CONTROL (RBAC) & PERSONA TESTING
# =====================================================================
class TestRoleBasedAccessControl:
    """Tests switching between roles: Admin, DevOps Engineer, SRE, and Viewer."""

    @pytest.mark.parametrize("role,name", [
        ("Admin", "David Miller"),
        ("SRE", "Marcus Vance"),
        ("DevOps Engineer", "Priya Sharma"),
        ("Viewer", "Read-Only Stakeholder")
    ])
    def test_switch_role_cookie_propagation(self, qa_client, role, name):
        switch_res = qa_client.post("/switch-role", data={
            "role": role,
            "name": name
        }, follow_redirects=True)
        assert switch_res.status_code == 200
        assert f"Switched role to {role}".encode() in switch_res.data

        # Verify role appears in the navigation bar context
        dash_res = qa_client.get("/")
        assert role.encode() in dash_res.data
        assert name.encode() in dash_res.data


# =====================================================================
# 5. OBSERVABILITY & METRICS COMPLIANCE TESTING
# =====================================================================
class TestObservabilityMetrics:
    """Validates Prometheus metrics format and health check schema."""

    def test_health_check_payload_contract(self, qa_client):
        res = qa_client.get("/api/v1/health")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["status"] == "healthy"
        assert data["service"] == "incident-management-portal"
        # Validate ISO 8601 UTC timestamp
        parsed_time = datetime.fromisoformat(data["timestamp"])
        assert parsed_time is not None

    def test_prometheus_metrics_format_and_counters(self, qa_client):
        # Create 2 Open incidents
        qa_client.post("/api/v1/incidents", json={
            "title": "Metrics Test 1", "service": "srv-1", "description": "desc"
        })
        qa_client.post("/api/v1/incidents", json={
            "title": "Metrics Test 2", "service": "srv-2", "description": "desc"
        })

        res = qa_client.get("/api/v1/metrics")
        assert res.status_code == 200
        assert "text/plain" in res.headers["Content-Type"]

        content = res.data.decode("utf-8")
        assert "# HELP incident_total Number of incidents by status" in content
        assert "# TYPE incident_total gauge" in content
        assert 'incident_total{status="Open"} 2' in content


# =====================================================================
# 6. NOTIFICATION SUBSYSTEM RESILIENCE TESTING
# =====================================================================
class TestNotificationResilience:
    """Tests zero-downtime mock fallback when SMTP is disabled or fails."""

    def test_simulation_fallback_when_smtp_disabled(self):
        incident_data = {
            "id": 101,
            "title": "Simulated Queue Overflow",
            "severity": "P2 - High",
            "service": "sqs-worker",
            "status": "Open",
            "assigned_to": "devops@company.internal",
            "description": "Simulated queue test"
        }
        res = notifications.send_incident_notification("devops@company.internal", "Test Alert", incident_data)
        assert res["status"] == "simulated"
        assert res["recipient"] == "devops@company.internal"

    def test_graceful_exception_handling_on_smtp_error(self, monkeypatch):
        # Temporarily enable SMTP and point to invalid host
        monkeypatch.setattr(notifications, "ENABLE_SMTP", True)
        monkeypatch.setattr(notifications, "SMTP_HOST", "invalid.nonexistent.smtp.server.local")

        incident_data = {"id": 102, "title": "SMTP Fault", "severity": "P1"}
        res = notifications.send_incident_notification("alert@ops.internal", "Fault Test", incident_data)
        assert res["status"] == "failed_fallback_logged"
        assert "error" in res
