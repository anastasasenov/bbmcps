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
import bbmcps_log as log

logger = log.get_logger()

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
        result = save_note_impl(
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
        result = get_note_impl(topic)

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
        result = delete_note_impl(
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
        result = search_notes_impl(
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
        result = get_ancestors_impl(topic)

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
        result = get_descendants_impl(
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
        result = traverse_notes_impl(
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
        result = link_notes_impl(
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
        result = unlink_notes_impl(
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
        result = add_external_link_impl(
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
        result = remove_external_link_impl(
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
        result = save_agent_profile_impl(
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
        result = get_agent_profile_impl(name)

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
        result = list_agent_profiles_impl()

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
        result = delete_agent_profile_impl(name)

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
        result = create_thread_impl(
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
        result = post_comment_impl(
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
        result = get_thread_impl(
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
        result = list_threads_impl(
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
        result = update_thread_status_impl(
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
        result = stats_impl()

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
        result = render_tree_impl(
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
