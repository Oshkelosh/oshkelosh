from flask import current_app
from flask_login import UserMixin
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Iterator, KeysView, ValuesView, ItemsView, Optional, List
import json
import string
import keyword
import importlib.util

import bcrypt
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, func, event
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declared_attr

from app.database import db
from app.utils.logging import get_logger
from app.utils import encryption

log = get_logger(__name__)


def safe_name(name: str) -> str:
    alphabet = string.ascii_lowercase
    stripped = "".join(letter if letter in alphabet else "_" for letter in name.lower())
    return stripped


def check_names(name: str) -> str:
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


# Association table for Product-Category many-to-many relationship
product_category = db.Table(
    'product_category',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product_table.id'), nullable=False),
    db.Column('category_id', db.Integer, db.ForeignKey('category_table.id', ondelete='CASCADE'), nullable=False),
)


class User(UserMixin, db.Model):
    __tablename__ = 'user_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=True)
    password = Column(String, nullable=False)
    role = Column(String, default='CLIENT', server_default='CLIENT')
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow, server_default=func.now())
    
    # Relationships
    addresses = relationship('Address', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    cart_items = relationship('Cart', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    orders = relationship('Order', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reviews = relationship('Review', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    messages = relationship('Message', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint("role IN ('CLIENT', 'ADMIN')", name='check_user_role'),
    )
    
    def check_password(self, input_password: str) -> bool:
        return bcrypt.checkpw(input_password.encode('utf-8'), self.password.encode('utf-8'))
    
    def update_password(self, old_password: str, new_password: str) -> bool:
        if not bcrypt.checkpw(old_password.encode(), self.password.encode()):
            return False
        self.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        db.session.commit()
        return True
    
    def add_address(self, **kwargs: Any) -> "Address":
        kwargs["user_id"] = self.id
        address = Address(**kwargs)
        db.session.add(address)
        db.session.commit()
        return address


class Address(db.Model):
    __tablename__ = 'address_table'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_table.id'), nullable=False)
    type = Column(String, default='SHIPPING', server_default='SHIPPING')
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=True)
    postal_code = Column(String, nullable=False)
    country = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("type IN ('SHIPPING', 'BILLING')", name='check_address_type'),
    )


class Cart(db.Model):
    __tablename__ = 'cart_table'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_table.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product_table.id'), nullable=False)
    quantity = Column(Integer, default=1, server_default='1')
    added_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)
    
    product = relationship('Product', backref='cart_items')
    
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='unique_user_product_cart'),
        CheckConstraint('quantity > 0', name='check_cart_quantity'),
    )
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()


class Product(db.Model):
    __tablename__ = 'product_table'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(String, nullable=True)  # ID at supplier
    supplier_id = Column(Integer, ForeignKey('addon_table.id'), nullable=False)
    payment_processor_id = Column(Integer, ForeignKey('addon_table.id'), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, default='An amazing new product!', server_default='An amazing new product!')
    price = Column(Float, default=0.0, server_default='0.0')
    stock = Column(Integer, default=0, server_default='0')
    variant_of_id = Column(Integer, ForeignKey('product_table.id'), nullable=True)
    active = Column(Boolean, default=True, server_default='1')
    is_base = Column(Boolean, default=False, server_default='0')
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow, server_default=func.now())
    
    # Relationships
    images = relationship('Image', backref='product', lazy='selectin', cascade='all, delete-orphan', order_by='Image.position')
    categories = relationship('Category', secondary=product_category, backref='products', lazy='dynamic')
    variants = relationship('Product', backref=backref('base_product', remote_side=[id]), lazy='dynamic')
    supplier = relationship('Addon', foreign_keys=[supplier_id], backref='supplied_products')
    payment_processor = relationship('Addon', foreign_keys=[payment_processor_id], backref='processed_products')
    
    
    def get_variants(self) -> List["Product"]:
        base_id = self.id if self.is_base else self.variant_of_id
        return Product.query.filter_by(variant_of_id=base_id).all()
    
    def add_category(self, category: "Category") -> None:
        if category not in self.categories:
            self.categories.append(category)
            db.session.commit()
    
    def get_categories(self) -> List["Category"]:
        return self.categories.all()
    
    def delete_category(self, category: "Category") -> None:
        if category in self.categories:
            self.categories.remove(category)
            db.session.commit()
    
    def get_supplier(self) -> "Addon | None":
        return self.supplier


