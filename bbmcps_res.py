# BBMCPS

import json
import logging
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional
from urllib.parse import urlparse
import mcp
from mcp.server import MCPServer

logger = log.get_logger()

@blackboard.resource("blackboard://tree")
def resource_tree() -> str:
    """
    Return the complete note hierarchy as an indented tree.
    """
    return render_tree_impl()


@blackboard.resource("blackboard://agent-profiles")
def resource_agent_profiles() -> str:
    """
    Return all registered agent profiles.
    """
    result = list_agent_profiles_impl()

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


@blackboard.resource("blackboard://stats")
def resource_stats() -> str:
    """
    Return database statistics.
    """
    return json.dumps(
        stats_impl(),
        ensure_ascii=False,
        indent=2,
    )


@blackboard.resource("blackboard://recent")
def resource_recent() -> str:
    """
    Return recently updated notes.
    """
    with db.connection() as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                topic,
                category,
                updated_at
            FROM notes
            ORDER BY updated_at DESC
            LIMIT 50
            """
        ).fetchall()

        result = {
            "count": len(rows),
            "notes": rows_to_dicts(rows),
        }

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )


@blackboard.resource("blackboard://threads")
def resource_threads() -> str:
    """
    Return recently updated discussion threads.
    """
    result = list_threads_impl(
        limit=50
    )

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
