db_path = "./data/database.db"

schema = [
    {"table_name":"user_table",
    "table_columns":{
        "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
        "name":"TEXT NOT NULL",
        "surname":"TEXT NOT NULL",
        "email":"TEXT UNIQUE NOT NULL",
        "phone":"TEXT",
        "password":"TEXT NOT NULL",
        "role":"TEXT DEFAULT 'CLIENT' CHECK (role IN ('CLIENT', 'ADMIN'))",
        "shipping_address":"TEXT DEFAULT '{}'",
        "billing_address":"TEXT DEFAULT '{}'",
        "cart":"TEXT DEFAULT '[]'",
        "created_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at":"TIMESTAMP"
        }},
    {"table_name":"product_table",
    "table_columns":{
        "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
        "product_id":"TEXT",   #ID at supplier
        "supplier_id":"INTEGER",
        "payment_processor_id":"INTEGER",
        "name":"TEXT NOT NULL",
        "description":"TEXT DEFAULT 'An amazing new product!'",
        "price":"FLOAT DEFAULT 0.0",
        "stock":"INTEGER DEFAULT 0",
        "variant_of_id":"INTEGER",
        "active":"BOOL DEFAULT 1",
        "created_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at":"TIMESTAMP",
        "FOREIGN KEY":[{
                "key":"supplier_id",
                "parent_table":"supplier_table",
                "parent_key":"id"
            },
            {
                "key":"payment_processor_id",
                "parent_table":"payment_processor_table",
                "parent_key":"id"
            },
            {
                "key":"variant_of_id",
                "parent_table":"product_table",
                "parent_key":"id"
            }]
        }},
    {
        "table_name":"image_table",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "product_id":"INTEGER NOT NULL",
            "title":"TEXT NOT NULL",
            "alt_text":"TEXT DEFAULT 'An amazing new product!'",
            "url":"TEXT NOT NULL",
            "position":"INTEGER DEFAULT 0",
            "FOREIGN KEY":[{
                    "key":"product_id",
                    "parent_table":"product_table",
                    "parent_key":"id"
                }]
        }},
    {
        "table_name":"order_table",    #Ported from user cart on checkout
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "user_id":"INTEGER NOT NULL",
            "shipping_cost":"FLOAT  DEFAULT 0.0",
            "tax":"FLOAT  DEFAULT 0.0",
            "other":"FLOAT  DEFAULT 0.0",
            "total":"FLOAT  DEFAULT 0.0",
            "status":"TEXT DEFAULT 'PENDING'",
            "created_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at":"TIMESTAMP",
            "FOREIGN KEY":[{
                    "key":"user_id",
                    "parent_table":"user_table",
                    "parent_key":"id"
                }]
        }},
    {
        "table_name":"order_products",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "order_id":"INTEGER NOT NULL",  #Supplier order id
            "product_id":"INTEGER NOT NULL",
            "amount":"INTEGER  DEFAULT 0",
            "price":"FLOAT  DEFAULT 0.0",   #Per item
            "payment":"TEXT DEFAULT 'OUTSTANDING'",
            "status":"TEXT DEFAULT 'PENDING'",
            "FOREIGN KEY":[{
                    "key":"order_id",
                    "parent_table":"order_table",
                    "parent_key":"id"
                },
                {
                    "key":"product_id",
                    "parent_table":"product_table",
                    "parent_key":"id"
                }]
        }},
    {
        "table_name":"order_payments",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "order_id":"INTEGER NOT NULL",
            "payment_processor_id":"INTEGER NOT NULL",
            "payment_id":"TEXT NOT NULL",   #ID at payment processor
            "reference_id":"INTEGER  NOT NULL",   #ID for order payment received or product payment made, based on 'direction'
            "direction":"TEXT NOT NULL",
            "status":"TEXT",
            "FOREIGN KEY":[{
                    "key":"order_id",
                    "parent_table":"order_table",
                    "parent_key":"id"
                },
                {
                    "key":"payment_processor_id",
                    "parent_table":"payment_processor_table",
                    "parent_key":"id"
                }]
        }},
    {
        "table_name":"order_shipping",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "order_id":"INTEGER NOT NULL",
            "supplier_id":"INTEGER NOT NULL",
            "cost":"FLOAT DEFAULT 0.0",
            "status":"TEXT DEFAULT 'PENDING'",
            "FOREIGN KEY":[{
                    "key":"order_id",
                    "parent_table":"order_table",
                    "parent_key":"id"
                },
                {
                    "key":"supplier_id",
                    "parent_table":"supplier_table",
                    "parent_key":"id"
                }]
        }
    },
    {
        "table_name":"category_table",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "name":"TEXT NOT NULL",
            "description":"TEXT",
        }},
    {
        "table_name":"product_category",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "product_id":"INTEGER NOT NULL",
            "category_id":"INTEGER NOT NULL",
            "FOREIGN KEY":[{
                    "key":"product_id",
                    "parent_table":"product_table",
                    "parent_key":"id",
                },
                {
                    "key":"category_id",
                    "parent_table":"category_table",
                    "parent_key":"id",
                    "instruction":"ON DELETE CASCADE"
                }]
        }},
    {
        "table_name":"supplier_table",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "name":"TEXT NOT NULL",
            "description":"TEXT",
            "active":"BOOL DEFAULT 1",
            "api_key":"BLOB NOT NULL",
            "api_secret":"BLOB",
            "created_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at":"TIMESTAMP"
        }},
    {
        "table_name":"payment_processor_table",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "name":"TEXT NOT NULL",
            "description":"TEXT",
            "active":"BOOL DEFAULT 1",
            "api_key":"BLOB NOT NULL",
            "api_secret":"BLOB",
            "created_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at":"TIMESTAMP"
        }},
    {
        "table_name":"review_table",
        "table_columns":{
            "id":"INTEGER PRIMARY KEY AUTOINCREMENT",
            "product_id":"INTEGER NOT NULL",
            "user_id":"INTEGER NOT NULL",
            "content":"TEXT",
            "rating":"INTEGER NOT NULL",
            "created_at":"TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at":"TIMESTAMP",
            "FOREIGN KEY":[{
                    "key":"user_id",
                    "parent_table":"user_table",
                    "parent_key":"id"
                },
                {
                    "key":"product_id",
                    "parent_table":"product_table",
                    "parent_key":"id"
            }]
        }},
    {
    "table_name": "addon_table",
    "table_columns": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT NOT NULL",
        "type": "TEXT NOT NULL CHECK (type IN ('MODULE', 'STYLE'))",
        "description": "TEXT",
        "version": "TEXT DEFAULT '1.0'",
        "download_url": "TEXT",
        "installed": "BOOL DEFAULT 0",
        "active": "BOOL DEFAULT 0",
        "config": "TEXT DEFAULT '{}'",  # JSON for addon-specific settings
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TIMESTAMP",
        "UNIQUE":["name","type"]
        }},
    {
        "table_name": "setup_table",
        "table_columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "key": "TEXT NOT NULL UNIQUE",
            "value":"TEXT NOT NULL",
            "description":"TEXT",
            "editable":"BOOL DEFAULT 1",
            "addon_id":"INTEGER",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TIMESTAMP",
            "FOREIGN KEY":[{
                "key":"addon_id",
                "parent_table":"addon_table",
                "parent_key":"id",
                "instruction":"ON DELETE CASCADE"
            }]
        }}
]