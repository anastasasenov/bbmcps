# BBMCPS

def save_note_impl(
    topic: str,
    content: str,
    category: str = "general",
    parent_topic: Optional[str] = None,
    agent_profile_name: Optional[str] = None,
) -> dict[str, Any]:

    topic = validate_nonempty(
        topic,
        "topic",
        MAX_TOPIC_SIZE,
    )

    if not isinstance(content, str):
        raise ValidationError(
            "content must be a string"
        )

    if len(content) > MAX_CONTENT_SIZE:
        raise ValidationError(
            f"content exceeds maximum size "
            f"of {MAX_CONTENT_SIZE} bytes/characters"
        )

    category = validate_nonempty(
        category,
        "category",
        128,
    ).lower()

    agent_profile_name = validate_optional_text(
        agent_profile_name,
        "agent_profile_name",
        256,
    )

    with db.connection() as conn:

        existing = conn.execute(
            """
            SELECT id
            FROM notes
            WHERE topic = ?
            """,
            (topic,),
        ).fetchone()

        now = utc_now()

        if existing is None:

            parent_id = resolve_parent_id(
                conn,
                parent_topic,
            )

            profile_id = None

            if agent_profile_name:
                profile_id = get_profile_by_name(
                    conn,
                    agent_profile_name,
                )["id"]

            cursor = conn.execute(
                """
                INSERT INTO notes (
                    topic,
                    content,
                    category,
                    parent_id,
                    agent_profile_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    topic,
                    content,
                    category,
                    parent_id,
                    profile_id,
                    now,
                    now,
                ),
            )

            conn.commit()

            return {
                "operation": "created",
                "id": cursor.lastrowid,
                "topic": topic,
            }

        note_id = int(existing["id"])

        parent_id = resolve_parent_id(
            conn,
            parent_topic,
            current_note_id=note_id,
        )

        profile_id = None

        if agent_profile_name:
            profile_id = get_profile_by_name(
                conn,
                agent_profile_name,
            )["id"]

        if parent_topic is None:
            conn.execute(
                """
                UPDATE notes
                SET
                    content = ?,
                    category = ?,
                    agent_profile_id = COALESCE(?, agent_profile_id),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    content,
                    category,
                    profile_id,
                    now,
                    note_id,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE notes
                SET
                    content = ?,
                    category = ?,
                    parent_id = ?,
                    agent_profile_id = COALESCE(?, agent_profile_id),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    content,
                    category,
                    parent_id,
                    profile_id,
                    now,
                    note_id,
                ),
            )

        conn.commit()

        return {
            "operation": "updated",
            "id": note_id,
            "topic": topic,
        }


def get_note_impl(
    topic: str,
) -> dict[str, Any]:

    topic = validate_nonempty(
        topic,
        "topic",
        MAX_TOPIC_SIZE,
    )

    with db.connection() as conn:

        note = get_note_row(
            conn,
            topic,
        )

        note_id = int(note["id"])

        children = conn.execute(
            """
            SELECT id, topic, category, updated_at
            FROM notes
            WHERE parent_id = ?
            ORDER BY topic COLLATE NOCASE
            """,
            (note_id,),
        ).fetchall()

        relations = conn.execute(
            """
            SELECT
                r.source_id,
                r.target_id,
                s.topic AS source_topic,
                t.topic AS target_topic,
                r.created_at
            FROM note_relations r
            JOIN notes s
                ON s.id = r.source_id
            JOIN notes t
                ON t.id = r.target_id
            WHERE
                r.source_id = ?
                OR r.target_id = ?
            ORDER BY
                s.topic COLLATE NOCASE,
                t.topic COLLATE NOCASE
            """,
            (
                note_id,
                note_id,
            ),
        ).fetchall()

        links = conn.execute(
            """
            SELECT
                id,
                url,
                description,
                created_at
            FROM external_links
            WHERE note_id = ?
            ORDER BY id
            """,
            (note_id,),
        ).fetchall()

        return {
            "note": row_to_dict(note),
            "children": rows_to_dicts(children),
            "relations": rows_to_dicts(relations),
            "external_links": rows_to_dicts(links),
        }


