from app.utils.logging import get_logger
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Tuple, Dict, List, Any

import sqlite3
import psycopg2
import pymysql

log = get_logger(__name__)

DB_OPERATIONAL_ERRORS = (
    sqlite3.Error,
    psycopg2.Error,
    pymysql.MySQLError,
)


def _map_type(col_type: str, backend: str) -> str:
    """Map schema type strings to DB-specific equivalents."""
    base_type = col_type.upper().split()[0]
    constraints = ' '.join(col_type.upper().split()[1:]) if len(col_type.split()) > 1 else ''
    
    type_map = {
        "INTEGER": {
            "sqlite": "INTEGER",
            "postgres": "INTEGER",
            "mysql": "INT",
        },
        "TEXT": {"sqlite": "TEXT", "postgres": "TEXT", "mysql": "TEXT"},
        "FLOAT": {"sqlite": "REAL", "postgres": "DOUBLE PRECISION", "mysql": "DOUBLE"},
        "TIMESTAMP": {"sqlite": "TEXT", "postgres": "TIMESTAMP", "mysql": "TIMESTAMP"},
        "BOOL": {"sqlite": "INTEGER", "postgres": "BOOLEAN", "mysql": "TINYINT(1)"},
    }
    mapped_base = type_map.get(base_type, {"sqlite": base_type, "postgres": base_type, "mysql": base_type})[backend]

    if "PRIMARY KEY" in constraints:
        if "AUTOINCREMENT" in constraints or "AUTO_INCREMENT" in constraints:
            if backend == "sqlite":
                return f"{mapped_base} PRIMARY KEY AUTOINCREMENT"
            elif backend == "postgres":
                return "SERIAL PRIMARY KEY"
            elif backend == "mysql":
                return f"{mapped_base} AUTO_INCREMENT PRIMARY KEY"
        else:
            return f"{mapped_base} PRIMARY KEY"
    return f"{mapped_base} {constraints}".strip()


def _table_exists(db: Any, table_name: str) -> bool:
    backend = db.backend
    if backend == "sqlite":
        query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
        params = (table_name,)
    elif backend == "postgresql":
        query = "SELECT 1 FROM information_schema.tables WHERE table_name = %s AND table_schema = current_schema()"
        params = (table_name,)
    elif backend == "mysql":
        query = "SELECT 1 FROM information_schema.tables WHERE table_name = %s AND table_schema = DATABASE()"
        params = (table_name,)
    else:
        raise ValueError(f"Unsupported backend: {backend}")
    res = db.execute(query, params, fetch="one")
    return res is not None


def _constraint_exists(cur: Any, table_name: str, constraint_name: str, backend: str) -> bool:
    if backend == "sqlite":
        return False
    elif backend == "postgresql":
        query = """
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = %s AND constraint_name = %s
              AND table_schema = current_schema()
        """
    elif backend == "mysql":
        query = """
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = %s AND constraint_name = %s
              AND table_schema = DATABASE()
        """
    else:
        raise ValueError(f"Unsupported backend: {backend}")
    cur.execute(query, (table_name, constraint_name))
    return cur.fetchone() is not None

