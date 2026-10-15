"""
Seed script to populate initial users and realistic infrastructure/application incidents.
"""
from datetime import datetime, timedelta, timezone

import models


def seed_users():
    """Populates users table with initial team members."""
    conn = models.get_db_connection()
    cursor = conn.cursor()
    team_members = [
        ("Alice Chen", "alice.chen@ops.example.com", "Admin"),
        ("David Miller", "david.m@ops.example.com", "DevOps Engineer"),
        ("Siddharth Patel", "siddharth.p@ops.example.com", "SRE"),
        ("Elena Rostova", "elena.r@ops.example.com", "DevOps Engineer"),
        ("Security Bot", "secops-alert@internal.local", "Viewer")
    ]
    for name, email, role in team_members:
        cursor.execute(
            "INSERT OR IGNORE INTO users (name, email, role, created_at) VALUES (?, ?, ?, ?)",
            (name, email, role, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        )
    conn.commit()
    conn.close()

def seed():
    models.init_db()
    conn = models.get_db_connection()
    cursor = conn.cursor()

    # Clear previous seed data
    cursor.execute("DELETE FROM incident_logs;")
    cursor.execute("DELETE FROM incidents;")
    cursor.execute("DELETE FROM users;")
    conn.commit()
    conn.close()

    seed_users()
    conn = models.get_db_connection()
    cursor = conn.cursor()

    # Seed Sample Incidents
    now = datetime.now(timezone.utc)
    incidents_data = [
        {
            "title": "API Gateway 504 Gateway Timeout Spikes",
            "description": "High latency observed on `/v1/orders` endpoint; NGINX reverse proxy returning 504 Gateway Timeout under 850 RPS load.",
            "service": "api-gateway-prod",
            "severity": "P1 - Critical",
            "status": "Resolved",
            "reporter_name": "CloudWatch Alert",
            "reporter_email": "alerts@cloudwatch.aws",
            "assigned_to": "david.m@ops.example.com",
            "resolution_notes": "Identified database connection pool starvation. Increased backend max_connections to 300 and scaled read replicas from 2 to 4.",
            "created_at": (now - timedelta(days=2, hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": (now - timedelta(days=2, hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": (now - timedelta(days=2, hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "logs": [
                ("Incident Reported", "CloudWatch Alert", "Triggered by P99 Latency > 2500ms for 3 consecutive checks."),
                ("Assigned", "Alice Chen", "Assigned incident to David Miller for immediate mitigation."),
                ("Investigation", "David Miller", "Traced slow queries to unindexed join on `order_items` table."),
                ("Resolved", "David Miller", "Scaled replicas and added composite index. Latency normalized to 45ms.")
            ]
        },
        {
            "title": "Kubernetes Ingress SSL/TLS Certificate Expiration Warning",
            "description": "Automated cert-manager renewal failed for `*.api.company.com` due to Let's Encrypt rate-limiting challenge error.",
            "service": "k8s-ingress-controller",
            "severity": "P2 - High",
            "status": "Mitigated",
            "reporter_name": "Prometheus Blackbox",
            "reporter_email": "prometheus@internal.local",
            "assigned_to": "siddharth.p@ops.example.com",
            "resolution_notes": "Manually uploaded wildcard backup SSL secret while debugging DNS01 ACME challenge timeout.",
            "created_at": (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": None,
            "logs": [
                ("Incident Reported", "Prometheus Blackbox", "Cert expiration threshold breached (< 7 days remaining)."),
                ("Assigned", "Alice Chen", "Assigned to Siddharth Patel."),
                ("Mitigated", "Siddharth Patel", "Applied fallback certificate secret. Service remains green; troubleshooting Route53 webhook.")
            ]
        },
        {
            "title": "Payment Microservice Pod CrashLoopBackOff",
            "description": "Pod `payment-service-7f98d6c7b-xk89l` is crashlooping due to OOMKilled (Exit Code 137). Memory usage exceeded 512Mi limit.",
            "service": "payment-service",
            "severity": "P1 - Critical",
            "status": "Investigating",
            "reporter_name": "Datadog Agent",
            "reporter_email": "pagerduty@internal.local",
            "assigned_to": "elena.r@ops.example.com",
            "resolution_notes": None,
            "created_at": (now - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": None,
            "logs": [
                ("Incident Reported", "Datadog Agent", "Container killed due to OOM memory violation."),
                ("Status Changed to Investigating", "Elena Rostova", "Analyzing memory heap dump from latest pod restart.")
            ]
        },
        {
            "title": "High Disk Space Utilization on ElasticSearch Data Node 03",
            "description": "Disk utilization reached 86% on mount point `/data/es-node-03`. Exceeds warning threshold of 80%.",
            "service": "logging-elasticsearch",
            "severity": "P3 - Medium",
            "status": "Open",
            "reporter_name": "Grafana Alert Rule",
            "reporter_email": "monitoring@company.com",
            "assigned_to": None,
            "resolution_notes": None,
            "created_at": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": None,
            "logs": [
                ("Incident Reported", "Grafana Alert Rule", "Disk utilization warning triggered.")
            ]
        },
        {
            "title": "Nightly Backup CronJob Failed to Upload to S3",
            "description": "The scheduled PostgreSQL database snapshot cronjob failed with `AccessDenied` error while invoking `PutObject`.",
            "service": "postgres-backup-cron",
            "severity": "P3 - Medium",
            "status": "Resolved",
            "reporter_name": "System Cron",
            "reporter_email": "root@prod-backup-worker",
            "assigned_to": "david.m@ops.example.com",
            "resolution_notes": "AWS IAM role session token had expired. Refreshed STS credentials and re-ran backup job successfully.",
            "created_at": (now - timedelta(days=1, hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": (now - timedelta(days=1, hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": (now - timedelta(days=1, hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
            "logs": [
                ("Incident Reported", "System Cron", "Backup exit code 1."),
                ("Resolved", "David Miller", "Renewed IAM role and verified snapshot uploaded (Size: 14.8 GB).")
            ]
        }
    ]

    for inc in incidents_data:
        cursor.execute("""
            INSERT INTO incidents (
                title, description, service, severity, status,
                reporter_name, reporter_email, assigned_to, resolution_notes,
                created_at, updated_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inc["title"], inc["description"], inc["service"], inc["severity"],
            inc["status"], inc["reporter_name"], inc["reporter_email"],
            inc["assigned_to"], inc["resolution_notes"], inc["created_at"],
            inc["updated_at"], inc["resolved_at"]
        ))
        inc_id = cursor.lastrowid

        for action, actor, notes in inc["logs"]:
            cursor.execute("""
                INSERT INTO incident_logs (incident_id, action, actor, notes, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (inc_id, action, actor, notes, inc["created_at"]))

    conn.commit()
    conn.close()
    print("Seed data successfully inserted into SQLite database.")

if __name__ == "__main__":
    seed()
