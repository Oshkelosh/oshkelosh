from app.utils.logging import get_logger
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Tuple, Dict, List

import sqlite3
import psycopg2
import pymysql

log = get_logger(__name__)

DB_OPERATIONAL_ERRORS = (
    sqlite3.Error,
    psycopg2.Error,
    pymysql.MySQLError,
)

def _connect(uri: str) -> Tuple[object, object, str]:
    """Establish connection and cursor; return (conn, cursor, backend_type)."""
    if uri.startswith("sqlite:///"):
        path = uri.split(":///", 1)[-1] or ":memory:"
        db_path = str(Path(path).expanduser().resolve()) if path != ":memory:" else ":memory:"
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=10)  # Add timeout
        conn.execute("PRAGMA foreign_keys = OFF")
        return conn, conn.cursor(), "sqlite"
    if uri.startswith(("postgresql://", "postgres://")):
        conn = psycopg2.connect(uri)
        cur = conn.cursor()
        cur.execute("SET client_min_messages TO WARNING;")
        return conn, cur, "postgres"
    if uri.startswith(("mysql://", "mariadb://")):
        parsed = urlparse(uri)
        conn = pymysql.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or None,
            charset="utf8mb4",
            connect_timeout=10,
        )
        return conn, conn.cursor(), "mysql"
    raise ValueError(f"Unsupported DATABASE_URI: {uri}")


def _map_type(col_type: str, backend: str) -> str:
    """Map schema type strings to DB-specific equivalents."""
    base_type = col_type.upper().split()[0]  # E.g., 'INTEGER' from 'INTEGER PRIMARY KEY AUTOINCREMENT'
    constraints = ' '.join(col_type.upper().split()[1:]) if len(col_type.split()) > 1 else ''
    
    type_map = {
        "INTEGER": {
            "sqlite": "INTEGER",
            "postgres": "INTEGER",
            "mysql": "INT",
        },
        "TEXT": {"sqlite": "TEXT", "postgres": "TEXT", "mysql": "TEXT"},
        "FLOAT": {"sqlite": "REAL", "postgres": "DOUBLE PRECISION", "mysql": "DOUBLE"},
        "TIMESTAMP": {"sqlite": "TEXT", "postgres": "TIMESTAMP", "mysql": "TIMESTAMP"},  # SQLite: store ISO or epoch
        "BOOL": {"sqlite": "INTEGER", "postgres": "BOOLEAN", "mysql": "TINYINT(1)"},  # Use 0/1
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

def _table_exists(cursor, table_name: str, backend: str) -> bool:
    if backend == "sqlite":
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    else:
        cursor.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s AND table_schema = DATABASE()",
            (table_name,),
        )
    return cursor.fetchone() is not None

def _get_existing_columns(cursor, table_name: str, backend: str) -> Dict[str, str]:
    if backend == "sqlite":
        cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1].lower(): row[2].lower() for row in cursor.fetchall()}
    else:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s AND table_schema = DATABASE()",
            (table_name,),
        )
        return {row[0].lower(): row[1].lower() for row in cursor.fetchall()}

def _constraint_exists(cursor, table_name: str, constraint_name: str, backend: str) -> bool:
    if backend == "sqlite":
        # SQLite doesn't easily query constraints; assume try-except handles
        return False
    else:
        cursor.execute(
            "SELECT 1 FROM information_schema.table_constraints WHERE table_name = %s AND constraint_name = %s",
            (table_name, constraint_name),
        )
        return cursor.fetchone() is not None

def _get_row_count(cursor, table_name: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]

def _recreate_table_for_sqlite(conn, cursor, table_name: str, cols_def: Dict, backend: str):
    """Safely recreate SQLite table with data copy if changes needed."""
    # Get existing data
    cursor.execute(f"SELECT * FROM {table_name}")
    data = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    # Create temp table with new schema
    temp_name = f"{table_name}_temp"
    _create_table(cursor, temp_name, cols_def, backend)  # Use helper to build CREATE
    
    # Insert data (map to new columns, use defaults for added)
    new_cols = [n for n in cols_def if n.upper() not in ("FOREIGN KEY", "UNIQUE")]
    insert_cols = ', '.join(new_cols)
    values = ', '.join(['?' for _ in new_cols])
    for row in data:
        row_dict = dict(zip(columns, row))
        new_row = [row_dict.get(col, None) for col in new_cols]  # None for new cols
        cursor.execute(f"INSERT INTO {temp_name} ({insert_cols}) VALUES ({values})", new_row)
    
    # Drop old, rename new
    cursor.execute(f"DROP TABLE {table_name}")
    cursor.execute(f"ALTER TABLE {temp_name} RENAME TO {table_name}")
    conn.commit()
    log.info(f"Recreated {table_name} with changes")

