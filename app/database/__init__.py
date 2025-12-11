from .migrations import setupDB
from .defaults import default_list

import os
from contextlib import contextmanager
from typing import Any, Tuple, Dict
from pathlib import Path
from urllib.parse import urlparse

from retry import retry

from enum import StrEnum, auto
import sqlite3, pymysql, psycopg2

from typing import Any, Dict, Generator, Tuple, Literal, ClassVar, Type

from app.utils.logging import get_logger

import json

logger = get_logger(__name__)

class Backend(StrEnum):
    SQLITE = auto()
    POSTGRESQL = auto()
    MYSQL = auto()

class DBClient:
    OperationalError: ClassVar[Tuple[Type[BaseException], ...]] = (
        sqlite3.OperationalError,
        psycopg2.OperationalError,
        pymysql.err.OperationalError
    )
    ProgrammingError: ClassVar[Tuple[Type[BaseException], ...]] = (
        sqlite3.ProgrammingError,
        psycopg2.ProgrammingError,
        pymysql.err.ProgrammingError
    )
    IntegrityError: ClassVar[Tuple[Type[BaseException], ...]] = (
        sqlite3.IntegrityError,
        psycopg2.IntegrityError,
        pymysql.err.IntegrityError
    )

    def __init__(self):
        self.uri = None
        self.backend = None
        self._row_factory = self._dict_factory

    def init_app(self, app):
        uri = (
            app.config.get("DATABASE_URI")
            or app.config.get("SQLALCHEMY_DATABASE_URI")
            or app.config.get("DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )
        if uri.startswith("sqlite:///"):
            self.backend = Backend.SQLITE
        elif uri.startswith(("postgresql://", "postgres://")):
            self.backend = Backend.POSTGRESQL
        elif uri.startswith(("mysql://", "mariadb://")):
            self.backend = Backend.MYSQL
        else:
            raise ValueError(f"Unsupported DATABASE_URI: {self.uri}")



        if not uri:
            raise RuntimeError("No Database config found")
        self.uri = uri


    def checkDB(self, schema):
        setupDB(schema, self)

    def _dict_factory(self, cursor, row):
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    @retry(tries=3,
           delay=1,
           backoff=2,
           exceptions=(OperationalError,),
           )
    def _connect(self) -> Tuple[Any, Any]:
        """Establish connection/ cursor with timeout/retry."""
        if not self.uri:
            raise RuntimeError("DBClient no initialized. Call init_app() first.")

        if self.backend == "sqlite":
            path = self.uri.split(":///", 1)[-1] or ":memory:"
            db_path = str(Path(path).expanduser().resolve()) if path != ":memory:" else ":memory:"
            if db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.row_factory = self._row_factory
            return conn, conn.cursor()
        
        if self.backend == "postgresql":
            conn = psycopg2.connect(self.uri, connect_timeout=10)
            conn.set_session(autocommit=False)
            cur = conn.cursor()
            cur.execute("SET client_min_messages TO WARNING;")
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            self.backend = Backend.POSTGRES
            return conn, conn.cursor()
        
        if self.backend == "mysql":
            parsed = urlparse(self.uri)
            conn = pymysql.connect(
                host=parsed.hostname or "localhost",
                port=parsed.port or 3306,
                user=parsed.username or "",
                password=parsed.password or "",
                database=parsed.path.lstrip("/") or None,
                charset="utf8mb4",
                autocommit=False,
                connect_timeout=10,
            )
            conn.cursorclass = pymysql.cursors.DictCursor
            self.backend = Backend.MYSQL
            return conn, conn.cursor()

        raise ValueError(f"Unsupported Database Backend: {self.backend}")

    @contextmanager
    def connection(self, autocommit: bool = True) -> Generator[Tuple[Any, Any], None, None]:
        """
        Context manager for conn/cursor.
        Usage:
        with db.connection() as (conn, cur):
            cur.execute("SELECT * FROM table", params)
            results = cur.fetchall()
        """
        conn, cur = self._connect()
        try:
            yield conn, cur
            if autocommit:
                conn.commit()
        except self.OperationalError as e:
            conn.rollback()
            logger.warning(f"Transient DB error (will retry on next call): {e}")
            raise
        except self.ProgrammingError as e:
            conn.rollback()
            logger.error(f"Database Programming error: {e}")
            raise
        except self.IntegrityError as e:
            logger.info(f"Integrity Error during DB operation: {e}")
            raise
        except Exception as e:
            conn.rollback()
            logger.exception(f"Unexpected DB error: {e}")
            raise
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def execute(
        self,
        query: str,
        params: tuple | dict | None = None,
        fetch: Literal["all", "one", "none"] = "all",
    ) -> Any:
        with self.connection() as (conn, cur):
            cur.execute(query, params or ())
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
            return None

    def get_columns(self, table_name: str) -> Dict[str, str]:
        if self.backend == "sqlite":
            res = self.execute(f"PRAGMA table_info({table_name})", fetch="all")
            return {row["name"].lower(): row["type"].lower() for row in res}
        elif self.backend == "postgresql":
            sql = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                  AND table_schema = current_schema()
                ORDER BY ordinal_position
            """
            res = self.execute(sql, (table_name,), fetch="all")
            return {row["column_name"].lower(): row["data_type"].lower() for row in res}
        elif self.backend == "mysql":
            sql = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s
                  AND table_schema = DATABASE()
                ORDER BY ordinal_position
            """
            res = self.execute(sql, (table_name,), fetch="all")
            return {row["column_name"].lower(): row["data_type"].lower() for row in res}
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")

    @staticmethod
    def is_duplicate(exc: Exception, column: str | None = None) -> bool:
        """
        Checks if Exception is for duplicate entry error
        """
        msg = str(exc).lower()
        checks = ["unique", "duplicate", "uniq_", "key"]
        if not any(c in msg for c in checks):
            return False
        if column:
            return column.lower() in msg
        return True
