# Blackboard MCP Server
#
#   Requirements
#       Python 3.10+
#       mcp >= 2.x
#
#   Environment variables:
#       BLACKBOARD_DB
#       BLACKBOARD_LOG_LEVEL
#       BLACKBOARD_MAX_CONTENT_SIZE
#       BLACKBOARD_MAX_COMMENT_SIZE
#       BLACKBOARD_MAX_PROMPT_SIZE

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
import bbmcps_cfg as cfg
import bbmcps_log as log
import bbmcps_fn as fn
import bbmcps_db as db
import bbmcps_impl as impl

db = fn.get_db()
logger = log.get_logger()

blackboard = MCPServer(
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


# ============================================================================
# MCP Resources
# ============================================================================

@blackboard.resource("blackboard://tree")
def resource_tree() -> str:
    """
    Return the complete note hierarchy as an indented tree.
    """
    return impl.render_tree_impl()


@blackboard.resource("blackboard://agent-profiles")
def resource_agent_profiles() -> str:
    """
    Return all registered agent profiles.
    """
    result = impl.list_agent_profiles_impl()

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
        impl.stats_impl(),
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
    result = impl.list_threads_impl(
        limit=50
    )

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


# ============================================================================
# MCP Tools
# ============================================================================

@blackboard.tool()
def save_note(
    topic: str,
    content: str,
    category: str = "general",
    parent_topic: Optional[str] = None,
    agent_profile_name: Optional[str] = None,
) -> str:
    """
    Create or update a persistent knowledge note.

    If the topic does not exist it is created.
    If it exists it is updated.

    parent_topic optionally places the note underneath another note.
    agent_profile_name optionally associates an agent profile.
    """
    try:
        result = impl.save_note_impl(
            topic=topic,
            content=content,
            category=category,
            parent_topic=parent_topic,
            agent_profile_name=agent_profile_name,
        )

        return json_result(
            True,
            f"Note {result['operation']}",
            **result,
        )

    except Exception as exc:
        logger.exception("save_note failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_note(
    topic: str,
) -> str:
    """
    Retrieve a note together with children, relations and external links.
    """
    try:
        result = impl.get_note_impl(topic)

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("get_note failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def delete_note(
    topic: str,
    cascade: bool = False,
) -> str:
    """
    Delete a note.

    With cascade=false, deletion fails if the note has children.

    With cascade=true, the complete descendant subtree is deleted.
    Relations and external links are automatically removed by SQLite
    foreign-key cascades.
    """
    try:
        result = impl.delete_note_impl(
            topic,
            cascade,
        )

        return json_result(
            True,
            "Note deleted",
            **result,
        )

    except Exception as exc:
        logger.exception("delete_note failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def search_notes(
    query: str,
    category: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    Search notes using SQLite FTS5 when available, otherwise LIKE search.
    """
    try:
        result = impl.search_notes_impl(
            query,
            category,
            limit,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("search_notes failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_ancestors(
    topic: str,
) -> str:
    """
    Return the complete parent chain of a note.
    """
    try:
        result = impl.get_ancestors_impl(topic)

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("get_ancestors failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_descendants(
    topic: str,
    depth: int = 10,
) -> str:
    """
    Return descendants of a note up to a specified hierarchy depth.
    """
    try:
        result = impl.get_descendants_impl(
            topic,
            depth,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("get_descendants failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def traverse_notes(
    topic: str,
    depth: int = 2,
    include_children: bool = True,
    include_relations: bool = True,
) -> str:
    """
    Traverse the knowledge graph starting at a note.

    Traversal can include hierarchical child edges and graph relations.
    """
    try:
        result = impl.traverse_notes_impl(
            topic=topic,
            depth=depth,
            include_children=include_children,
            include_relations=include_relations,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("traverse_notes failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def link_notes(
    source_topic: str,
    target_topic: str,
) -> str:
    """
    Create a directed many-to-many relation from source to target.
    """
    try:
        result = impl.link_notes_impl(
            source_topic,
            target_topic,
        )

        return json_result(
            True,
            "Relation processed",
            **result,
        )

    except Exception as exc:
        logger.exception("link_notes failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def unlink_notes(
    source_topic: str,
    target_topic: str,
) -> str:
    """
    Remove a directed relation from source to target.
    """
    try:
        result = impl.unlink_notes_impl(
            source_topic,
            target_topic,
        )

        return json_result(
            True,
            "Relation removal processed",
            **result,
        )

    except Exception as exc:
        logger.exception("unlink_notes failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def add_external_link(
    note_topic: str,
    url: str,
    description: Optional[str] = None,
) -> str:
    """
    Attach an HTTP(S) external URL to a note.
    """
    try:
        result = impl.add_external_link_impl(
            note_topic,
            url,
            description,
        )

        return json_result(
            True,
            "External link created",
            **result,
        )

    except Exception as exc:
        logger.exception("add_external_link failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def remove_external_link(
    link_id: int,
) -> str:
    """
    Remove an external link by ID.
    """
    try:
        result = impl.remove_external_link_impl(
            link_id,
        )

        return json_result(
            True,
            "External link deleted",
            **result,
        )

    except Exception as exc:
        logger.exception("remove_external_link failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def save_agent_profile(
    name: str,
    system_prompt: str,
) -> str:
    """
    Create or update an agent profile containing a system prompt.
    """
    try:
        result = impl.save_agent_profile_impl(
            name,
            system_prompt,
        )

        return json_result(
            True,
            f"Agent profile {result['operation']}",
            **result,
        )

    except Exception as exc:
        logger.exception("save_agent_profile failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_agent_profile(
    name: str,
) -> str:
    """
    Retrieve one agent profile.
    """
    try:
        result = impl.get_agent_profile_impl(name)

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("get_agent_profile failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def list_agent_profiles() -> str:
    """
    List all available agent profiles.
    """
    try:
        result = impl.list_agent_profiles_impl()

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("list_agent_profiles failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def delete_agent_profile(
    name: str,
) -> str:
    """
    Delete an agent profile.

    Existing notes keep their content but their profile reference
    becomes NULL because of ON DELETE SET NULL.
    """
    try:
        result = impl.delete_agent_profile_impl(name)

        return json_result(
            True,
            "Agent profile deleted",
            **result,
        )

    except Exception as exc:
        logger.exception("delete_agent_profile failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def create_thread(
    title: str,
    note_topic: Optional[str] = None,
) -> str:
    """
    Create a persistent discussion thread.

    Optionally associate the discussion with a note.
    """
    try:
        result = impl.create_thread_impl(
            title,
            note_topic,
        )

        return json_result(
            True,
            "Discussion thread created",
            **result,
        )

    except Exception as exc:
        logger.exception("create_thread failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def post_comment(
    thread_id: int,
    comment: str,
    author: str = "Unknown",
) -> str:
    """
    Add a persistent comment to a discussion thread.
    """
    try:
        result = impl.post_comment_impl(
            thread_id,
            comment,
            author,
        )

        return json_result(
            True,
            "Comment created",
            **result,
        )

    except Exception as exc:
        logger.exception("post_comment failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_thread(
    thread_id: int,
) -> str:
    """
    Retrieve a discussion thread and all comments.
    """
    try:
        result = impl.get_thread_impl(
            thread_id,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("get_thread failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def list_threads(
    status: Optional[str] = None,
    note_topic: Optional[str] = None,
    limit: int = 50,
) -> str:
    """
    List discussion threads.
    """
    try:
        result = impl.list_threads_impl(
            status=status,
            note_topic=note_topic,
            limit=limit,
        )

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception("list_threads failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def update_thread_status(
    thread_id: int,
    status: str,
) -> str:
    """
    Change a discussion thread status.

    Valid statuses:
        open
        resolved
        archived
    """
    try:
        result = impl.update_thread_status_impl(
            thread_id,
            status,
        )

        return json_result(
            True,
            "Thread status updated",
            **result,
        )

    except Exception as exc:
        logger.exception(
            "update_thread_status failed"
        )

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_statistics() -> str:
    """
    Return Blackboard database statistics.
    """
    try:
        result = impl.stats_impl()

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logger.exception(
            "get_statistics failed"
        )

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_tree(
    root_topic: Optional[str] = None,
    max_depth: int = 100,
) -> str:
    """
    Return the note hierarchy as an indented tree.

    If root_topic is omitted, all root trees are returned.
    """
    try:
        result = impl.render_tree_impl(
            root_topic,
            max_depth,
        )

        return result

    except Exception as exc:
        logger.exception("get_tree failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )

if __name__ == "__main__":

    logger = log.get_logger()
    logger.info(
        "%s %s starting",
        cfg.SERVER_NAME,
        cfg.SERVER_VERSION,
    )

    logger.info(
        "Python MCP package version: %s",
        getattr(mcp, "__version__", "2.0"),
    )

    logger.info(
        "Database: %s",
        cfg.DB_PATH,
    )

    blackboard.run(transport="stdio")
