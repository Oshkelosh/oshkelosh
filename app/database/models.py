from .schema import schema
from .schema import db_path
from .migrations import get_columns

from flask_login import UserMixin, login_manager

from functools import lru_cache

import sqlite3, os, datetime, time
import json, string
import keyword
import importlib.util
from pathlib import Path

import bcrypt

from typing import Any, Dict, List, Optional, Tuple, Union


def safe_name(name):
    alphabet = string.ascii_lowercase
    stripped = "".join(letter if letter in alphabet else "_" for letter in name.lower())
    return stripped


def check_names(name):
    name = safe_name(name.lower())
    if name == "":
        raise ValueError("Name not accepted!")
    while name.startswith("_"):
        name = name[1:]
    while name.endswith("_"):
        name = name[:-1]
    while "__" in name:
        name = name.replace("__", "_")
    if name.lower() in [word.lower() for word in keyword.kwlist]:
        raise ValueError("Name not accepted!")
    return name


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


@lru_cache(maxsize=None)
def conn_db():
    db = sqlite3.connect(db_path, check_same_thread=False)
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("PRAGMA busy_timeout=5000;")
    db.execute("PRAGMA synchronous=NORMAL;")
    return db


def set_defaults(default_list):
    classes = {
        "USER": User,
        "PRODUCT": Product,
        "IMAGE": Image,
        "ORDER": Order,
        "CATEGORY": Category,
        "SUPPLIER": Supplier,
        "REVIEW": Review,
        "ADDON": Addon,
        "SETUP": Config,
    }
    try:
        for entry in default_list:
            print(f"Setting default {entry['type']} for {entry['object_name']}")
            if entry["type"] == "PLACEHOLDER":
                objects = classes[entry["object_name"]].get()
                difference = int(entry["amount"]) - len(objects)
                if difference == 0:
                    continue
                for i in range(difference):
                    classes[entry["object_name"]].new(**entry["data"])
                continue
            if entry["type"] in ["NOT NULL", "NOT_NULL"]:
                objects = classes[entry["object_name"]].get()
                exists = False
                if objects:
                    for set_object in objects:
                        if getattr(set_object, entry["key"], None) == entry["value"]:
                            exists = True

                if exists:
                    continue
                object_data = entry["data"].copy()
                object_data[entry["key"]] = entry["value"]
                classes[entry["object_name"]].new(**object_data)
    except Exception as e:
        print(f"Failed loading defaults, {e}")
        return False
    return True