def delete_note_impl(
    topic: str,
    cascade: bool = False,
) -> dict[str, Any]:

    topic = validate_nonempty(
        topic,
        "topic",
        MAX_TOPIC_SIZE,
    )

    with db.connection() as conn:

        note = get_note_row(
            conn,
            topic,
        )

        note_id = int(note["id"])

        children_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM notes
            WHERE parent_id = ?
            """,
            (note_id,),
        ).fetchone()[0]

        if children_count > 0 and not cascade:
            raise ConflictError(
                f"Note '{topic}' has "
                f"{children_count} child notes. "
                f"Use cascade=true to recursively delete."
            )

        if cascade:
            descendants = conn.execute(
                """
                WITH RECURSIVE descendants(id) AS (
                    SELECT id
                    FROM notes
                    WHERE id = ?

                    UNION ALL

                    SELECT n.id
                    FROM notes n
                    JOIN descendants d
                        ON n.parent_id = d.id
                )
                SELECT id
                FROM descendants
                """,
                (note_id,),
            ).fetchall()

            ids = [
                int(row["id"])
                for row in descendants
            ]

            conn.execute(
                """
                DELETE FROM notes
                WHERE id IN (
                    WITH RECURSIVE descendants(id) AS (
                        SELECT id
                        FROM notes
                        WHERE id = ?

                        UNION ALL

                        SELECT n.id
                        FROM notes n
                        JOIN descendants d
                            ON n.parent_id = d.id
                    )
                    SELECT id
                    FROM descendants
                )
                """,
                (note_id,),
            )

            conn.commit()

            return {
                "operation": "deleted",
                "topic": topic,
                "cascade": True,
                "deleted_note_count": len(ids),
            }

        conn.execute(
            """
            DELETE FROM notes
            WHERE id = ?
            """,
            (note_id,),
        )

        conn.commit()

        return {
            "operation": "deleted",
            "topic": topic,
            "cascade": False,
            "deleted_note_count": 1,
        }


def search_notes_impl(
    query: str,
    category: Optional[str] = None,
    limit: int = 20,
) -> dict[str, Any]:

    query = validate_nonempty(
        query,
        "query",
        1024,
    )

    if limit < 1:
        raise ValidationError(
            "limit must be >= 1"
        )

    limit = min(
        limit,
        MAX_SEARCH_RESULTS,
    )

    category = validate_optional_text(
        category,
        "category",
        128,
    )

    with db.connection() as conn:

        fts_exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'notes_fts'
            """
        ).fetchone()

        rows: list[sqlite3.Row]

        if fts_exists:

            tokens = re.findall(
                r"[A-Za-z0-9_]+",
                query,
            )

            if tokens:

                fts_query = " AND ".join(
                    f'"{token}"'
                    for token in tokens
                )

                if category:

                    rows = conn.execute(
                        """
                        SELECT
                            n.*,
                            bm25(notes_fts) AS rank
                        FROM notes_fts
                        JOIN notes n
                            ON n.id = notes_fts.rowid
                        WHERE notes_fts MATCH ?
                          AND n.category = ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (
                            fts_query,
                            category,
                            limit,
                        ),
                    ).fetchall()

                else:

                    rows = conn.execute(
                        """
                        SELECT
                            n.*,
                            bm25(notes_fts) AS rank
                        FROM notes_fts
                        JOIN notes n
                            ON n.id = notes_fts.rowid
                        WHERE notes_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                        """,
                        (
                            fts_query,
                            limit,
                        ),
                    ).fetchall()

            else:
                rows = []

        else:

            pattern = f"%{query}%"

            if category:

                rows = conn.execute(
                    """
                    SELECT *
                    FROM notes
                    WHERE category = ?
                      AND (
                          topic LIKE ?
                          OR content LIKE ?
                      )
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (
                        category,
                        pattern,
                        pattern,
                        limit,
                    ),
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT *
                    FROM notes
                    WHERE
                        topic LIKE ?
                        OR content LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (
                        pattern,
                        pattern,
                        limit,
                    ),
                ).fetchall()

        return {
            "query": query,
            "count": len(rows),
            "results": rows_to_dicts(rows),
        }


