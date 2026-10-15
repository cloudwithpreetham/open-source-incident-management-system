"""
Open-Source Incident Management System
Flask Application providing REST APIs and a Responsive Web Dashboard.
"""
import os
from datetime import datetime, timezone

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

import models
import notifications

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "incident-management-super-secret-key-2026")

# Ensure database tables exist upon startup
models.init_db()

# -------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------
def get_current_user_role():
    """Simulate session/role selection (Viewer, DevOps Engineer, Admin). Default: DevOps Engineer."""
    return request.cookies.get("incident_user_role", "DevOps Engineer")

def get_current_user_name():
    return request.cookies.get("incident_user_name", "David Miller")

@app.context_processor
def inject_global_context():
    return {
        "current_role": get_current_user_role(),
        "current_user_name": get_current_user_name(),
        "app_version": "v1.0.0-elevatelabs"
    }

# -------------------------------------------------------------
# REST API ENDPOINTS
# -------------------------------------------------------------
@app.route("/api/v1/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "incident-management-portal",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

@app.route("/api/v1/incidents", methods=["GET"])
def api_list_incidents():
    status = request.args.get("status")
    severity = request.args.get("severity")
    service = request.args.get("service")

    query = "SELECT * FROM incidents WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if service:
        query += " AND service LIKE ?"
        params.append(f"%{service}%")

    query += " ORDER BY id DESC"

    conn = models.get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    incidents = [dict(row) for row in rows]
    return jsonify({"count": len(incidents), "incidents": incidents}), 200

@app.route("/api/v1/incidents", methods=["POST"])
def api_create_incident():
    data = request.get_json(silent=True) or request.form
    title = data.get("title")
    description = data.get("description")
    service = data.get("service")
    severity = data.get("severity", "P3 - Medium")
    reporter_name = data.get("reporter_name", get_current_user_name())
    reporter_email = data.get("reporter_email", "ops-team@company.internal")
    assigned_to = data.get("assigned_to")

    if not title or not description or not service:
        return jsonify({"error": "Fields 'title', 'description', and 'service' are required."}), 400

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = models.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incidents (title, description, service, severity, status, reporter_name, reporter_email, assigned_to, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?)
    """, (title, description, service, severity, reporter_name, reporter_email, assigned_to, now, now))
    incident_id = cursor.lastrowid
    conn.commit()
    conn.close()

    models.log_incident_activity(incident_id, "Incident Created", reporter_name, f"Initial severity: {severity}")

    incident_dict = {
        "id": incident_id,
        "title": title,
        "description": description,
        "service": service,
        "severity": severity,
        "status": "Open",
        "assigned_to": assigned_to,
        "reporter_name": reporter_name,
        "reporter_email": reporter_email
    }

    if assigned_to:
        notifications.send_incident_notification(assigned_to, f"New Incident Assigned: #{incident_id} [{severity}]", incident_dict, "Assigned")

    return jsonify({"message": "Incident created successfully", "incident_id": incident_id}), 201

@app.route("/api/v1/incidents/<int:incident_id>", methods=["GET"])
def api_get_incident(incident_id):
    conn = models.get_db_connection()
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Incident not found"}), 404

    logs = conn.execute("SELECT * FROM incident_logs WHERE incident_id = ? ORDER BY id DESC", (incident_id,)).fetchall()
    conn.close()

    result = dict(row)
    result["timeline"] = [dict(log) for log in logs]
    return jsonify(result), 200

@app.route("/api/v1/incidents/<int:incident_id>/assign", methods=["POST"])
def api_assign_incident(incident_id):
    data = request.get_json(silent=True) or request.form
    assigned_to = data.get("assigned_to")
    actor = data.get("actor", get_current_user_name())

    if not assigned_to:
        return jsonify({"error": "'assigned_to' email or name is required."}), 400

    conn = models.get_db_connection()
    inc = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not inc:
        conn.close()
        return jsonify({"error": "Incident not found"}), 404

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE incidents SET assigned_to = ?, updated_at = ? WHERE id = ?", (assigned_to, now, incident_id))
    conn.commit()
    conn.close()

    models.log_incident_activity(incident_id, "Assigned", actor, f"Assigned to {assigned_to}")

    inc_dict = dict(inc)
    inc_dict["assigned_to"] = assigned_to
    notifications.send_incident_notification(assigned_to, f"Assignment Update: #{incident_id} [{inc_dict['severity']}]", inc_dict, "Assigned")

    return jsonify({"message": f"Incident #{incident_id} assigned to {assigned_to}"}), 200

@app.route("/api/v1/incidents/<int:incident_id>/resolve", methods=["POST"])
def api_resolve_incident(incident_id):
    data = request.get_json(silent=True) or request.form
    resolution_notes = data.get("resolution_notes")
    actor = data.get("actor", get_current_user_name())

    if not resolution_notes:
        return jsonify({"error": "'resolution_notes' are required to resolve an incident."}), 400

    conn = models.get_db_connection()
    inc = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not inc:
        conn.close()
        return jsonify({"error": "Incident not found"}), 404

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE incidents
        SET status = 'Resolved', resolution_notes = ?, updated_at = ?, resolved_at = ?
        WHERE id = ?
    """, (resolution_notes, now, now, incident_id))
    conn.commit()
    conn.close()

    models.log_incident_activity(incident_id, "Incident Resolved", actor, resolution_notes)

    inc_dict = dict(inc)
    inc_dict["status"] = "Resolved"
    inc_dict["resolution_notes"] = resolution_notes
    if inc_dict.get("reporter_email"):
        notifications.send_incident_notification(inc_dict["reporter_email"], f"Resolved: #{incident_id} {inc_dict['title']}", inc_dict, "Resolved")

    return jsonify({"message": f"Incident #{incident_id} resolved"}), 200

