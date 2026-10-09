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
import bbmcps_cfg as cfg

class BlackboardDatabase:

    def __init__(self, path: Path):
        self.path = path

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:

        conn = sqlite3.connect(
            str(self.path),
            timeout=10.0,
        )

        conn.row_factory = sqlite3.Row

        try:
            conn.execute(
                "PRAGMA foreign_keys = ON"
            )

            conn.execute(
                "PRAGMA busy_timeout = 10000"
            )

            conn.execute(
                "PRAGMA journal_mode = WAL"
            )

            conn.execute(
                "PRAGMA synchronous = NORMAL"
            )

            yield conn

        finally:
            conn.close()

    def initialize(self) -> None:

        logging.info(
            "Initializing Blackboard database: %s",
            self.path,
        )

        with self.connection() as conn:
            version = conn.execute(
                "PRAGMA user_version"
            ).fetchone()[0]

            logging.info(
                "Current schema version: %s",
                version,
            )

            if version == 0:
                self._create_schema(conn)
                conn.execute(
                    f"PRAGMA user_version = {cfg.SCHEMA_VERSION}"
                )
                conn.commit()

            elif version < cfg.SCHEMA_VERSION:
                self._migrate(
                    conn,
                    version,
                    cfg.SCHEMA_VERSION,
                )
                conn.execute(
                    f"PRAGMA user_version = {cfg.SCHEMA_VERSION}"
                )
                conn.commit()

            elif version > cfg.SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {version} "
                    f"is newer than supported version "
                    f"{cfg.SCHEMA_VERSION}"
                )

            self._verify_schema(conn)

    def _create_schema(
        self,
        conn: sqlite3.Connection,
    ) -> None:

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL UNIQUE,

                system_prompt TEXT NOT NULL,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                topic TEXT NOT NULL UNIQUE,

                content TEXT NOT NULL,

                category TEXT NOT NULL
                    DEFAULT 'general',

                parent_id INTEGER,

                agent_profile_id INTEGER,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                FOREIGN KEY (parent_id)
                    REFERENCES notes(id)
                    ON DELETE SET NULL,

                FOREIGN KEY (agent_profile_id)
                    REFERENCES agent_profiles(id)
                    ON DELETE SET NULL
            );


            CREATE TABLE IF NOT EXISTS note_relations (
                source_id INTEGER NOT NULL,

                target_id INTEGER NOT NULL,

                created_at TEXT NOT NULL,

                PRIMARY KEY (
                    source_id,
                    target_id
                ),

                CHECK (
                    source_id <> target_id
                ),

                FOREIGN KEY (source_id)
                    REFERENCES notes(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (target_id)
                    REFERENCES notes(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS external_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                note_id INTEGER NOT NULL,

                url TEXT NOT NULL,

                description TEXT,

                created_at TEXT NOT NULL,

                FOREIGN KEY (note_id)
                    REFERENCES notes(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS topics_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                note_id INTEGER,

                title TEXT NOT NULL,

                status TEXT NOT NULL
                    DEFAULT 'open',

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                CHECK (
                    status IN (
                        'open',
                        'resolved',
                        'archived'
                    )
                ),

                FOREIGN KEY (note_id)
                    REFERENCES notes(id)
                    ON DELETE CASCADE
            );


            CREATE TABLE IF NOT EXISTS discussions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                thread_id INTEGER NOT NULL,

                author TEXT NOT NULL,

                comment TEXT NOT NULL,

                created_at TEXT NOT NULL,

                FOREIGN KEY (thread_id)
                    REFERENCES topics_threads(id)
                    ON DELETE CASCADE
            );


            CREATE INDEX IF NOT EXISTS idx_notes_parent
                ON notes(parent_id);

            CREATE INDEX IF NOT EXISTS idx_notes_category
                ON notes(category);

            CREATE INDEX IF NOT EXISTS idx_notes_agent_profile
                ON notes(agent_profile_id);

            CREATE INDEX IF NOT EXISTS idx_notes_updated
                ON notes(updated_at);

            CREATE INDEX IF NOT EXISTS idx_relations_source
                ON note_relations(source_id);

            CREATE INDEX IF NOT EXISTS idx_relations_target
                ON note_relations(target_id);

            CREATE INDEX IF NOT EXISTS idx_external_links_note
                ON external_links(note_id);

            CREATE INDEX IF NOT EXISTS idx_threads_note
                ON topics_threads(note_id);

            CREATE INDEX IF NOT EXISTS idx_threads_status
                ON topics_threads(status);

            CREATE INDEX IF NOT EXISTS idx_discussions_thread
                ON discussions(thread_id);
            """
        )

        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
                USING fts5(
                    topic,
                    content,
                    category,
                    content='notes',
                    content_rowid='id'
                )
                """
            )

            self._rebuild_fts(conn)

            logging.info(
                "SQLite FTS5 enabled"
            )

        except sqlite3.OperationalError as exc:
            logging.warning(
                "SQLite FTS5 unavailable: %s",
                exc,
            )

    def _migrate(
        self,
        conn: sqlite3.Connection,
        from_version: int,
        to_version: int,
    ) -> None:

        logging.info(
            "Migrating database %s -> %s",
            from_version,
            to_version,
        )

        if from_version < 2:
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(topics_threads)"
                ).fetchall()
            }

            if "note_id" not in columns:
                conn.execute(
                    """
                    ALTER TABLE topics_threads
                    ADD COLUMN note_id INTEGER
                    """
                )

        if from_version < 3:
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(notes)"
                ).fetchall()
            }

            if "created_at" not in columns:
                now = utc_now()

                conn.execute(
                    """
                    ALTER TABLE notes
                    ADD COLUMN created_at TEXT
                    """
                )

                conn.execute(
                    """
                    UPDATE notes
                    SET created_at = ?
                    WHERE created_at IS NULL
                    """,
                    (now,),
                )

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_notes_parent
                ON notes(parent_id);

            CREATE INDEX IF NOT EXISTS idx_notes_category
                ON notes(category);

            CREATE INDEX IF NOT EXISTS idx_notes_updated
                ON notes(updated_at);

            CREATE INDEX IF NOT EXISTS idx_relations_source
                ON note_relations(source_id);

            CREATE INDEX IF NOT EXISTS idx_relations_target
                ON note_relations(target_id);

            CREATE INDEX IF NOT EXISTS idx_external_links_note
                ON external_links(note_id);

            CREATE INDEX IF NOT EXISTS idx_threads_note
                ON topics_threads(note_id);

            CREATE INDEX IF NOT EXISTS idx_threads_status
                ON topics_threads(status);

            CREATE INDEX IF NOT EXISTS idx_discussions_thread
                ON discussions(thread_id);
            """
        )

    def _verify_schema(
        self,
        conn: sqlite3.Connection,
    ) -> None:

        result = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if result:
            raise RuntimeError(
                "SQLite foreign key integrity check failed"
            )

    def _rebuild_fts(
        self,
        conn: sqlite3.Connection,
    ) -> None:

        try:
            conn.execute(
                """
                INSERT INTO notes_fts(notes_fts)
                VALUES ('rebuild')
                """
            )
        except sqlite3.OperationalError:
            pass
