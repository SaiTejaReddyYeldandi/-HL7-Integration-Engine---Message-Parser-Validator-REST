"""
Message storage in SQLite.

Every message received — valid or invalid — is stored with its parsed
content, validation result, routing decision, and ACK code.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "hl7_engine.db"


def init_db():
    """Create the messages table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            message_control_id TEXT,
            message_type TEXT,
            sending_app TEXT,
            sending_facility TEXT,
            patient_id TEXT,
            is_valid INTEGER,
            errors TEXT,
            warnings TEXT,
            destinations TEXT,
            ack_code TEXT,
            raw_message TEXT,
            parsed_json TEXT
        )
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_control_id
        ON messages(message_control_id)
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_type
        ON messages(message_type)
    """)

    conn.commit()
    conn.close()


def save_message(raw, parsed, validation, routing, ack_code):
    """Persist a processed message to SQLite."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    patient_id = (
        parsed["patient"]["patient_id"] if parsed.get("patient") else None
    )

    c.execute("""
        INSERT INTO messages (
            received_at, message_control_id, message_type,
            sending_app, sending_facility, patient_id,
            is_valid, errors, warnings, destinations,
            ack_code, raw_message, parsed_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        parsed.get("message_control_id"),
        parsed.get("message_type"),
        parsed.get("sending_app"),
        parsed.get("sending_facility"),
        patient_id,
        1 if validation["valid"] else 0,
        json.dumps(validation["errors"]),
        json.dumps(validation["warnings"]),
        json.dumps(routing["destinations"]),
        ack_code,
        raw,
        json.dumps({k: v for k, v in parsed.items() if k != "segments"}),
    ))

    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return msg_id


def get_all_messages(limit=100):
    """Retrieve recent messages."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, received_at, message_control_id, message_type,
               sending_app, patient_id, is_valid, ack_code,
               errors, destinations
        FROM messages
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = [dict(r) for r in c.fetchall()]

    for r in rows:
        r["errors"] = json.loads(r["errors"]) if r["errors"] else []
        r["destinations"] = json.loads(r["destinations"]) if r["destinations"] else []

    conn.close()
    return rows


def get_message_by_id(msg_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    result = dict(row)

    for col in ("errors", "warnings", "destinations"):
        if result.get(col):
            result[col] = json.loads(result[col])

    if result.get("parsed_json"):
        result["parsed_json"] = json.loads(result["parsed_json"])

    return result


def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM messages")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM messages WHERE is_valid = 1")
    valid = c.fetchone()[0]

    c.execute("""
        SELECT message_type, COUNT(*)
        FROM messages
        GROUP BY message_type
    """)
    by_type = dict(c.fetchall())

    conn.close()

    return {
        "total": total,
        "valid": valid,
        "invalid": total - valid,
        "by_type": by_type,
    }