def get_ancestors_impl(
    topic: str,
) -> dict[str, Any]:

    topic = validate_nonempty(
        topic,
        "topic",
        MAX_TOPIC_SIZE,
    )

    with db.connection() as conn:

        note = get_note_row(
            conn,
            topic,
        )

        rows = conn.execute(
            """
            WITH RECURSIVE ancestors AS (
                SELECT
                    n.id,
                    n.topic,
                    n.parent_id,
                    0 AS distance
                FROM notes n
                WHERE n.id = ?

                UNION ALL

                SELECT
                    p.id,
                    p.topic,
                    p.parent_id,
                    a.distance + 1
                FROM notes p
                JOIN ancestors a
                    ON p.id = a.parent_id
            )
            SELECT
                id,
                topic,
                parent_id,
                distance
            FROM ancestors
            ORDER BY distance DESC
            """,
            (int(note["id"]),),
        ).fetchall()

        return {
            "topic": topic,
            "ancestors": rows_to_dicts(rows),
        }


def get_descendants_impl(
    topic: str,
    depth: int = 10,
) -> dict[str, Any]:

    topic = validate_nonempty(
        topic,
        "topic",
        MAX_TOPIC_SIZE,
    )

    if depth < 0:
        raise ValidationError(
            "depth must be >= 0"
        )

    depth = min(depth, 1000)

    with db.connection() as conn:

        note = get_note_row(
            conn,
            topic,
        )

        rows = conn.execute(
            """
            WITH RECURSIVE descendants AS (
                SELECT
                    n.id,
                    n.topic,
                    n.parent_id,
                    n.category,
                    0 AS depth
                FROM notes n
                WHERE n.id = ?

                UNION ALL

                SELECT
                    child.id,
                    child.topic,
                    child.parent_id,
                    child.category,
                    d.depth + 1
                FROM notes child
                JOIN descendants d
                    ON child.parent_id = d.id
                WHERE d.depth < ?
            )
            SELECT
                id,
                topic,
                parent_id,
                category,
                depth
            FROM descendants
            WHERE depth > 0
            ORDER BY depth, topic COLLATE NOCASE
            """,
            (
                int(note["id"]),
                depth,
            ),
        ).fetchall()

        return {
            "topic": topic,
            "depth_limit": depth,
            "count": len(rows),
            "descendants": rows_to_dicts(rows),
        }


