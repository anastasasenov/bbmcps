# BBMCPS

@blackboard.resource("blackboard://tree")
def resource_tree() -> str:

    return render_tree_impl()


@blackboard.resource("blackboard://agent-profiles")
def resource_agent_profiles() -> str:

    result = list_agent_profiles_impl()

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )


@blackboard.resource("blackboard://stats")
def resource_stats() -> str:

    return json.dumps(
        stats_impl(),
        ensure_ascii=False,
        indent=2,
    )


@blackboard.resource("blackboard://recent")
def resource_recent() -> str:

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

    result = list_threads_impl(
        limit=50
    )

    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )
