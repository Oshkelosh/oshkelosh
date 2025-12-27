import bcrypt
from typing import Any, Dict, List

default_list: List[Dict[str, Any]] = [
    {
        "object_name": "USER",
        "type": "NOT_NULL",
        "key": "role",
        "value": "ADMIN",
        "data": {
            "name": "John",
            "surname": "Doe",
            "email": "admin@admin.com",
            "password": bcrypt.hashpw("Oshkelosh".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        },
    },
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "style",
        "data": {"value": "basic", "description": "The Styling and Theme applied to the site."},
    },

    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "site_name",
        "data": {"value": "Oshkelosh", "description": "The website name"},
    },
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "currency",
        "data": {"value": "USD", "description": "The display currency"},
    },
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "contact_email",
        "data": {
            "value": "admin@oshkelosh.com",
            "description": "Primary Contact email visible on website",
        },
    },
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "about",
        "data": {
            "value": """
                Welcome to Oshkelosh, the lightweight, open-source e-commerce framework built for creators who value simplicity and flexibility. Designed with Python's Flask at its core, Oshkelosh empowers you to spin up modular online stores—especially for print-on-demand (POD) and custom goods—without the bloat of heavy platforms.
    
                Founded in 2025 by a solo developer passionate about accessible tools, Oshkelosh started as a response to clunky ecomm setups. Drawing from the ethos of open-source pioneers like WooCommerce, we crafted a framework that's easy to extend, secure by default, and community-driven. Today, it's a growing ecosystem where solos launch shops in hours, agencies customize at scale, and contributors shape the future.
                """,
            "description": "The 'About' page text",
        },
    },
    {
        "object_name": "ADDON",
        "type": "NOT_NULL",
        "key": "name",
        "value": "basic",
        "data": {
            "type": "STYLE",
            "description": "Basic style and theme",
            "active": "1",
        },
    },
    {
        "object_name": "ADDON",
        "type": "NOT_NULL",
        "key": "name",
        "value": "printful",
        "data": {
            "type": "SUPPLIER",
            "description": "Printful Shop api",
            "active": "1",
        },
    },

]
