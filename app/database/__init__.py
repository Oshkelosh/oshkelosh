from .migrations import setupDB
from .defaults import default_list

import os
from contextlib import contextmanager
from typing import Any, Tuple, Dict
from pathlib import Path
from urllib.parse import urlparse

from retry import retry

import sqlite3, pymysql, psycopg2 

from app.utils.logging import get_logger

import json

logger = get_logger(__name__)


class DBClient:
    def __init__(self):
        self.uri = None
        self.backend = None
    def init_app(self, app, schema):
        uri = (
            app.config.get("DATABASE_URI")
            or app.config.get("SQLALCHEMY_DATABASE_URI")
            or app.config.get("DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )

        if not uri:
            raise RuntimeError("No Database config found")
        self.uri = uri
        setupDB(schema = schema, uri=uri)

    def _dict_factory(self, cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    @retry(tries=3, delay=1, backoff=2, exceptions=(sqlite3.OperationalError, psycopg2.OperationalError, pymysql.OperationalError))
    def _connect(self) -> Tuple[Any, Any, str]:
        """Establish connection/ cursor with timeout/retry."""
        if self.uri.startswith("sqlite:///"):
            path = self.uri.split(":///", 1)[-1] or ":memory:"
            db_path = str(Path(path).expanduser().resolve()) if path != ":memory:" else ":memory:"
            if db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.row_factory = self._dict_factory
            return conn, conn.cursor(), "sqlite"
        
        if self.uri.startswith(("postgresql://", "postgres://")):
            conn = psycopg2.connect(self.uri, connect_timeout=10)
            cur = conn.cursor()
            cur.row_factory = self._dict_factory
            cur.execute("SET client_min_messages TO WARNING;")
            return conn, cur, "postgres"
        
        if self.uri.startswith(("mysql://", "mariadb://")):
            parsed = urlparse(self.uri)
            conn = pymysql.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 3306,
                user=parsed.username or "",
                password=parsed.password or "",
                database=parsed.path.lstrip("/") or None,
                charset="utf8mb4",
                connect_timeout=10,
            )
            cur = conn.cursor
            cur.row_factory = self._dict_factory
            return conn, conn.cursor(), "mysql"
        raise ValueError(f"Unsupported DATABASE_URI: {self.uri}")

    @contextmanager
    def connection(self, autocommit: bool = True):
        """
        Context manager for conn/cursor.
        Usage:
        with db.connection() as (conn, cur):
            cur.execute("SELECT * FROM table", params)
            results = cur.fetchall()
        """
        conn, cur, backend = self._connect()
        self.backend = backend  # Cache for type-specific logic if needed
        try:
            yield conn, cur
            if autocommit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if backend == "sqlite":
                conn.execute("PRAGMA foreign_keys = ON")
            cur.close()
            conn.close()

    def execute(self, query: str, params: Tuple = (), fetch: str = "all") -> Any:
        """Execute query with params; fetch='all', 'one', 'none'."""
        with self.connection(autocommit=True) as (conn, cursor):
            cursor.execute(query, params)
            if fetch == "all":
                return cursor.fetchall()
            elif fetch == "one":
                return cursor.fetchone()
            return None

    def get_columns(self, table_name: str) -> Dict[str,str]:
        """
        Return a dict of {column_name: data_type} for the given table.
        Works with SQLite, PostgreSQL, and MySQL.
        Column names are normalized to lowercase.
        """
        with self.connection(autocommit=False) as (conn, cursor):
            if self.backend == "sqlite":
                cursor.execute(f"PRAGMA table_info({table_name})")
                data = cursor.fetchall()
                return {entry['name'].lower(): entry['type'].lower() for entry in data}

            else:  # PostgreSQL + MySQL
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                      AND table_schema = CURRENT_SCHEMA()
                    ORDER BY ordinal_position
                """, (table_name,))
                data = cursor.fetchall()
                return {entry['column_name'].lower(): entry['data_type'].lower() for entry in data}