def _get_row_count(cur: Any, table_name: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    row = cur.fetchone()
    return list(row.values())[0]

def _recreate_table_for_sqlite(conn: Any, cur: Any, table_name: str, cols_def: Dict[str, Any], backend: str) -> None:
    """Safely recreate SQLite table with data copy if changes needed."""
    cur.execute(f"SELECT * FROM {table_name}")
    data = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    
    temp_name = f"{table_name}_temp"
    _create_table(cur, temp_name, cols_def, backend)
    
    new_cols = [n for n in cols_def if n.upper() not in ("FOREIGN KEY", "UNIQUE")]
    insert_cols = ', '.join(new_cols)
    values = ', '.join(['?' for _ in new_cols])
    for row in data:
        new_row = [row.get(col, None) for col in new_cols]
        cur.execute(f"INSERT INTO {temp_name} ({insert_cols}) VALUES ({values})", new_row)
    
    cur.execute(f"DROP TABLE {table_name}")
    cur.execute(f"ALTER TABLE {temp_name} RENAME TO {table_name}")
    log.info(f"Recreated {table_name} with changes")

def _create_table(cur: Any, table_name: str, cols_def: Dict[str, Any], backend: str) -> None:
    parts = []
    for col_name, col_type in cols_def.items():
        if col_name.upper() in ("FOREIGN KEY", "UNIQUE"):
            continue
        mapped_type = _map_type(col_type, backend)
        if "NOT NULL" in mapped_type.upper() and "DEFAULT" not in mapped_type.upper():
            default_val = "''" if "TEXT" in mapped_type.upper() else "0"
            mapped_type += f" DEFAULT {default_val}"
        parts.append(f"{col_name} {mapped_type}")
    
    if "UNIQUE" in cols_def:
        u = cols_def["UNIQUE"]
        if isinstance(u, list) and u:
            parts.append(f"UNIQUE ({', '.join(u)})")
    
    if "FOREIGN KEY" in cols_def:
        fks = cols_def["FOREIGN KEY"] if isinstance(cols_def["FOREIGN KEY"], list) else [cols_def["FOREIGN KEY"]]
        for fk in fks:
            instr = fk.get("instruction", "").strip()
            parts.append(f"FOREIGN KEY ({fk['key']}) REFERENCES {fk['parent_table']}({fk['parent_key']}) {instr}")
    cur.execute(f"CREATE TABLE {table_name} ({', '.join(parts)})")

def setupDB(schema: List[Dict[str, Any]], db: Any) -> None:
    """
    Synchronize DB schema safely:
    - Create missing tables with all columns/constraints.
    - Add missing columns/constraints to existing tables (recreate for SQLite if needed).
    - Add missing UNIQUE/FK constraints (skips if exist).
    - No data loss; production-safe, but use Alembic for complex prod migrations.
    - Call anytime for addon schema extensions.
    """
    if not schema:
        log.error("No schema provided")
        return
    backend_str = db.backend
    if backend_str == "postgresql":
        backend_str = "postgres"

    with db.connection(autocommit=False) as (conn, cur):
        try:
            for table_def in schema:
                table_name = table_def["table_name"]
                cols_def = table_def["table_columns"]
                log.info(f"Syncing {table_name}")
                
                if not _table_exists(db, table_name):
                    _create_table(cur, table_name, cols_def, backend_str)
                    log.info(f"Created table")
                    continue
                
                needs_recreate = False
                if backend_str == "sqlite":
                    existing_cols = db.get_columns(table_name)
                    for col_name in cols_def:
                        if col_name.upper() in ("FOREIGN KEY", "UNIQUE"):
                            needs_recreate = True
                        elif col_name.lower() not in existing_cols:
                            needs_recreate = True
                    if needs_recreate:
                        _recreate_table_for_sqlite(conn, cur, table_name, cols_def, backend_str)
                        continue
                
                existing_cols = db.get_columns(table_name)
                for col_name, col_type in cols_def.items():
                    if col_name.upper() in ("FOREIGN KEY", "UNIQUE"):
                        continue
                    if col_name.lower() not in existing_cols:
                        row_count = _get_row_count(cur, table_name)
                        mapped_type = _map_type(col_type, backend_str)
                        if "NOT NULL" in mapped_type.upper() and row_count > 0 and "DEFAULT" not in mapped_type.upper():
                            temp_type = mapped_type.replace("NOT NULL", "")
                            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {temp_type}")
                            default_val = "''" if "TEXT" in mapped_type.upper() else "0"
                            cur.execute(f"UPDATE {table_name} SET {col_name} = {default_val}")
                            if backend_str == "mysql":
                                cur.execute(f"ALTER TABLE {table_name} MODIFY {col_name} {mapped_type}")
                            else:
                                cur.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET {mapped_type.split(' ', 1)[1]}")
                        else:
                            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {mapped_type}")
                        log.info(f"Added column {col_name}")
                
                if "UNIQUE" in cols_def:
                    u = cols_def["UNIQUE"]
                    if isinstance(u, list) and u:
                        uniq_name = f"uniq_{table_name}_{'_'.join(u)}"
                        if not _constraint_exists(cur, table_name, uniq_name, backend_str):
                            try:
                                cur.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT {uniq_name} UNIQUE ({', '.join(u)})")
                                log.info(f"Added UNIQUE on {u}")
                            except Exception:
                                log.debug(f"UNIQUE constraint {uniq_name} already exists or conflict")
                
                if "FOREIGN KEY" in cols_def:
                    fks = cols_def["FOREIGN KEY"] if isinstance(cols_def["FOREIGN KEY"], list) else [cols_def["FOREIGN KEY"]]
                    for fk in fks:
                        fk_name = f"fk_{table_name}_{fk['key']}"
                        if not _constraint_exists(cur, table_name, fk_name, backend_str):
                            try:
                                instr = fk.get("instruction", "").strip()
                                cur.execute(
                                    f"ALTER TABLE {table_name} ADD CONSTRAINT {fk_name} "
                                    f"FOREIGN KEY ({fk['key']}) REFERENCES {fk['parent_table']}({fk['parent_key']}) {instr}"
                                )
                                log.info(f"Added FK {fk['key']} -> {fk['parent_table']}")
                            except Exception:
                                log.debug(f"FK constraint {fk_name} already exists or conflict")
            
            conn.commit()
            log.info("Schema sync complete")
        except Exception as e:
            conn.rollback()
            log.exception(f"Sync failed: {e}")
            raise
        finally:
            if backend_str == "sqlite":
                conn.execute("PRAGMA foreign_keys = ON")
