# BBMCPS

import logging

@blackboard.tool()
def save_note(
    topic: str,
    content: str,
    category: str = "general",
    parent_topic: Optional[str] = None,
    agent_profile_name: Optional[str] = None,
) -> str:

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
        logging.exception("save_note failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_note(
    topic: str,
) -> str:

    try:
        result = get_note_impl(topic)

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logging.exception("get_note failed")

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
        logging.exception("delete_note failed")

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
        logging.exception("search_notes failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_ancestors(
    topic: str,
) -> str:

    try:
        result = get_ancestors_impl(topic)

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logging.exception("get_ancestors failed")

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
        logging.exception("get_descendants failed")

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
        logging.exception("traverse_notes failed")

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
        logging.exception("link_notes failed")

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
        logging.exception("unlink_notes failed")

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
        logging.exception("add_external_link failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def remove_external_link(
    link_id: int,
) -> str:

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
        logging.exception("remove_external_link failed")

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
        logging.exception("save_agent_profile failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_agent_profile(
    name: str,
) -> str:

    try:
        result = get_agent_profile_impl(name)

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logging.exception("get_agent_profile failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def list_agent_profiles() -> str:

    try:
        result = list_agent_profiles_impl()

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logging.exception("list_agent_profiles failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def delete_agent_profile(
    name: str,
) -> str:

    try:
        result = delete_agent_profile_impl(name)

        return json_result(
            True,
            "Agent profile deleted",
            **result,
        )

    except Exception as exc:
        logging.exception("delete_agent_profile failed")

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
        logging.exception("create_thread failed")

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
        logging.exception("post_comment failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_thread(
    thread_id: int,
) -> str:

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
        logging.exception("get_thread failed")

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
        logging.exception("list_threads failed")

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
        logging.exception(
            "update_thread_status failed"
        )

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )


@blackboard.tool()
def get_statistics() -> str:

    try:
        result = stats_impl()

        return json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

    except Exception as exc:
        logging.exception(
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

    try:
        result = render_tree_impl(
            root_topic,
            max_depth,
        )

        return result

    except Exception as exc:
        logging.exception("get_tree failed")

        return json_result(
            False,
            str(exc),
            error_type=type(exc).__name__,
        )