def traverse_notes_impl(
    topic: str,
    depth: int = 2,
    include_children: bool = True,
    include_relations: bool = True,
) -> dict[str, Any]:

    topic = validate_nonempty(
        topic,
        "topic",
        MAX_TOPIC_SIZE,
    )

    if depth < 0:
        raise ValidationError(
            "depth must be >= 0"
        )

    depth = min(depth, 100)

    with db.connection() as conn:

        root = get_note_row(
            conn,
            topic,
        )

        root_id = int(root["id"])

        visited: set[int] = {root_id}

        nodes: list[dict[str, Any]] = [
            {
                "id": root_id,
                "topic": root["topic"],
                "category": root["category"],
                "depth": 0,
            }
        ]

        frontier: list[tuple[int, int]] = [
            (root_id, 0)
        ]

        edges: list[dict[str, Any]] = []

        while frontier:

            current_id, current_depth = frontier.pop(0)

            if current_depth >= depth:
                continue

            neighbors: list[tuple[int, str]] = []

            if include_children:

                child_rows = conn.execute(
                    """
                    SELECT id
                    FROM notes
                    WHERE parent_id = ?
                    ORDER BY topic COLLATE NOCASE
                    """,
                    (current_id,),
                ).fetchall()

                for row in child_rows:
                    neighbors.append(
                        (
                            int(row["id"]),
                            "child",
                        )
                    )

            if include_relations:

                relation_rows = conn.execute(
                    """
                    SELECT
                        CASE
                            WHEN source_id = ?
                            THEN target_id
                            ELSE source_id
                        END AS neighbor_id,

                        CASE
                            WHEN source_id = ?
                            THEN 'relation_out'
                            ELSE 'relation_in'
                        END AS relation_kind
                    FROM note_relations
                    WHERE source_id = ?
                       OR target_id = ?
                    """,
                    (
                        current_id,
                        current_id,
                        current_id,
                        current_id,
                    ),
                ).fetchall()

                for row in relation_rows:
                    neighbors.append(
                        (
                            int(row["neighbor_id"]),
                            row["relation_kind"],
                        )
                    )

            for neighbor_id, edge_type in neighbors:

                neighbor = get_note_by_id(
                    conn,
                    neighbor_id,
                )

                edges.append(
                    {
                        "source_id": current_id,
                        "target_id": neighbor_id,
                        "type": edge_type,
                    }
                )

                if neighbor_id not in visited:

                    visited.add(neighbor_id)

                    node = {
                        "id": neighbor_id,
                        "topic": neighbor["topic"],
                        "category": neighbor["category"],
                        "depth": current_depth + 1,
                    }

                    nodes.append(node)

                    frontier.append(
                        (
                            neighbor_id,
                            current_depth + 1,
                        )
                    )

        return {
            "root": topic,
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
        }


def link_notes_impl(
    source_topic: str,
    target_topic: str,
) -> dict[str, Any]:

    source_topic = validate_nonempty(
        source_topic,
        "source_topic",
        MAX_TOPIC_SIZE,
    )

    target_topic = validate_nonempty(
        target_topic,
        "target_topic",
        MAX_TOPIC_SIZE,
    )

    with db.connection() as conn:

        source = get_note_row(
            conn,
            source_topic,
        )

        target = get_note_row(
            conn,
            target_topic,
        )

        source_id = int(source["id"])
        target_id = int(target["id"])

        if source_id == target_id:
            raise ValidationError(
                "A note cannot be related to itself"
            )

        existing = conn.execute(
            """
            SELECT 1
            FROM note_relations
            WHERE source_id = ?
              AND target_id = ?
            """,
            (
                source_id,
                target_id,
            ),
        ).fetchone()

        if existing:
            return {
                "operation": "already_exists",
                "source": source_topic,
                "target": target_topic,
            }

        conn.execute(
            """
            INSERT INTO note_relations (
                source_id,
                target_id,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                source_id,
                target_id,
                utc_now(),
            ),
        )

        conn.commit()

        return {
            "operation": "created",
            "source": source_topic,
            "target": target_topic,
        }


def unlink_notes_impl(
    source_topic: str,
    target_topic: str,
) -> dict[str, Any]:

    source_topic = validate_nonempty(
        source_topic,
        "source_topic",
        MAX_TOPIC_SIZE,
    )

    target_topic = validate_nonempty(
        target_topic,
        "target_topic",
        MAX_TOPIC_SIZE,
    )

    with db.connection() as conn:

        source = get_note_row(
            conn,
            source_topic,
        )

        target = get_note_row(
            conn,
            target_topic,
        )

        cursor = conn.execute(
            """
            DELETE FROM note_relations
            WHERE source_id = ?
              AND target_id = ?
            """,
            (
                source["id"],
                target["id"],
            ),
        )

        conn.commit()

        if cursor.rowcount == 0:
            return {
                "operation": "not_found",
                "source": source_topic,
                "target": target_topic,
            }

        return {
            "operation": "deleted",
            "source": source_topic,
            "target": target_topic,
        }


def add_external_link_impl(
    note_topic: str,
    url: str,
    description: Optional[str] = None,
) -> dict[str, Any]:

    note_topic = validate_nonempty(
        note_topic,
        "note_topic",
        MAX_TOPIC_SIZE,
    )

    url = validate_url(url)

    description = validate_optional_text(
        description,
        "description",
        4096,
    )

    with db.connection() as conn:

        note = get_note_row(
            conn,
            note_topic,
        )

        cursor = conn.execute(
            """
            INSERT INTO external_links (
                note_id,
                url,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                note["id"],
                url,
                description,
                utc_now(),
            ),
        )

        conn.commit()

        return {
            "operation": "created",
            "id": cursor.lastrowid,
            "note_topic": note_topic,
            "url": url,
        }