class Image(db.Model):
    __tablename__ = 'image_table'
    
    id = Column(Integer, primary_key=True)
    image_id = Column(String, nullable=True)  # ID at supplier
    product_id = Column(Integer, ForeignKey('product_table.id'), nullable=False)
    title = Column(String, default='Product Image', server_default='Product Image')
    alt_text = Column(Text, default='An amazing new product!', server_default='An amazing new product!')
    filename = Column(String, nullable=True)
    supplier_url = Column(String, nullable=True)
    position = Column(Integer, default=0, server_default='0')
    
    def delete(self) -> Dict[str, str]:
        filename = self.filename
        file_path = Path(current_app.instance_path) / "images" / filename
        product_id = self.product_id
        
        db.session.delete(self)
        db.session.commit()
        
        reorder_images(product_id)
        
        try:
            if file_path.is_file():
                file_path.unlink()
                return {"success": "File Deleted"}
            elif file_path.exists():
                return {"failed": "Path exists but is not a file"}
            else:
                return {"success": "File does not exist (nothing to delete)"}
        except FileNotFoundError:
            return {"success": "File already deleted or not found"}
        except PermissionError:
            return {"failed": "Permission denied deleting"}
        except OSError:
            return {"failed": "Error deleting file"}


def reorder_images(product_id: int) -> None:
    product_images = Image.query.filter_by(product_id=product_id).order_by(Image.position).all()
    if not product_images:
        return
    for i, image in enumerate(product_images, start=1):
        if image.position != i:
            image.position = i
    db.session.commit()


class Order(db.Model):
    __tablename__ = 'order_table'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_table.id'), nullable=False)
    shipping_cost = Column(Float, default=0.0, server_default='0.0')
    tax = Column(Float, default=0.0, server_default='0.0')
    other = Column(Float, default=0.0, server_default='0.0')
    total = Column(Float, default=0.0, server_default='0.0')
    status = Column(String, default='PENDING', server_default='PENDING')
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow, server_default=func.now())
    
    # Relationships
    order_products = relationship('OrderProduct', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    payments = relationship('OrderPayment', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    shippings = relationship('OrderShipping', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def add_product(self, **kwargs: Any) -> "OrderProduct":
        kwargs['order_id'] = self.id
        order_product = OrderProduct(**kwargs)
        db.session.add(order_product)
        db.session.commit()
        return order_product
    
    def get_products(self) -> List["OrderProduct"]:
        return self.order_products.all()
    
    def add_payment(self, **kwargs: Any) -> "OrderPayment":
        kwargs['order_id'] = self.id
        payment = OrderPayment(**kwargs)
        db.session.add(payment)
        db.session.commit()
        return payment
    
    def get_payments(self) -> List["OrderPayment"]:
        return self.payments.all()
    
    def add_shipping(self, **kwargs: Any) -> "OrderShipping":
        kwargs['order_id'] = self.id
        shipping = OrderShipping(**kwargs)
        db.session.add(shipping)
        db.session.commit()
        return shipping
    
    def get_shipping(self) -> List["OrderShipping"]:
        return self.shippings.all()


class OrderProduct(db.Model):
    __tablename__ = 'order_products'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order_table.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product_table.id'), nullable=False)
    amount = Column(Integer, default=0, server_default='0')
    price = Column(Float, default=0.0, server_default='0.0')  # Per item
    payment = Column(String, default='OUTSTANDING', server_default='OUTSTANDING')
    status = Column(String, default='PENDING', server_default='PENDING')
    
    product = relationship('Product', backref='order_products')


class OrderPayment(db.Model):
    __tablename__ = 'order_payments'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order_table.id'), nullable=False)
    payment_processor_id = Column(Integer, ForeignKey('addon_table.id'), nullable=False)
    payment_id = Column(String, nullable=False)  # ID at payment processor
    reference_id = Column(Integer, nullable=False)
    direction = Column(String, nullable=False)
    status = Column(String, nullable=True)
    
    payment_processor = relationship('Addon', backref='order_payments')


class OrderShipping(db.Model):
    __tablename__ = 'order_shipping'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('order_table.id'), nullable=False)
    supplier_id = Column(Integer, ForeignKey('addon_table.id'), nullable=False)
    cost = Column(Float, default=0.0, server_default='0.0')
    status = Column(String, default='PENDING', server_default='PENDING')
    
    supplier = relationship('Addon', backref='order_shippings')


class Category(db.Model):
    __tablename__ = 'category_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    def delete(self) -> None:
        db.session.delete(self)
        db.session.commit()


class Review(db.Model):
    __tablename__ = 'review_table'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('product_table.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user_table.id'), nullable=False)
    content = Column(Text, nullable=True)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow, server_default=func.now())
    
    product = relationship('Product', backref='reviews')