@app.route("/api/v1/metrics", methods=["GET"])
def api_metrics():
    """Prometheus-compatible plain text metrics."""
    conn = models.get_db_connection()
    counts = conn.execute("""
        SELECT status, COUNT(*) as count FROM incidents GROUP BY status
    """).fetchall()
    conn.close()

    lines = [
        "# HELP incident_total Number of incidents by status",
        "# TYPE incident_total gauge"
    ]
    for row in counts:
        lines.append(f'incident_total{{status="{row["status"]}"}} {row["count"]}')
    return "\n".join(lines), 200, {"Content-Type": "text/plain; version=0.0.4"}


# -------------------------------------------------------------
# WEB DASHBOARD & UI VIEWS
# -------------------------------------------------------------
@app.route("/")
def dashboard_view():
    conn = models.get_db_connection()
    total_incidents = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    open_incidents = conn.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Open'").fetchone()[0]
    investigating = conn.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Investigating'").fetchone()[0]
    mitigated = conn.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Mitigated'").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Resolved'").fetchone()[0]
    critical_p1 = conn.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'P1 - Critical' AND status != 'Resolved'").fetchone()[0]

    recent_incidents = conn.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT 5").fetchall()
    recent_logs = conn.execute("""
        SELECT l.*, i.title as incident_title
        FROM incident_logs l
        JOIN incidents i ON l.incident_id = i.id
        ORDER BY l.id DESC LIMIT 6
    """).fetchall()
    users = conn.execute("SELECT * FROM users ORDER BY name ASC").fetchall()
    conn.close()

    metrics = {
        "total": total_incidents,
        "open": open_incidents,
        "investigating": investigating,
        "mitigated": mitigated,
        "resolved": resolved,
        "critical_active": critical_p1
    }

    return render_template("index.html", metrics=metrics, recent_incidents=recent_incidents, recent_logs=recent_logs, users=users)

@app.route("/incidents")
def incidents_view():
    status = request.args.get("status", "")
    severity = request.args.get("severity", "")
    search = request.args.get("q", "")

    query = "SELECT * FROM incidents WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if search:
        query += " AND (title LIKE ? OR service LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " ORDER BY id DESC"

    conn = models.get_db_connection()
    incidents = conn.execute(query, params).fetchall()
    users = conn.execute("SELECT * FROM users ORDER BY name ASC").fetchall()
    conn.close()

    return render_template("incidents.html", incidents=incidents, users=users, selected_status=status, selected_severity=severity, search_query=search)

@app.route("/incidents/<int:incident_id>")
def incident_detail_view(incident_id):
    conn = models.get_db_connection()
    incident = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not incident:
        conn.close()
        flash(f"Incident #{incident_id} not found.", "danger")
        return redirect(url_for("incidents_view"))

    logs = conn.execute("SELECT * FROM incident_logs WHERE incident_id = ? ORDER BY id DESC", (incident_id,)).fetchall()
    users = conn.execute("SELECT * FROM users ORDER BY name ASC").fetchall()
    conn.close()

    return render_template("incident_detail.html", incident=incident, logs=logs, users=users)