def remove_external_link_impl(
    link_id: int,
) -> dict[str, Any]:

    if link_id < 1:
        raise ValidationError(
            "link_id must be positive"
        )

    with db.connection() as conn:

        cursor = conn.execute(
            """
            DELETE FROM external_links
            WHERE id = ?
            """,
            (link_id,),
        )

        conn.commit()

        if cursor.rowcount == 0:
            raise NotFoundError(
                f"External link not found: {link_id}"
            )

        return {
            "operation": "deleted",
            "id": link_id,
        }


def save_agent_profile_impl(
    name: str,
    system_prompt: str,
) -> dict[str, Any]:

    name = validate_nonempty(
        name,
        "name",
        256,
    )

    if not isinstance(system_prompt, str):
        raise ValidationError(
            "system_prompt must be a string"
        )

    if not system_prompt.strip():
        raise ValidationError(
            "system_prompt cannot be empty"
        )

    if len(system_prompt) > MAX_PROMPT_SIZE:
        raise ValidationError(
            f"system_prompt exceeds maximum size "
            f"of {MAX_PROMPT_SIZE}"
        )

    with db.connection() as conn:

        existing = conn.execute(
            """
            SELECT id
            FROM agent_profiles
            WHERE name = ?
            """,
            (name,),
        ).fetchone()

        now = utc_now()

        if existing is None:

            cursor = conn.execute(
                """
                INSERT INTO agent_profiles (
                    name,
                    system_prompt,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    system_prompt,
                    now,
                    now,
                ),
            )

            conn.commit()

            return {
                "operation": "created",
                "id": cursor.lastrowid,
                "name": name,
            }

        profile_id = int(existing["id"])

        conn.execute(
            """
            UPDATE agent_profiles
            SET
                system_prompt = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                system_prompt,
                now,
                profile_id,
            ),
        )

        conn.commit()

        return {
            "operation": "updated",
            "id": profile_id,
            "name": name,
        }


def get_agent_profile_impl(
    name: str,
) -> dict[str, Any]:

    name = validate_nonempty(
        name,
        "name",
        256,
    )

    with db.connection() as conn:

        row = get_profile_by_name(
            conn,
            name,
        )

        return {
            "profile": row_to_dict(row),
        }


def list_agent_profiles_impl() -> dict[str, Any]:

    with db.connection() as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                name,
                system_prompt,
                created_at,
                updated_at
            FROM agent_profiles
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()

        return {
            "count": len(rows),
            "profiles": rows_to_dicts(rows),
        }


def delete_agent_profile_impl(
    name: str,
) -> dict[str, Any]:

    name = validate_nonempty(
        name,
        "name",
        256,
    )

    with db.connection() as conn:

        row = get_profile_by_name(
            conn,
            name,
        )

        conn.execute(
            """
            DELETE FROM agent_profiles
            WHERE id = ?
            """,
            (row["id"],),
        )

        conn.commit()

        return {
            "operation": "deleted",
            "name": name,
        }


VALID_THREAD_STATUSES = {
    "open",
    "resolved",
    "archived",
}