class Message(db.Model):
    __tablename__ = 'message_table'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_table.id'), nullable=True)
    subject = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    message_role = Column(String, default='CLIENT', server_default='CLIENT')
    type = Column(String, default='FLASH', server_default='FLASH')
    level = Column(String, default='INFO', server_default='INFO')
    template = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("message_role IN ('CLIENT', 'ADMIN')", name='check_message_role'),
        CheckConstraint("type IN ('FLASH', 'EMAIL')", name='check_message_type'),
        CheckConstraint("level IN ('INFO', 'WARNING', 'ERROR')", name='check_message_level'),
    )


class Addon(db.Model):
    __tablename__ = 'addon_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String, default='1.0', server_default='1.0')
    download_url = Column(String, nullable=True)
    active = Column(Boolean, default=False, server_default='0')
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow, server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('name', 'type', name='unique_addon_name_type'),
        CheckConstraint("type IN ('STYLE', 'PAYMENT', 'SUPPLIER', 'MESSAGING')", name='check_addon_type'),
    )
    
    @classmethod
    def new(cls, **kwargs: Any) -> "Addon":
        if "id" in kwargs:
            raise KeyError("Invalid ID key found")
        
        if kwargs['type'] == "MANUAL_SUPPLIER":
            kwargs['type'] = "SUPPLIER"
            default_list = kwargs.pop('default_list')
            addon = cls(**kwargs)
            db.session.add(addon)
            db.session.flush()
            last_id = addon.id
            for i in range(len(default_list)):
                default_list[i]["data"]["addon_id"] = last_id
            if not set_defaults(default_list):
                raise ValueError(f"Defaults for Addon: {kwargs['name']} failed to set")
            else:
                log.info(f"Finished setting defaults for {kwargs['name']}")
            db.session.commit()
            return addon
        
        addon = cls(**kwargs)
        db.session.add(addon)
        db.session.flush()
        
        last_id = addon.id

        log.debug(f"Addon type: {kwargs['type']}")
        log.debug(f"Addon name: {kwargs['name']}")
        log.debug(f"Addon id: {last_id}")
        
        addon_path: Path | None = None
        module_name = ""
        if kwargs['type'] == "STYLE":
            addon_path = Path('app') / 'styles' / kwargs['name'].lower()
            module_name = f"app.styles.{kwargs['name'].lower()}"
        elif kwargs['type'] == "SUPPLIER":
            addon_path = Path('app') / 'addons' / 'suppliers' / kwargs['name'].lower()
            module_name = f"app.addons.suppliers.{kwargs['name'].lower()}"
        elif kwargs['type'] == "MESSAGING":
            addon_path = Path('app') / 'addons' / 'messaging' / kwargs['name'].lower()
            module_name = f"app.addons.messaging.{kwargs['name'].lower()}"
        elif kwargs['type'] == "PAYMENT":
            addon_path = Path('app') / 'addons' / 'payments' / kwargs['name'].lower()
            module_name = f"app.addons.payments.{kwargs['name'].lower()}"

        log.debug(f"Addon path: {addon_path}")
        log.debug(f"Module name: {module_name}")
        
        if addon_path:
            spec = importlib.util.spec_from_file_location(
                module_name, addon_path / "__init__.py"
            )
            if spec and spec.loader:
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
        
        db.session.commit()
        return addon


