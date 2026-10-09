# BBMCPS

import os
import sys
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional
from urllib.parse import urlparse
import mcp
from mcp.server import MCPServer
from bbmcps_db import BlackboardDatabase
import bbmcps_cfg as cfg

g_db = BlackboardDatabase(cfg.DB_PATH)
g_srv = MCPServer(
    cfg.SERVER_NAME,
    instructions=(
        "Blackboard is a persistent local SQLite knowledge graph. "
        "Use search_notes before assuming knowledge is absent. "
        "Use get_note and traverse_notes to inspect existing knowledge. "
        "Use save_note for persistent knowledge, link_notes for "
        "cross-connections, discussions for persistent reasoning, "
        "and agent profiles for reusable behavioral configurations."
    ),
)
#
def get_srv():
    return g_srv

def get_db():
    return g_db

def utc_now() -> str:

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def normalize_text(value: str) -> str:

    return value.strip()


def validate_nonempty(
    value: str,
    field_name: str,
    max_length: Optional[int] = None,
) -> str:

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    if max_length is not None and len(value) > max_length:
        raise ValueError(
            f"{field_name} exceeds maximum length "
            f"of {max_length} characters"
        )

    return value


def validate_optional_text(
    value: Optional[str],
    field_name: str,
    max_length: Optional[int] = None,
) -> Optional[str]:

    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    value = value.strip()

    if max_length is not None and len(value) > max_length:
        raise ValueError(
            f"{field_name} exceeds maximum length "
            f"of {max_length} characters"
        )

    return value


def validate_url(url: str) -> str:

    url = validate_nonempty(
        url,
        "url",
        cfg.MAX_URL_SIZE,
    )

    parsed = urlparse(url)

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(
            "Only http:// and https:// URLs are allowed"
        )

    if not parsed.netloc:
        raise ValueError("Invalid URL: missing hostname")

    return url


def json_result(
    success: bool,
    message: str,
    **data: Any,
) -> str:

    result = {
        "success": success,
        "message": message,
    }

    result.update(data)

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:

    return {
        key: row[key]
        for key in row.keys()
    }


def rows_to_dicts(
    rows: list[sqlite3.Row],
) -> list[dict[str, Any]]:

    return [row_to_dict(row) for row in rows]

def get_note_row(
    conn: sqlite3.Connection,
    topic: str,
) -> sqlite3.Row:

    row = conn.execute(
        """
        SELECT
            n.*,
            ap.name AS agent_profile_name
        FROM notes n
        LEFT JOIN agent_profiles ap
            ON ap.id = n.agent_profile_id
        WHERE n.topic = ?
        """,
        (topic,),
    ).fetchone()

    if row is None:
        raise NotFoundError(
            f"Note not found: {topic}"
        )

    return row


def get_note_by_id(
    conn: sqlite3.Connection,
    note_id: int,
) -> sqlite3.Row:

    row = conn.execute(
        """
        SELECT *
        FROM notes
        WHERE id = ?
        """,
        (note_id,),
    ).fetchone()

    if row is None:
        raise NotFoundError(
            f"Note ID not found: {note_id}"
        )

    return row


def get_profile_by_name(
    conn: sqlite3.Connection,
    name: str,
) -> sqlite3.Row:

    row = conn.execute(
        """
        SELECT *
        FROM agent_profiles
        WHERE name = ?
        """,
        (name,),
    ).fetchone()

    if row is None:
        raise NotFoundError(
            f"Agent profile not found: {name}"
        )

    return row


def get_thread(
    conn: sqlite3.Connection,
    thread_id: int,
) -> sqlite3.Row:

    row = conn.execute(
        """
        SELECT
            t.*,
            n.topic AS note_topic
        FROM topics_threads t
        LEFT JOIN notes n
            ON n.id = t.note_id
        WHERE t.id = ?
        """,
        (thread_id,),
    ).fetchone()

    if row is None:
        raise NotFoundError(
            f"Thread not found: {thread_id}"
        )

    return row


def would_create_cycle(
    conn: sqlite3.Connection,
    child_id: int,
    proposed_parent_id: int,
) -> bool:

    if child_id == proposed_parent_id:
        return True

    row = conn.execute(
        """
        WITH RECURSIVE ancestors(id) AS (
            SELECT parent_id
            FROM notes
            WHERE id = ?

            UNION ALL

            SELECT n.parent_id
            FROM notes n
            JOIN ancestors a
                ON n.id = a.id
            WHERE a.id IS NOT NULL
        )
        SELECT 1
        FROM ancestors
        WHERE id = ?
        LIMIT 1
        """,
        (
            proposed_parent_id,
            child_id,
        ),
    ).fetchone()

    return row is not None


def resolve_parent_id(
    conn: sqlite3.Connection,
    parent_topic: Optional[str],
    current_note_id: Optional[int] = None,
) -> Optional[int]:

    if parent_topic is None:
        return None

    parent_topic = validate_nonempty(
        parent_topic,
        "parent_topic",
        cfg.MAX_TOPIC_SIZE,
    )

    row = conn.execute(
        """
        SELECT id
        FROM notes
        WHERE topic = ?
        """,
        (parent_topic,),
    ).fetchone()

    if row is None:
        raise NotFoundError(
            f"Parent note not found: {parent_topic}"
        )

    parent_id = int(row["id"])

    if current_note_id is not None:
        if would_create_cycle(
            conn,
            current_note_id,
            parent_id,
        ):
            raise CycleError(
                "Changing the parent would create "
                "a hierarchy cycle"
            )

    return parent_id

