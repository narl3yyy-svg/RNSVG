"""SQLite storage for RNSVG messages and conversations."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class MessageDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE NOT NULL,
                    source_hash TEXT NOT NULL,
                    destination_hash TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    fields TEXT DEFAULT '{}',
                    state TEXT DEFAULT 'delivered',
                    timestamp REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_peer ON messages(destination_hash);
                CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);
                """,
            )

    def insert_message(
        self,
        *,
        source_hash: str,
        destination_hash: str,
        direction: str,
        content: str,
        title: str | None = None,
        fields: dict[str, Any] | None = None,
        state: str = "delivered",
        message_hash: str | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        msg_hash = message_hash or uuid.uuid4().hex
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages
                (hash, source_hash, destination_hash, direction, title, content, fields, state, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msg_hash,
                    source_hash,
                    destination_hash,
                    direction,
                    title,
                    content,
                    json.dumps(fields or {}),
                    state,
                    now,
                    created_at,
                ),
            )
        return self.get_message_by_hash(msg_hash)

    def get_message_by_hash(self, message_hash: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM messages WHERE hash = ?", (message_hash,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_conversation_messages(
        self,
        local_hash: str,
        peer_hash: str,
        *,
        limit: int = 100,
        order: str = "asc",
        after_id: int | None = None,
    ) -> list[dict[str, Any]]:
        order_sql = "DESC" if order.lower() == "desc" else "ASC"
        params: list[Any] = [local_hash, peer_hash, peer_hash, local_hash]
        after_clause = ""
        if after_id is not None:
            if order_sql == "DESC":
                after_clause = "AND id < ?"
            else:
                after_clause = "AND id > ?"
            params.append(after_id)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM messages
                WHERE ((source_hash = ? AND destination_hash = ?)
                   OR (source_hash = ? AND destination_hash = ?))
                   {after_clause}
                ORDER BY id {order_sql}
                LIMIT ?
                """,
                params,
            ).fetchall()
        rows_out = [self._row_to_dict(r) for r in rows]
        if order_sql == "DESC":
            rows_out.reverse()
        return rows_out

    def get_conversations(self, local_hash: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT m.* FROM messages m
                INNER JOIN (
                    SELECT
                        CASE WHEN source_hash = ? THEN destination_hash ELSE source_hash END AS peer_hash,
                        MAX(timestamp) AS max_ts
                    FROM messages
                    WHERE source_hash = ? OR destination_hash = ?
                    GROUP BY peer_hash
                ) latest ON latest.max_ts = m.timestamp
                ORDER BY m.timestamp DESC
                """,
                (local_hash, local_hash, local_hash),
            ).fetchall()
        conversations: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            peer = row["destination_hash"] if row["source_hash"] == local_hash else row["source_hash"]
            if peer in seen:
                continue
            seen.add(peer)
            conversations.append(
                {
                    "peer_hash": peer,
                    "title": row["title"],
                    "content": row["content"],
                    "fields": row["fields"],
                    "failed_count": 0,
                    "created_at": row["created_at"],
                    "timestamp": row["timestamp"],
                },
            )
        return conversations

    def update_message_state(self, message_hash: str, state: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE messages SET state = ? WHERE hash = ?", (state, message_hash))

    def delete_conversation(self, local_hash: str, peer_hash: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM messages
                WHERE (source_hash = ? AND destination_hash = ?)
                   OR (source_hash = ? AND destination_hash = ?)
                """,
                (local_hash, peer_hash, peer_hash, local_hash),
            )

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)