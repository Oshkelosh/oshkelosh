import bcrypt

"""
'NOT_NULL' check if entry of that type exists
'PLACEHOLDER' check and fill table with minimum placeholders
"""

default_list=[
    {
        "table_name":"product_table",
        "instruction": "'amount':3,'PLACEHOLDER'",
        "data":{
            "name":"Sample",
            "description":"An amazing example product"
        },
    },
    {
        "table_name":"user_table",
        "instruction": "'role':'ADMIN','NOT_NULL'",
        "data":{
            "name":"John",
            "surname":"Doe",
            "email":"admin@admin.com",
            "password":bcrypt.hashpw("Oshkelosh".encode(), bcrypt.gensalt()).decode(),
        },
    },
    {
        "table_name":"addon_table",
        "instruction": "'name':'basic','NOT_NULL'",
        "data":{
            "type":"STYLE",
            "description":"Basic style and theme",
            "active":"1",
            "config":{}
        },
    },
    {
        "table_name":"setup_table",
        "instruction": "'key':'site_name','NOT_NULL'",
        "data":{
            "value":"Oshkelosh"
        },
    },
    {
        "table_name":"setup_table",
        "instruction": "'key':'style','NOT_NULL'",
        "data":{
            "value":"basic"
        },
    },
    {
        "table_name":"setup_table",
        "instruction": "'key':'site_icon','NOT_NULL'",
        "data":{
            "value":"/static/img/logo.png"
        },
    },
    {
        "table_name":"setup_table",
        "instruction": "'key':'favicon','NOT_NULL'",
        "data":{
            "value":"/static/img/favicon.ico"
        },
    },
    {
        "table_name":"setup_table",
        "instruction": "'key':'currency','NOT_NULL'",
        "data":{
            "value":"USD"
        },
    },
    {
        "table_name":"setup_table",
        "instruction": "'key':'contact_email','NOT_NULL'",
        "data":{
            "value":"admin@oshkelosh.com"
        },
    },
    {
        "table_name":"setup_table",
        "instruction": "'key':'about','NOT_NULL'",
        "data":{
            "value":"""
            Welcome to Oshkelosh, the lightweight, open-source e-commerce framework built for creators who value simplicity and flexibility. Designed with Python's Flask at its core, Oshkelosh empowers you to spin up modular online stores—especially for print-on-demand (POD) and custom goods—without the bloat of heavy platforms.

            Founded in 2025 by a solo developer passionate about accessible tools, Oshkelosh started as a response to clunky ecomm setups. Drawing from the ethos of open-source pioneers like WooCommerce, we crafted a framework that's easy to extend, secure by default, and community-driven. Today, it's a growing ecosystem where solos launch shops in hours, agencies customize at scale, and contributors shape the future.
            """
        },
    },
]