def create_thread_impl(
    title: str,
    note_topic: Optional[str] = None,
) -> dict[str, Any]:

    title = validate_nonempty(
        title,
        "title",
        1024,
    )

    note_topic = validate_optional_text(
        note_topic,
        "note_topic",
        MAX_TOPIC_SIZE,
    )

    with db.connection() as conn:

        note_id = None

        if note_topic:
            note = get_note_row(
                conn,
                note_topic,
            )

            note_id = note["id"]

        now = utc_now()

        cursor = conn.execute(
            """
            INSERT INTO topics_threads (
                note_id,
                title,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, 'open', ?, ?)
            """,
            (
                note_id,
                title,
                now,
                now,
            ),
        )

        conn.commit()

        return {
            "operation": "created",
            "thread_id": cursor.lastrowid,
            "title": title,
            "status": "open",
            "note_topic": note_topic,
        }


def post_comment_impl(
    thread_id: int,
    comment: str,
    author: str = "Unknown",
) -> dict[str, Any]:

    if thread_id < 1:
        raise ValidationError(
            "thread_id must be positive"
        )

    comment = validate_nonempty(
        comment,
        "comment",
        MAX_COMMENT_SIZE,
    )

    author = validate_nonempty(
        author,
        "author",
        256,
    )

    with db.connection() as conn:

        thread = get_thread(
            conn,
            thread_id,
        )

        if thread["status"] == "archived":
            raise ConflictError(
                "Cannot post to an archived thread"
            )

        now = utc_now()

        cursor = conn.execute(
            """
            INSERT INTO discussions (
                thread_id,
                author,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                thread_id,
                author,
                comment,
                now,
            ),
        )

        conn.execute(
            """
            UPDATE topics_threads
            SET updated_at = ?
            WHERE id = ?
            """,
            (
                now,
                thread_id,
            ),
        )

        conn.commit()

        return {
            "operation": "created",
            "comment_id": cursor.lastrowid,
            "thread_id": thread_id,
            "author": author,
        }


def update_thread_status_impl(
    thread_id: int,
    status: str,
) -> dict[str, Any]:

    if thread_id < 1:
        raise ValidationError(
            "thread_id must be positive"
        )

    status = validate_nonempty(
        status,
        "status",
        32,
    ).lower()

    if status not in VALID_THREAD_STATUSES:
        raise ValidationError(
            "status must be one of: "
            + ", ".join(
                sorted(VALID_THREAD_STATUSES)
            )
        )

    with db.connection() as conn:

        get_thread(
            conn,
            thread_id,
        )

        conn.execute(
            """
            UPDATE topics_threads
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                utc_now(),
                thread_id,
            ),
        )

        conn.commit()

        return {
            "operation": "updated",
            "thread_id": thread_id,
            "status": status,
        }


