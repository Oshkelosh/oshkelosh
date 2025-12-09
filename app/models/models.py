from flask import current_app


from app import db

from flask_login import UserMixin, login_manager


import sqlite3, os, datetime, time
import json, string
import keyword
import importlib.util
from pathlib import Path

import bcrypt

from typing import Any, Dict, Iterator, KeysView, ValuesView, ItemsView, Optional, List

from app.utils.logging import get_logger
log = get_logger(__name__) 

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





def conn_db():
    return db.connection()


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
        "SETUP": ConfigData
    }
    try:
        for entry in default_list:
            log.info(f"Setting default {entry['type']} for {entry['object_name']}")
            if entry["type"] in ["NOT NULL", "NOT_NULL"]:
                cls_ = classes[entry["object_name"]]
                objects = (
                    cls_.get(addon_id=entry['data']['addon_id'])
                    if entry['data'].get('addon_id') is not None
                    else cls_.get()
                )
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
        log.error(f"Failed loading defaults, {e}")
        raise ValueError(f"Failed loading defaults, {e}") from e
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
        table_columns = db.get_columns(table_name=cls.table_name)
        excess = [col for col in kwargs if col not in table_columns]
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for key in kwargs:
            if isinstance(kwargs[key], (dict, list)):
                try:
                    kwargs[key] = json.dumps(kwargs[key])
                except (TypeError, ValueError):
                    pass
        with conn_db() as (conn, cursor):
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
        with conn_db() as (conn, cursor):

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
            log.info(f"Nothing updated to {self.table_name}")
            return True
        set_clause = ", ".join(f"{k} = ?" for k in update_data)
        params = tuple(update_data.values()) + (getattr(self, 'id'),)
        with conn_db() as (conn, cursor):
            cursor.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?", params
            )
            conn.commit()
        return True


class User(UserMixin, BaseClass):
    table_name = "user_table"
    non_update = ["id", "created_at", "updated_at"]

    def check_password(self, input_password):
        return bcrypt.checkpw(input_password.encode('utf-8'), self.password.encode('utf-8'))

    def update_password(self, old_password, new_password):
        if not bcrypt.checkpw(old_password.encode(), self.password.encode()):
            return False
        self.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self.update()
        return True


class Address(BaseClass):
    table_name = "address_table"
    non_update = ["id", "user_id", "type", "created_at", "updated_at"]


