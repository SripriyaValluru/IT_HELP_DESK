"""SQLite database for IT Helpdesk - stores tickets and conversation history."""

import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DB_PATH = "helpdesk.db"


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database schema."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                customer_segment TEXT,
                channel TEXT,
                product_area TEXT,
                issue_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                sla_plan TEXT,
                initial_message TEXT,
                agent_first_reply TEXT,
                resolution_summary TEXT,
                resolution_time_hours REAL,
                reopened INTEGER DEFAULT 0,
                customer_sentiment TEXT,
                csat_score INTEGER,
                has_attachment INTEGER DEFAULT 0,
                platform TEXT,
                region TEXT,
                eval_split TEXT,
                scenario_key TEXT,
                assigned_to TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                thread_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_message TEXT,
                message_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS conversation_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES conversations(thread_id)
            );

            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_thread ON conversation_messages(thread_id);
        """)


def create_ticket(
    ticket_id: str,
    customer_id: str,
    issue_type: str,
    priority: str,
    initial_message: str,
    product_area: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> dict:
    """Create a new ticket."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tickets 
            (ticket_id, customer_id, issue_type, priority, initial_message, 
             product_area, assigned_to, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)""",
            (
                ticket_id,
                customer_id,
                issue_type,
                priority,
                initial_message,
                product_area,
                assigned_to or "L1",
                now,
                now,
            ),
        )
    return get_ticket(ticket_id)


def get_ticket(ticket_id: str) -> Optional[dict]:
    """Get a ticket by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None


def update_ticket(ticket_id: str, **updates) -> Optional[dict]:
    """Update a ticket."""
    if not updates:
        return get_ticket(ticket_id)

    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [ticket_id]

    with get_db() as conn:
        conn.execute(
            f"UPDATE tickets SET {set_clause} WHERE ticket_id = ?", values
        )
    return get_ticket(ticket_id)


def list_tickets(customer_id: Optional[str] = None, status: Optional[str] = None) -> list:
    """List tickets with optional filters."""
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def create_conversation(thread_id: str, user_id: str) -> dict:
    """Create a new conversation thread."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO conversations 
            (thread_id, user_id, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, 0)""",
            (thread_id, user_id, now, now),
        )
    return get_conversation(thread_id)


def get_conversation(thread_id: str) -> Optional[dict]:
    """Get conversation metadata."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ?", (thread_id,)
        ).fetchone()
        if row:
            return dict(row)
        return None


def add_message(thread_id: str, role: str, content: str) -> dict:
    """Add a message to a conversation."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO conversation_messages (thread_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)""",
            (thread_id, role, content, now),
        )
        conn.execute(
            """UPDATE conversations 
            SET last_message = ?, updated_at = ?, message_count = message_count + 1
            WHERE thread_id = ?""",
            (content, now, thread_id),
        )
    return {
        "thread_id": thread_id,
        "role": role,
        "content": content,
        "timestamp": now,
    }


def get_conversation_history(thread_id: str) -> list:
    """Get all messages for a conversation."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT role, content, timestamp 
            FROM conversation_messages 
            WHERE thread_id = ? 
            ORDER BY timestamp ASC""",
            (thread_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_user_conversations(user_id: str) -> list:
    """Get all conversations for a user."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM conversations 
            WHERE user_id = ? 
            ORDER BY updated_at DESC""",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]


# Initialize on import
init_db()