@app.route("/incidents/new", methods=["GET", "POST"])
def new_incident_view():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        service = request.form.get("service")
        severity = request.form.get("severity", "P3 - Medium")
        assigned_to = request.form.get("assigned_to") or None
        reporter_name = get_current_user_name()
        reporter_email = "devops-lead@ops.internal"

        if not title or not description or not service:
            flash("Please provide Title, Service, and Description.", "warning")
            return redirect(url_for("new_incident_view"))

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn = models.get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO incidents (title, description, service, severity, status, reporter_name, reporter_email, assigned_to, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?)
        """, (title, description, service, severity, reporter_name, reporter_email, assigned_to, now, now))
        new_id = cur.lastrowid
        conn.commit()
        conn.close()

        models.log_incident_activity(new_id, "Incident Created", reporter_name, f"Reported through Web Portal. Severity: {severity}")

        if assigned_to:
            inc_dict = {
                "id": new_id, "title": title, "description": description,
                "service": service, "severity": severity, "status": "Open",
                "assigned_to": assigned_to, "reporter_name": reporter_name
            }
            notifications.send_incident_notification(assigned_to, f"Incident Assigned: #{new_id} [{severity}]", inc_dict, "Assigned")

        flash(f"Incident #{new_id} created successfully!", "success")
        return redirect(url_for("incident_detail_view", incident_id=new_id))

    conn = models.get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY name ASC").fetchall()
    conn.close()
    return render_template("new_incident.html", users=users)

@app.route("/incidents/<int:incident_id>/update-status", methods=["POST"])
def update_status_form(incident_id):
    new_status = request.form.get("status")
    note = request.form.get("status_note", "")
    actor = get_current_user_name()

    conn = models.get_db_connection()
    inc = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    if not inc:
        conn.close()
        flash("Incident not found", "danger")
        return redirect(url_for("incidents_view"))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    resolved_at = now if new_status == "Resolved" else inc["resolved_at"]

    conn.execute("""
        UPDATE incidents
        SET status = ?, updated_at = ?, resolved_at = ?
        WHERE id = ?
    """, (new_status, now, resolved_at, incident_id))
    conn.commit()
    conn.close()

    models.log_incident_activity(incident_id, f"Status changed to {new_status}", actor, note)
    flash(f"Incident status updated to {new_status}.", "info")
    return redirect(url_for("incident_detail_view", incident_id=incident_id))

@app.route("/incidents/<int:incident_id>/assign-form", methods=["POST"])
def assign_form(incident_id):
    assigned_to = request.form.get("assigned_to")
    actor = get_current_user_name()

    conn = models.get_db_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE incidents SET assigned_to = ?, updated_at = ? WHERE id = ?", (assigned_to, now, incident_id))
    conn.commit()
    conn.close()

    models.log_incident_activity(incident_id, "Assigned", actor, f"Assigned to {assigned_to}")
    flash(f"Incident #{incident_id} assigned to {assigned_to}.", "success")
    return redirect(url_for("incident_detail_view", incident_id=incident_id))

@app.route("/incidents/<int:incident_id>/resolve-form", methods=["POST"])
def resolve_form(incident_id):
    resolution_notes = request.form.get("resolution_notes")
    actor = get_current_user_name()

    if not resolution_notes:
        flash("Resolution notes are required.", "warning")
        return redirect(url_for("incident_detail_view", incident_id=incident_id))

    conn = models.get_db_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE incidents
        SET status = 'Resolved', resolution_notes = ?, updated_at = ?, resolved_at = ?
        WHERE id = ?
    """, (resolution_notes, now, now, incident_id))
    conn.commit()
    conn.close()

    models.log_incident_activity(incident_id, "Incident Resolved", actor, resolution_notes)
    flash(f"Incident #{incident_id} marked as Resolved.", "success")
    return redirect(url_for("incident_detail_view", incident_id=incident_id))

@app.route("/switch-role", methods=["POST"])
def switch_role():
    role = request.form.get("role", "DevOps Engineer")
    name = request.form.get("name", "David Miller")
    redirect_target = request.referrer or url_for("dashboard_view")
    response = redirect(redirect_target)
    response.set_cookie("incident_user_role", role, max_age=60*60*24*7)
    response.set_cookie("incident_user_name", name, max_age=60*60*24*7)
    flash(f"Switched role to {role} ({name}).", "info")
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