class Cart(BaseClass):
    table_name = "cart_table"
    non_update = ["id", "user_id", "product_id", "created_at", "updated_at"]

    def delete(self):
        with conn_db() as (connection, cursor):
            query = "DELETE FROM cart_table WHERE id = ?"
            data = [getattr(self, 'id')]
            cursor.execute(query, data)
            connection.commit()

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
        with conn_db() as (connection, cursor):
            query = "DELETE FROM image_table WHERE id = ?"
            data = [getattr(self, 'id')]
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
        with conn_db() as (connection, cursor):
            query = "DELETE FROM category_table WHERE id=?"
            data = [getattr(self, 'id')]
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
        table_columns = db.get_columns(table_name=cls.table_name)
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
        with conn_db() as (conn, cursor):
            cursor.execute(
                f"""
                INSERT INTO {cls.table_name} ({", ".join(kwargs.keys())})
                VALUES ({", ".join(["?" for _ in kwargs])})
            """,
                tuple(kwargs.values()),
            )
            conn.commit()
            last_id = cursor.lastrowid

            addon_path = None
            module_name = ""
            if kwargs['type'] == "STYLE":   #Add names for other addon types
                addon_path = (
                    Path('app') / 'styles' / kwargs['name'].lower()
                )
                module_name = f"app.styles.{kwargs['name'].lower()}"

            spec = importlib.util.spec_from_file_location(
                module_name, addon_path / "__init__.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            default_list = module.default_list
            for i in range(len(default_list)):
                default_list[i]["data"]["addon_id"] = last_id

            log.info(f"Setting Addon {kwargs['name']} defaults")
            if not set_defaults(default_list):
                raise ValueError(f"Defaults for Addon: {kwargs['name']} failed to set")
            else:
                log.info(f"Finished setting defaults for {kwargs['name']}")

            last_entry = cursor.execute(
                f"SELECT * FROM {cls.table_name} WHERE id = ?", (last_id,)
            ).fetchone()
            return cls(**last_entry)


class ConfigData(BaseClass):
    """Thin wrapper that holds the raw value + meta data, behaves like the value itself"""

    value: Any
    editable: bool = True
    description: Optional[str] = None
    addon_id: Optional[int] = None
    created_at: str
    updated_at: str
    id: int
    key: str
    type: str
    table_name = "setup_table"
    non_update = ["addon_id", "created_at", "updated_at", "id", "key", "type"]

    def __repr__(self) -> str:
        return f"<ConfigValue {self.key}={self.value}"
    def __str__(self) -> str:
        return str(self.value)
    def __eq__(self, other: Any) -> bool:
        return self.value == other
    def __hash__(self) -> int:
        return hash(self.value)
    def __int__(self):      return int(self.value)
    def __float__(self):    return float(self.value)
    def __bool__(self):     return bool(self.value)
    def __len__(self):      return len(self.value)
    def __getitem__(self, k): return self.value[k]
    def __contains__(self, item): return item in self.value
    def __iter__(self) -> Iterator:
        return iter(self.value)
    def meta(self) -> Dict[str, Any]:
        """Return all metadata (excluding the raw value)."""
        return {
            "editable": self.editable,
            "description": self.description,
            "addon_id": self.addon_id,
            "created_at":self.created_at,
            "updated_at":self.updated_at,
            "id": self.id,
            "key": self.key,
            "type": self.type
        }

    def delete(self):
        with conn_db() as (connection, cursor):
            query = "DELETE FROM setup_table WHERE id=?"
            data = [self.id]
            cursor.execute(query, data)
            connection.commit()
        if self._parent and self._attr_name:
            delattr(self._parent, self._attr_name)


class Config:
    def __init__(self, addon_id:Optional[int] = None):
        self._addon_id = addon_id
        self._cache: Dict[str, ConfigData] = {}
        self._load()

    def _load(self):
        with conn_db() as (conn, cur):
            if self._addon_id is None:
                cur.execute(f"SELECT * FROM setup_table WHERE addon_id IS NULL")
            else:
                cur.execute(f"SELECT * FROM setup_table WHERE addon_id = ?", (self._addon_id,))
            result = cur.fetchall()
            if not result:
                raise ValueError(f"Config data for {f"addon_id:{self.addon_id}" if self.addon_id else "site"} not found, check defaults.")
            for row in result:
                data = ConfigData(
                    value=row["value"],
                    editable=bool(row["editable"]),
                    description=row.get("description"),
                    addon_id=row["addon_id"],
                    created_at = row["created_at"],
                    updated_at = row["updated_at"],
                    id=row["id"],
                    key=row["key"],
                    type=row["type"]
                )
                self._cache[row["key"]] = data

    def __getitem__(self, key: str) -> Any:
        return self._cache[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set value and persist immediately (or queue – your call)."""
        if key not in self._cache:
            raise KeyError(f"Config key '{key}' does not exist")
        self._cache[key].value = value
        self._cache[key].update()   # atomic persistence

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def __iter__(self):
        return iter(self._cache)

    def keys(self) -> KeysView[str]:      return self._cache.keys()
    def values(self) -> ValuesView[Any]:  return (cv.value for cv in self._cache.values())
    def items(self) -> ItemsView[str, Any]: return ((k, cv.value) for k, cv in self._cache.items())

    def data(self) -> Dict[str, Any]:
        """Plain dict of key → raw value (exactly what you wanted)."""
        return {k: cv.value for k, cv in self._cache.items()}

    def meta(self) -> Dict[str, Dict[str, Any]]:
        """All metadata for frontend/UI use."""
        return {k: cv.meta() for k, cv in self._cache.items()}

    @classmethod
    def new(cls, key: str, value: Any, *, addon_id: Optional[int] = None, **meta) -> None:
        with conn_db() as (conn, cursor):
            columns = ["key", "value", "addon_id"] + list(meta.keys())
            placeholders = ["?"] * len(columns)
            values = [key, str(value), addon_id] + list(meta.values())
            cursor.execute(
                f"INSERT INTO {cls._table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                values,
            )


def get_config(addon_name=None, addon_id=None):
    if addon_name is None and addon_id is None:
        return Config()

    with conn_db() as (conn, cursor):
        if addon_name and addon_id is None:
            data = cursor.execute(
                "SELECT * FROM addon_table WHERE name=?", (addon_name,)
            ).fetchone()
            if data:
                addon_id = data["id"]
            else:
                raise KeyError(f"Addon '{addon_name}' not installed")

    return Config(addon_id=addon_id)


def set_configs():
    """Returns all front-end config settings"""
    configs = {}
    site_config = Config()
    style_id = None
    log.info(f"Fetching config data for style: {site_config['style']}")
    with conn_db() as (conn, cursor):
        cursor.execute(
            "SELECT * FROM addon_table WHERE name=? AND type=?", (str(site_config["style"]), "STYLE")
        )
        data = cursor.fetchone()
        if not data:
            raise KeyError("Style not installed")
        style_id = data["id"]
    style_config = Config(addon_id = style_id)

    return{
        "style_config" : style_config,
        "site_config" : site_config
    }