class ConfigData(db.Model):
    """Config data model with encryption support via hybrid property"""
    __tablename__ = 'setup_table'
    
    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False)
    _value = Column('value', Text, nullable=False)  # Store encrypted value here
    type = Column(String, default='TEXT', server_default='TEXT')
    description = Column(Text, nullable=True)
    editable = Column(Boolean, default=True, server_default='1')
    secure = Column(Boolean, default=False, server_default='0')
    addon_id = Column(Integer, ForeignKey('addon_table.id', ondelete='CASCADE'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, onupdate=datetime.utcnow, server_default=func.now())
    
    addon = relationship('Addon', backref='configs')
    
    @hybrid_property
    def value(self) -> str:
        """Get decrypted value if secure, otherwise return raw value"""
        if self.secure:
            return encryption.decrypt_data(self._value)
        return self._value
    
    @value.setter
    def value(self, val: Any) -> None:
        """Set value, encrypting if secure"""
        if hasattr(self, 'secure') and self.secure:
            self._value = encryption.encrypt_data(str(val) if val is not None else '')
        else:
            self._value = str(val) if val is not None else ''
    
    def __repr__(self) -> str:
        return f"<ConfigValue {self.key}={self.value}>"
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __eq__(self, other: Any) -> bool:
        return self.value == other
    
    def __hash__(self) -> int:
        return hash(self.value)
    
    def __int__(self) -> int:
        return int(self.value)
    
    def __float__(self) -> float:
        return float(self.value)
    
    def __bool__(self) -> bool:
        return bool(self.value)
    
    def __len__(self) -> int:
        return len(self.value)
    
    def __getitem__(self, k: int | str) -> Any:
        return self.value[k]
    
    def __contains__(self, item: Any) -> bool:
        return item in self.value
    
    def __iter__(self) -> Iterator[str]:
        return iter(self.value)
    
    def meta(self) -> Dict[str, Any]:
        """Return all metadata (excluding the raw value)."""
        return {
            "editable": self.editable,
            "secure": self.secure,
            "description": self.description,
            "addon_id": self.addon_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "id": self.id,
            "key": self.key,
            "type": self.type
        }
    
    def delete(self) -> None:
        db.session.delete(self)
        db.session.commit()


class Config:
    def __init__(self, addon_id: Optional[int] = None) -> None:
        self._addon_id = addon_id
        self._cache: Dict[str, ConfigData] = {}
        self._load()
    
    def _load(self) -> None:
        if self._addon_id is None:
            configs = ConfigData.query.filter_by(addon_id=None).all()
        else:
            configs = ConfigData.query.filter_by(addon_id=self._addon_id).all()
        if not configs:
            raise ValueError(f"Config data for {'addon_id:' + str(self._addon_id) if self._addon_id else 'site'} not found, check defaults.")
        
        for config_data in configs:
            self._cache[config_data.key] = config_data
    
    def __getitem__(self, key: str) -> ConfigData:
        return self._cache[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Set value and persist immediately."""
        if key not in self._cache:
            raise KeyError(f"Config key '{key}' does not exist")
        self._cache[key].value = value
        db.session.commit()
    
    def __contains__(self, key: str) -> bool:
        return key in self._cache
    
    def __iter__(self) -> Iterator[str]:
        return iter(self._cache)
    
    def keys(self) -> KeysView[str]:
        return self._cache.keys()
    
    def values(self) -> ValuesView[Any]:
        return (cv.value for cv in self._cache.values())
    
    def items(self) -> ItemsView[str, Any]:
        return ((k, cv.value) for k, cv in self._cache.items())
    
    def data(self) -> Dict[str, Any]:
        """Plain dict of key → raw value."""
        return {k: cv.value for k, cv in self._cache.items()}
    
    def meta(self) -> Dict[str, Dict[str, Any]]:
        """All metadata for frontend/UI use."""
        return {k: cv.meta() for k, cv in self._cache.items()}
    
    @classmethod
    def new(cls, key: str, value: Any, *, addon_id: Optional[int] = None, **meta: Any) -> None:
        log.info('Adding new config')
        secure = meta.pop('secure', False)
        config_data = ConfigData(key=key, addon_id=addon_id, secure=secure, **meta)
        config_data.value = value
        db.session.add(config_data)
        db.session.commit()


def get_config(addon_name: Optional[str] = None, addon_id: Optional[int] = None, addon_type: Optional[str] = None) -> Config | List[Config]:
    if addon_id is not None:
        return Config(addon_id=addon_id)
    
    if addon_name is not None:
        addon = Addon.query.filter_by(name=addon_name).first()
        if not addon:
            raise KeyError(f"Addon '{addon_name}' not installed")
        return Config(addon_id=addon.id)
    
    if addon_type is not None:
        addons = Addon.query.filter_by(type=addon_type.upper()).all()
        if not addons:
            return []
        return [Config(addon_id=addon.id) for addon in addons]
    
    return Config()


def set_configs() -> Dict[str, Config]:
    """Returns all front-end config settings"""
    site_config = Config()
    log.info(f"Fetching config data for style: {site_config['style']}")
    
    addon = Addon.query.filter_by(name=str(site_config["style"]), type="STYLE").first()
    if not addon:
        raise KeyError("Style not installed")
    
    style_config = Config(addon_id=addon.id)
    
    return {
        "style_config": style_config,
        "site_config": site_config
    }


def set_defaults(default_list: List[Dict[str, Any]]) -> bool:
    classes = {
        "USER": User,
        "PRODUCT": Product,
        "IMAGE": Image,
        "ORDER": Order,
        "CATEGORY": Category,
        "SUPPLIER": Addon,  # Supplier is an Addon with type='SUPPLIER'
        "REVIEW": Review,
        "ADDON": Addon,
        "SETUP": ConfigData
    }
    try:
        for entry in default_list:
            log.info(f"Setting default {entry['type']} for {entry['object_name']}")
            if entry["type"] in ["NOT NULL", "NOT_NULL"]:
                cls_ = classes[entry["object_name"]]
                
                # Handle addon_id filter
                if entry['data'].get('addon_id') is not None:
                    query = cls_.query.filter_by(addon_id=entry['data']['addon_id'])
                    objects = query.all()
                else:
                    objects = cls_.query.all()
                exists = False
                if objects:
                    for set_object in objects:
                        if getattr(set_object, entry["key"], None) == entry["value"]:
                            exists = True
                if exists:
                    continue
                
                object_data = entry["data"].copy()
                object_data[entry["key"]] = entry["value"]
                # Create new object
                # Special handling for ConfigData to ensure encryption works properly
                if cls_ == ConfigData:
                    secure = object_data.pop('secure', False)
                    key_val = object_data.pop("value")
                    new_obj = cls_(secure=secure, **object_data)
                    new_obj.value = key_val  # This will encrypt if secure=True
                elif cls_ == Addon:
                    new_obj = cls_.new(**object_data)
                else:
                    new_obj = cls_(**object_data)
                
                db.session.add(new_obj)
                db.session.commit()
    except Exception as e:
        log.error(f"Failed loading defaults, {e}")
        db.session.rollback()
        raise ValueError(f"Failed loading defaults, {e}") from e
    return True
