import sqlite3, os, datetime, time
import json


def setupDB(schema: list, db_path: str = "./instance/database.db"):
    if not schema:
        currentTS = int(time.time())
        date = datetime.datetime.fromtimestamp(currentTS)
        dateFormat = "%d%b %Y %H:%M:%S"
        printDate = date.strftime(dateFormat)
        print(f"{printDate}: Error ~ No schema supplied!")
        return None

    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        currentTS = int(time.time())
        date = datetime.datetime.fromtimestamp(currentTS)
        dateFormat = "%d%b %Y %H:%M:%S"
        printDate = date.strftime(dateFormat)
        print(f"{printDate}: Creating {db_path}")
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    for table in schema:
        table_name = table["table_name"]

        currentTS = int(time.time())
        date = datetime.datetime.fromtimestamp(currentTS)
        dateFormat = "%d%b %Y %H:%M:%S"
        printDate = date.strftime(dateFormat)

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        exists = cursor.fetchone() is not None

        schema_col_names = {
            k
            for k, v in table["table_columns"].items()
            if k.upper() not in ["FOREIGN KEY", "UNIQUE"]
        }

        if not exists:
            print(f"{printDate}: Creating new table {table_name}")
            # Build and execute CREATE TABLE
            query_content = []
            for key, value in table["table_columns"].items():
                if key.upper() in ["FOREIGN KEY", "UNIQUE"]:
                    continue
                query_content.append(f"{key} {value}")
            if "UNIQUE" in table["table_columns"]:
                uniques = table["table_columns"]["UNIQUE"]
                if isinstance(uniques, list):
                    query_entry = f"UNIQUE ({', '.join(uniques)})"
                    query_content.append(query_entry)
            fk_key = "FOREIGN KEY"
            if fk_key in table["table_columns"]:
                fks = table["table_columns"][fk_key]
                if not isinstance(fks, list):
                    fks = [fks]
                for fk in fks:
                    instruction = fk.get("instruction", "")
                    query_entry = f"FOREIGN KEY ({fk['key']}) REFERENCES {fk['parent_table']}({fk['parent_key']}) {instruction}"
                    query_content.append(query_entry)
            columns_content = ", ".join(query_content)
            sql_string = f"CREATE TABLE {table_name} ({columns_content})"
            cursor.execute(sql_string)
            continue

        # Table exists, fetch info
        cursor.execute(f"PRAGMA table_info({table_name})")
        table_columns_info = cursor.fetchall()
        existing_columns = {row[1]: row for row in table_columns_info}
        existing_col_names = set(existing_columns.keys())

        # Existing FKs
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        existing_fks_raw = cursor.fetchall()
        existing_fks = {}
        for row in existing_fks_raw:
            child_col = row[3]
            on_delete = row[6]
            instruction = (
                f"ON DELETE {on_delete}"
                if on_delete and on_delete != "NO ACTION"
                else ""
            )
            existing_fks[child_col] = {
                "parent_table": row[2],
                "parent_key": row[4],
                "instruction": instruction,
            }

        # Existing UNIQUE
        cursor.execute(f"PRAGMA index_list({table_name})")
        existing_uniques = {}
        for idx_row in cursor.fetchall():
            if idx_row[2] == 1:  # unique
                cursor.execute(f"PRAGMA index_info({idx_row[1]})")
                cols = sorted([row[2] for row in cursor.fetchall()])
                existing_uniques[tuple(cols)] = True

        # Schema FKs
        schema_fks_raw = table["table_columns"].get("FOREIGN KEY", [])
        if not isinstance(schema_fks_raw, list):
            schema_fks_raw = [schema_fks_raw] if schema_fks_raw else []
        schema_fks = schema_fks_raw
        schema_fks_set = frozenset(
            (fk["key"], fk["parent_table"], fk["parent_key"], fk.get("instruction", ""))
            for fk in schema_fks
        )
        existing_fks_set = frozenset(
            (k, v["parent_table"], v["parent_key"], v["instruction"])
            for k, v in existing_fks.items()
        )

        # Schema UNIQUE
        schema_uniques_raw = table["table_columns"].get("UNIQUE", [])
        if not isinstance(schema_uniques_raw, list):
            schema_uniques_raw = []
        schema_uniques = schema_uniques_raw
        schema_unique_tuple = tuple(sorted(schema_uniques)) if schema_uniques else None

        # Determine if needs recreate
        needs_recreate = False
        if schema_col_names != existing_col_names:
            needs_recreate = True
        if schema_fks_set != existing_fks_set:
            needs_recreate = True
        unique_match = (schema_unique_tuple is None and not existing_uniques) or (
            schema_unique_tuple is not None and schema_unique_tuple in existing_uniques
        )
        if not unique_match:
            needs_recreate = True

        if not needs_recreate:
            print(f"{printDate}: {table_name} is up to date.")
            continue

        # Recreate
        print(f"{printDate}: Recreating {table_name} with data migration.")
        cursor.execute(
            f"CREATE TABLE {table_name}_backup AS SELECT * FROM {table_name}"
        )
        cursor.execute(f"DROP TABLE {table_name}")

        # Build and create new
        query_content = []
        for key, value in table["table_columns"].items():
            if key.upper() in ["FOREIGN KEY", "UNIQUE"]:
                continue
            query_content.append(f"{key} {value}")
        if "UNIQUE" in table["table_columns"]:
            uniques = table["table_columns"]["UNIQUE"]
            if isinstance(uniques, list):
                query_entry = f"UNIQUE ({', '.join(uniques)})"
                query_content.append(query_entry)
        fk_key = "FOREIGN KEY"
        if fk_key in table["table_columns"]:
            fks = table["table_columns"][fk_key]
            if not isinstance(fks, list):
                fks = [fks]
            for fk in fks:
                instruction = fk.get("instruction", "")
                query_entry = f"FOREIGN KEY ({fk['key']}) REFERENCES {fk['parent_table']}({fk['parent_key']}) {instruction}"
                query_content.append(query_entry)
        columns_content = ", ".join(query_content)
        sql_string = f"CREATE TABLE {table_name} ({columns_content})"
        cursor.execute(sql_string)

        # Migrate data
        common_cols = list(schema_col_names & existing_col_names)
        if common_cols:
            cols_str = ", ".join(f'"{col}"' for col in common_cols)
            cursor.execute(
                f"INSERT INTO {table_name} ({cols_str}) SELECT {cols_str} FROM {table_name}_backup"
            )

        cursor.execute(f"DROP TABLE {table_name}_backup")

    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def get_columns(table_name, db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
