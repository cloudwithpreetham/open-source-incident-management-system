"""
Database models and helpers for Open-Source Incident Management System.
Uses SQLite for zero-configuration, robust local and containerized persistence.
"""
import os
import sqlite3
from datetime import datetime, timezone


def get_db_path():
    return os.getenv("INCIDENT_DB_PATH", "incidents.db")

def get_db_connection():
    """Create and return a database connection with row factory enabled."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database tables with schema for incidents, audit logs, and users."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users / Team Members table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL CHECK(role IN ('Admin', 'DevOps Engineer', 'SRE', 'Viewer')),
        created_at TEXT NOT NULL
    );
    """)

    # Incidents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        service TEXT NOT NULL,
        severity TEXT NOT NULL CHECK(severity IN ('P1 - Critical', 'P2 - High', 'P3 - Medium', 'P4 - Low')),
        status TEXT NOT NULL CHECK(status IN ('Open', 'Investigating', 'Mitigated', 'Resolved')),
        reporter_name TEXT NOT NULL,
        reporter_email TEXT NOT NULL,
        assigned_to TEXT,
        resolution_notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        resolved_at TEXT
    );
    """)

    # Incident Audit Logs / Timeline table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incident_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        actor TEXT NOT NULL,
        notes TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def log_incident_activity(incident_id: int, action: str, actor: str, notes: str = None):
    """Helper to record an entry in the incident audit trail."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incident_logs (incident_id, action, actor, notes, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (incident_id, action, actor, notes or "", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