class BaseClass:
    non_update: List[str] = []
    table_name: Optional[str] = None

    def __init__(self, **kwargs: Any) -> None:
        if self.table_name is None:
            raise ValueError("table_name must be set in subclass")
        for key in kwargs:
            if isinstance(kwargs[key], str) and kwargs[key].startswith(("{", "[")):
                try:
                    kwargs[key] = json.loads(kwargs[key])
                except json.JSONDecodeError:
                    pass
            setattr(self, key, kwargs[key])

    @classmethod
    def new(cls, **kwargs) -> 'BaseClass':
        if "id" in kwargs:
            raise KeyError("Invalid ID key found")
        if cls.table_name is None:
            raise ValueError("table_name must be set in subclass")
        table_columns = get_columns(cls.table_name, db_path)
        excess = [col for col in kwargs if col not in table_columns]
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for key in kwargs:
            if isinstance(kwargs[key], (dict, list)):
                try:
                    kwargs[key] = json.dumps(kwargs[key])
                except (TypeError, ValueError):
                    pass
        with conn_db() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO {cls.table_name} ({", ".join(kwargs.keys())})
                VALUES ({", ".join(["?" for _ in kwargs])})
            """,
                tuple(kwargs.values()),
            )
            conn.commit()
            last_id = cursor.lastrowid
            last_entry = cursor.execute(
                f"SELECT * FROM {cls.table_name} WHERE id = ?", (last_id,)
            ).fetchone()
            return cls(**last_entry)

    @classmethod
    def get(cls, **kwargs) -> List['BaseClass']:
        with conn_db() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()

            if not kwargs:
                cursor.execute(f"SELECT * FROM {cls.table_name}")
            else:
                where_clause = " AND ".join(f"{key} = ?" for key in kwargs)
                cursor.execute(
                    f"SELECT * FROM {cls.table_name} WHERE {where_clause}",
                    tuple(kwargs.values()),
                )
            data = cursor.fetchall()
            if not data:
                return []
            return [cls(**entry) for entry in data]

    def update(self, *keys) -> bool:
        update_data: Dict[str, Any] = {}
        if not keys:
            update_data = {
                k: v for k, v in vars(self).items() if k not in self.non_update
            }
        else:
            invalid = [k for k in keys if k in self.non_update or k not in vars(self)]
            if invalid:
                raise KeyError(f"Invalid keys for update: {', '.join(invalid)}")
            update_data = {k: getattr(self, k) for k in keys}
        if not update_data:
            print(f"Nothing updated to {self.table_name}")
            return True
        set_clause = ", ".join(f"{k} = ?" for k in update_data)
        params = tuple(update_data.values()) + (getattr(self, 'id'),)
        with conn_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?", params
            )
            conn.commit()
        return True


class User(UserMixin, BaseClass):
    table_name = "user_table"
    non_update = ["id", "created_at", "updated_at"]

    def check_password(self, input_password):
        return bcrypt.checkpw(input_password.encode(), self.password.encode())

    def update_password(self, old_password, new_password):
        if not bcrypt.checkpw(old_password.encode(), self.password.encode()):
            return False
        self.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self.update()
        return True



class Product(BaseClass):
    table_name = "product_table"
    non_update = [
        "id",
        "product_id",
        "supplier_id",
        "variant_of_id",
        "created_at",
        "updated_at",
    ]

    def add_category(self, **kwargs):
        pass

    def get_categories(self):
        pass

    def delete_category(self, **kwargs):
        pass

    def get_supplier(self):
        pass


class Image(BaseClass):
    table_name = "image_table"
    non_update = ["id", "product_id"]

    def delete(self):
        with conn_db() as connection:
            query = "DELETE FROM image_table WHERE id = ?"
            data = [getattr(self, 'id')]
            cursor = connection.cursor()
            cursor.execute(query, data)
            connection.commit()


class Order(BaseClass):
    table_name = "order_table"
    non_update = ["id", "user_id", "created_at", "updated_at"]

    def add_product(self, **kwargs):
        pass

    def get_products(self, **kwargs):
        pass

    def update_product(self, **kwargs):
        pass

    def add_payment(self, **kwargs):
        pass

    def get_payments(self, **kwargs):
        pass

    def update_payment_status(self, **kwargs):
        pass

    def add_shipping(self, **kwargs):
        pass

    def get_shipping(self, **kwargs):
        pass

    def update_shipping_status(self, **kwargs):
        pass


class Category(BaseClass):
    table_name = "category_table"
    non_update = ["id"]

    def delete(self):
        with conn_db() as connection:
            query = "DELETE FROM category_table WHERE id=?"
            data = [getattr(self, 'id')]
            cursor = connection.cursor()
            cursor.execute(query, data)
            connection.commit()


class Supplier(BaseClass):
    table_name = "supplier_table"
    non_update = ["id", "created_at", "updated_at"]

    def get_products(self):
        pass


class PaymentProcessor(BaseClass):
    table_name = "payment_processor_table"
    non_update = ["id", "created_at", "updated_at"]


class Review(BaseClass):
    table_name = "review_table"
    non_update = ["id", "product_id", "user_id", "created_at", "updated_at"]


class Addon(BaseClass):
    table_name = "addon_table"
    non_update = ["id", "name", "created_at", "updated_at"]

    @classmethod
    def new(cls, **kwargs):
        if "id" in kwargs:
            raise KeyError("Invalid ID key found")
        if cls.table_name is None:
            raise ValueError("table_name must be set in subclass")
        table_columns = get_columns(cls.table_name, db_path)
        excess = [col for col in kwargs if col not in table_columns]
        if excess:
            raise KeyError(
                f"Table Columns not registered for {cls.table_name}: {', '.join(excess)}"
            )
        for key in kwargs:
            if isinstance(kwargs[key], (dict, list)):
                try:
                    kwargs[key] = json.dumps(kwargs[key])
                except (TypeError, ValueError):
                    pass
        with conn_db() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO {cls.table_name} ({", ".join(kwargs.keys())})
                VALUES ({", ".join(["?" for _ in kwargs])})
            """,
                tuple(kwargs.values()),
            )
            conn.commit()
            last_id = cursor.lastrowid

            addon_path = (
                Path("app") / "addons" / kwargs["type"].lower() / kwargs["name"].lower()
            )
            module_name = f"{kwargs['type'].lower()}.{kwargs['name'].lower()}"
            spec = importlib.util.spec_from_file_location(
                module_name, addon_path / "__init__.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            default_list = module.default_list
            for i in range(len(default_list)):
                default_list[i]["data"]["addon_id"] = last_id

            print(f"Setting Addon {kwargs['name']} defaults")
            if not set_defaults(default_list):
                raise ValueError(f"Defaults for Addon: {kwargs['name']} failed to set")

            last_entry = cursor.execute(
                f"SELECT * FROM {cls.table_name} WHERE id = ?", (last_id,)
            ).fetchone()
            return cls(**last_entry)


class ConfigData:
    def __init__(self, **kwargs):
        self._parent = kwargs.pop("parent", None)
        self._attr_name = kwargs.pop("attr_name", None)
        self._value = kwargs.pop("value")
        for arg in kwargs.keys():
            if arg == "editable":
                setattr(self, arg, bool(kwargs[arg]))
                continue
            if arg == "addon_id":
                setattr(self, arg, int(kwargs[arg]) if kwargs[arg] is not None else None)
                continue
            setattr(self, arg, kwargs[arg])


    def __getattr__(self, name):
        return getattr(self._value, name)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __iter__(self):
        for key in vars(self):
            if key.startswith('_'):
                continue
            yield (key, getattr(self, key))
    def items(self):
        return self
    def keys(self):
        return (k for k, _ in self)
    def values(self):
        return (v for _, v in self)

    def delete(self):
        with conn_db() as connection:
            query = "DELETE FROM setup_table WHERE id=?"
            data = [self.id]
            cursor = connection.cursor()
            cursor.execute(query, data)
            connection.commit()
        if self._parent and self._attr_name:
            delattr(self._parent, self._attr_name)


class Config:
    table_name = "setup_table"
    non_update = ["id", "key", "addon_id", "created_at", "updated_at"]

    def __init__(self, **kwargs):
        self.type = "ADDON" if kwargs["addon_id"] is not None else "GLOBAL"
        if len(kwargs) > 1 and "key" in kwargs:
            key = kwargs.pop("key")
            self.set_config(key, **kwargs)

    @classmethod
    def new(cls, **kwargs):
        with conn_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"INSERT INTO setup_table ({', '.join(kwargs.keys())}) VALUES ({', '.join(['?' for _ in kwargs])})",
                tuple(kwargs.values()),
            )
            conn.commit()

    @classmethod
    def get(cls, **kwargs):
        """Returns specific Config setting data"""
        with conn_db() as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            clauses = [f"{key} = ?" for key in kwargs]
            params = tuple(kwargs.values())
            if "addon_id" not in kwargs:
                clauses.append("addon_id IS NULL")
            cursor.execute(
                f"SELECT * from {cls.table_name} WHERE {', '.join(clauses)}", params
            )
            data = cursor.fetchall()
            if not data:
                return []
            return [ConfigData(**entry) for entry in data]

    def set_config(self, key, **kwargs):
        setattr(self, key, ConfigData(parent=self, attr_name=key, **kwargs))

    def list_keys(self):
        return [key for key in vars(self).keys() if key != "type"]

    def data(self):
        """Returns only 'key':'value' from ConfigData, instead of all meta-data"""
        data = {}
        for key in self.list_keys():
            data[key] = str(getattr(self, key))
        return data

    def __getitem__(self, key):
        data = vars(self)[key]
        return data

    def update(self):
        success = True
        data = []
        for key, value in vars(self).items():
            key_data = {"key": key}
            for meta_key, meta_value in vars(value).items():
                key_data[meta_key] = meta_value
            data.append(key_data)
        try:
            with conn_db() as conn:
                cursor = conn.cursor()
                for entry in data:
                    set_clauses = []
                    params = []
                    for key, value in entry.items():
                        if key in self.non_update:  # Keys not no be updated
                            continue
                        set_clauses.append(f"{key} = ?")
                        params.append(value)
                    where_clause = "WHERE id = ?"
                    params.append(self.id)
                    query = f"UPDATE setup_table SET {set_clauses}, updated_at = CURRENT_TIMESTAMP {where_clause}"
                    cursor.execute(query, params)
                    if cursor.rowcount == 0:
                        success = False
                conn.commit()
        except sqlite3.Error as e:
            print(f"Config update error: {e}")
            success = False
        return success


def get_config(addon_name=None, addon_id=None):
    config = None

    with conn_db() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        if addon_name:
            data = cursor.execute(
                "SELECT * FROM addon_table WHERE name=?", (addon_name,)
            ).fetchone()
            if data:
                addon_id = data["id"]
            else:
                raise KeyError(f"Addon '{addon_name}' not installed")

        query = f"SELECT * FROM setup_table WHERE addon_id {'= ?' if addon_id else 'IS NULL'}"
        params = (addon_id,) if addon_id else ()
        data = cursor.execute(query, params).fetchall()
        if data:
            config = Config(addon_id=addon_id)
            for entry in data:
                config_key = entry.pop("key")
                config.set_config(config_key, **entry)
        else:
            raise ValueError("Setup Table not found! Please restart the Oshkelosh app.")
    return config


def set_configs():
    """Returns all config settings"""
    addon = []
    with conn_db() as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        data = cursor.execute("SELECT * FROM addon_table").fetchall()
        if data:
            for entry in data:
                addon.append(entry)
    configs = {}
    configs["site_config"] = get_config()
    for entry in addon:
        configs[f"{entry['name'].lower()}_{entry['type'].lower()}"] = get_config(
            addon_id=entry["id"]
        )
    return configs