def _create_table(cursor, table_name: str, cols_def: Dict, backend: str):
    parts = []
    for col_name, col_type in cols_def.items():
        if col_name.upper() in ("FOREIGN KEY", "UNIQUE"):
            continue
        mapped_type = _map_type(col_type, backend)
        # Ensure DEFAULT for NOT NULL if missing
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
    cursor.execute(f"CREATE TABLE {table_name} ({', '.join(parts)})")

def setupDB(schema: List[Dict], uri: str):
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
    conn, cursor, backend = _connect(uri)
    
    try:
        for table_def in schema:
            table_name = table_def["table_name"]
            cols_def = table_def["table_columns"]
            log.info(f"Syncing {table_name}")
            
            if not _table_exists(cursor, table_name, backend):
                _create_table(cursor, table_name, cols_def, backend)
                log.info(f"Created table")
                continue
            
            # Check for changes needing recreate (SQLite only)
            needs_recreate = False
            if backend == "sqlite":
                # If adding columns with constraints or new FK/UNIQUE, flag
                existing_cols = _get_existing_columns(cursor, table_name, backend)
                for col_name, _ in cols_def.items():
                    if col_name.upper() in ("FOREIGN KEY", "UNIQUE"):
                        needs_recreate = True  # Can't add constraints
                    elif col_name.lower() not in existing_cols:
                        needs_recreate = True  # For safety, recreate
                if needs_recreate:
                    _recreate_table_for_sqlite(conn, cursor, table_name, cols_def, backend)
                    continue
            
            # Add missing columns (non-SQLite or simple adds)
            existing_cols = _get_existing_columns(cursor, table_name, backend)
            for col_name, col_type in cols_def.items():
                if col_name.upper() in ("FOREIGN KEY", "UNIQUE"):
                    continue
                if col_name.lower() not in existing_cols:
                    row_count = _get_row_count(cursor, table_name)
                    mapped_type = _map_type(col_type, backend)
                    if "NOT NULL" in mapped_type.upper() and row_count > 0 and "DEFAULT" not in mapped_type.upper():
                        # Add as NULL, update, then NOT NULL
                        temp_type = mapped_type.replace("NOT NULL", "")
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {temp_type}")
                        default_val = "''" if "TEXT" in mapped_type.upper() else "0"
                        cursor.execute(f"UPDATE {table_name} SET {col_name} = {default_val}")
                        cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} {mapped_type}")
                    else:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {mapped_type}")
                    log.info(f"Added column {col_name}")
            
            # Add UNIQUE if missing
            if "UNIQUE" in cols_def:
                u = cols_def["UNIQUE"]
                if isinstance(u, list) and u:
                    uniq_name = f"uniq_{table_name}_{'_'.join(u)}"
                    if not _constraint_exists(cursor, table_name, uniq_name, backend):
                        try:
                            cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT {uniq_name} UNIQUE ({', '.join(u)})")
                            log.info(f"Added UNIQUE on {u}")
                        except DB_OPERATIONAL_ERRORS:
                            log.debug(f"UNIQUE constraint {uniq_name} already exists or conflict")
            
            # Add FKs if missing
            if "FOREIGN KEY" in cols_def:
                fks = cols_def["FOREIGN KEY"] if isinstance(cols_def["FOREIGN KEY"], list) else [cols_def["FOREIGN KEY"]]
                for fk in fks:
                    fk_name = f"fk_{table_name}_{fk['key']}"
                    if not _constraint_exists(cursor, table_name, fk_name, backend):
                        try:
                            instr = fk.get("instruction", "").strip()
                            cursor.execute(
                                f"ALTER TABLE {table_name} ADD CONSTRAINT {fk_name} "
                                f"FOREIGN KEY ({fk['key']}) REFERENCES {fk['parent_table']}({fk['parent_key']}) {instr}"
                            )
                            log.info(f"Added FK {fk['key']} -> {fk['parent_table']}")
                        except DB_OPERATIONAL_ERRORS:
                            log.debug(f"FK constraint {fk_name} already exists or conflict")
        
        conn.commit()
        log.info("Schema sync complete")
    except DB_OPERATIONAL_ERRORS as e:
        conn.rollback()
        log.exception(f"Sync failed: {e}")
        raise
    finally:
        if backend == "sqlite":
            conn.execute("PRAGMA foreign_keys = ON")
        cursor.close()
        conn.close()