def get_thread_impl(
    thread_id: int,
) -> dict[str, Any]:

    if thread_id < 1:
        raise ValidationError(
            "thread_id must be positive"
        )

    with db.connection() as conn:

        thread = get_thread(
            conn,
            thread_id,
        )

        comments = conn.execute(
            """
            SELECT
                id,
                author,
                comment,
                created_at
            FROM discussions
            WHERE thread_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (thread_id,),
        ).fetchall()

        return {
            "thread": row_to_dict(thread),
            "comments": rows_to_dicts(comments),
        }


def list_threads_impl(
    status: Optional[str] = None,
    note_topic: Optional[str] = None,
    limit: int = 50,
) -> dict[str, Any]:

    if limit < 1:
        raise ValidationError(
            "limit must be >= 1"
        )

    limit = min(
        limit,
        MAX_SEARCH_RESULTS,
    )

    status = validate_optional_text(
        status,
        "status",
        32,
    )

    note_topic = validate_optional_text(
        note_topic,
        "note_topic",
        MAX_TOPIC_SIZE,
    )

    if status and status not in VALID_THREAD_STATUSES:
        raise ValidationError(
            "Invalid thread status"
        )

    with db.connection() as conn:

        sql = """
            SELECT
                t.id,
                t.title,
                t.status,
                t.note_id,
                n.topic AS note_topic,
                t.created_at,
                t.updated_at
            FROM topics_threads t
            LEFT JOIN notes n
                ON n.id = t.note_id
            WHERE 1 = 1
        """

        params: list[Any] = []

        if status:
            sql += """
                AND t.status = ?
            """
            params.append(status)

        if note_topic:
            sql += """
                AND n.topic = ?
            """
            params.append(note_topic)

        sql += """
            ORDER BY t.updated_at DESC
            LIMIT ?
        """

        params.append(limit)

        rows = conn.execute(
            sql,
            params,
        ).fetchall()

        return {
            "count": len(rows),
            "threads": rows_to_dicts(rows),
        }


def stats_impl() -> dict[str, Any]:

    with db.connection() as conn:

        notes = conn.execute(
            "SELECT COUNT(*) FROM notes"
        ).fetchone()[0]

        roots = conn.execute(
            """
            SELECT COUNT(*)
            FROM notes
            WHERE parent_id IS NULL
            """
        ).fetchone()[0]

        relations = conn.execute(
            "SELECT COUNT(*) FROM note_relations"
        ).fetchone()[0]

        links = conn.execute(
            "SELECT COUNT(*) FROM external_links"
        ).fetchone()[0]

        threads = conn.execute(
            "SELECT COUNT(*) FROM topics_threads"
        ).fetchone()[0]

        comments = conn.execute(
            "SELECT COUNT(*) FROM discussions"
        ).fetchone()[0]

        profiles = conn.execute(
            "SELECT COUNT(*) FROM agent_profiles"
        ).fetchone()[0]

        return {
            "database": str(db.path),
            "schema_version": SCHEMA_VERSION,
            "notes": notes,
            "root_notes": roots,
            "relations": relations,
            "external_links": links,
            "threads": threads,
            "discussion_comments": comments,
            "agent_profiles": profiles,
        }


def render_tree_impl(
    root_topic: Optional[str] = None,
    max_depth: int = 100,
) -> str:

    if max_depth < 0:
        raise ValidationError(
            "max_depth must be >= 0"
        )

    max_depth = min(max_depth, 1000)

    with db.connection() as conn:

        if root_topic:

            root_topic = validate_nonempty(
                root_topic,
                "root_topic",
                MAX_TOPIC_SIZE,
            )

            root = get_note_row(
                conn,
                root_topic,
            )

            rows = conn.execute(
                """
                WITH RECURSIVE tree AS (
                    SELECT
                        id,
                        topic,
                        parent_id,
                        category,
                        0 AS depth,
                        printf('%08d', id) AS path
                    FROM notes
                    WHERE id = ?

                    UNION ALL

                    SELECT
                        n.id,
                        n.topic,
                        n.parent_id,
                        n.category,
                        tree.depth + 1,
                        tree.path || '.' ||
                            printf('%08d', n.id)
                    FROM notes n
                    JOIN tree
                        ON n.parent_id = tree.id
                    WHERE tree.depth < ?
                )
                SELECT *
                FROM tree
                ORDER BY path
                """,
                (
                    root["id"],
                    max_depth,
                ),
            ).fetchall()

        else:

            rows = conn.execute(
                """
                WITH RECURSIVE tree AS (
                    SELECT
                        id,
                        topic,
                        parent_id,
                        category,
                        0 AS depth,
                        printf('%08d', id) AS path
                    FROM notes
                    WHERE parent_id IS NULL

                    UNION ALL

                    SELECT
                        n.id,
                        n.topic,
                        n.parent_id,
                        n.category,
                        tree.depth + 1,
                        tree.path || '.' ||
                            printf('%08d', n.id)
                    FROM notes n
                    JOIN tree
                        ON n.parent_id = tree.id
                    WHERE tree.depth < ?
                )
                SELECT *
                FROM tree
                ORDER BY path
                """,
                (max_depth,),
            ).fetchall()

        lines: list[str] = []

        for row in rows:

            depth = int(row["depth"])

            prefix = "    " * depth

            if depth == 0:
                marker = ""
            else:
                marker = "└── "

            lines.append(
                f"{prefix}{marker}"
                f"{row['topic']}"
                f" [{row['category']}]"
            )

        if not lines:
            return "(empty blackboard)"

        return "\n".join(lines)
