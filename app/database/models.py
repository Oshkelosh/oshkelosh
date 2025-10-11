from .schema import schema
from .schema import db_path
from .migrations import get_columns

import sqlite3, os, datetime, time
import json, string
import keyword

import bcrypt
from cryptography.fernet import Fernet
from dotenv import dotenv_values

def safe_name(name):
    alphabet = string.ascii_lowercase
    stripped = ''.join(letter if letter in alphabet else '_' for letter in name.lower())

def check_names(name):
    name = safe_name(name)
    while name.startswith('_'):
        name = name[1:]
    while name.endswith('_'):
        name = name[:-1]
    while '__' in name:
        name.replace('__','_')
    if name == '':
        raise ValueError('Name not accepted!')
    if name.lower() in [word.lower() for word in keyword.kwlist]:
        raise ValueError('Name not accepted!')
    return name

def get_columns(schema, table_name):
    if not table_name:
        raise KeyError("Expected Table Name")
    for table in schema:
        if table["table_name"] == table_name:
            columns = table["table_columns"].keys()
            if "FOREIGN KEY" in columns:
                columns.remove('FOREIGN KEY')
    raise KeyError(f"Table {table_name} not in Schema")

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

class User():
    non_update = ['id', 'created_at', 'updated_at']
    def __init__(self,**kwargs):
        table_columns = get_columns(schema, "user_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            if arg in ["shipping_address", "billing_address", "cart"]:
                setattr(self, arg, json.loads(kwargs[arg]))
            else:
                setattr(self, arg, kwargs[arg])
    
    def getattr(self, key):
        return getattr(self, key)

    def check_password(self, input_password):
        return bcrypt.checkpw(input_password.encode(), self.password.encode())

    def update_password(self, old_password, new_password):
        if not bcrypt.checkpw(old_password.encode(), self.password.encode()):
            return False
        self.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self.update()
        return True
    
    def update(self):
        table_columns = get_columns(schema, "user_table")
        for key in non_update:
            table_columns.remove(key)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE user_table SET {" = ?, ".join[table_columns]}, updated_at = TIMESTAMP WHERE id = ?"
            data = [self.getattr(key) if key not in ["shipping_address", "billing_address", "cart"] else json.dumps(self.getattr(key)) for key in table_columns]
            data.append(self.id)
            cursor.execute(query,data)
            conn.commit()
        return True

def get_user(**kwargs):
    """Returns User by 'id' or 'email', or all"""
    if kwargs is None:
        users = []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = dict_factory
            cursor = conn.cursor()
            data = cursor.execute("SELECT * FROM user_table").fetchall()
            if data:
                for entry in data:
                    users.append(User(**entry))
        return users

    if 'id' in kwargs:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            data = cursor.execute("SELECT * FROM user_table WHERE id=?",kwargs['id']).fetchone()
            if data:
                user_data={key: data[key] for key in data.keys()}
                return User(**user_data)

    if 'email' in kwargs:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            data = cursor.execute("SELECT * FROM user_table WHERE id=?",kwargs['email']).fetchone()
            if data:
                user_data={key: data[key] for key in data.keys()}
                return User(**user_data)
    else:
        raise KeyError(f"Incorrect user details. Required 'id' or 'email' not: {", ".join(kwargs.keys())}")


def add_user(**kwargs):
    """Kwargs: ["name","surname","email","phone","password","shipping_address","billing_address"]"""
    table_columns = get_columns(schema, "user_table")
    for entry in ["id", "role", "cart"]:
        table_columns.remove(entry)
        
    missing = [arg for arg in table_columns if arg not in kwargs]
    if missing:
        raise KeyError(f"Missing required arguments: {', '.join(missing)}")

    user_data = {key: kwargs[key] for key in table_columns}
    user_data["password"] = bcrypt.hashpw(kwargs["password"].encode(), bcrypt.gensalt()).decode()
    user_data["role"] = "CLIENT"
    user_data["shipping_address"] = json.dumps(kwargs["shipping_address"])
    user_data["billing_address"] = json.dumps(kwargs["billing_address"])
    user_data["cart"] = []
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO user_table ({', '.join(user_data.keys())})
            VALUES ({", ".join(['?' for _ in user_data])})
        """, tuple(user_data.values()))
        conn.commit()



class Product():
    non_update = ['id', 'product_id', 'supplier_id', 'variant_of_id', 'created_at', 'updated_at']
    def __init__(self, **kwargs):
        table_columns = get_columns(schema, "product_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            setattr(self, arg, kwargs[arg])

    def getattr(self, key):
        return getattr(self, key)

    def update(self):
        table_columns = get_columns(schema, "product_table")
        for key in self.non_update:
            table_columns.remove(key)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE product_table SET {" = ?, ".join[table_columns]}, updated_at = TIMESTAMP WHERE id = ?"
            data = [self.getattr(key) for key in table_columns]
            data.append(self.id)
            cursor.execute(query,data)
            conn.commit()
        return True
    
    def add_category(self, **kwargs):
        pass
    def get_categories(self):
        pass
    def delete_category(self, **kwargs):
        pass

    def get_supplier(self):
        pass
      
def get_product(**kwargs):
    """Returns Product by 'id', 'product_id', 'supplier_id', 'category_id', 'variant_of_id' or all"""
    products = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if kwargs is None:
            data = cursor.execute("SELECT * FROM product_table").fetchall()
            if data:
                for entry in data:
                    product_data={key: entry[key] for key in entry.keys()}
                    products.append(Product(**product_data))
        elif 'id' in kwargs:
            data = cursor.execute("SELECT * FROM product_table WHERE id=?",kwargs['id']).fetchone()
            if data:
                product_data={key: data[key] for key in data.keys()}
                products = Product(**product_data)
        elif 'product_id':
            data = cursor.execute("SELECT * FROM product_table WHERE product_id=?",kwargs['product_id']).fetchone()
            if data:
                product_data={key: data[key] for key in data.keys()}
                products = Product(**product_data)
        elif 'variant_of_id':
            data = cursor.execute("SELECT * FROM product_table WHERE variant_of_id=?",kwargs['variant_of_id']).fetchone()
            if data:
                product_data={key: data[key] for key in data.keys()}
                products = Product(**product_data)
        elif 'supplier_id' in kwargs:
            data = cursor.execute("SELECT * FROM product_table WHERE supplier_id = ?", kwargs["supplier_id"]).fetchall()
            if data:
                for entry in data:
                    products.append(Product(**product_data))
        elif 'category_id' in kwargs:
            pass

    return products


def add_product(**kwargs):
    """Kwargs: ["name","surname","email","phone","password","shipping_address","billing_address"]"""
    table_columns = get_columns(schema, "product_table")
    for entry in ["id", "role", "cart"]:
        table_columns.remove(entry)
        
    missing = [arg for arg in table_columns if arg not in kwargs]
    if missing:
        raise KeyError(f"Missing required arguments: {', '.join(missing)}")

    user_data = {key: kwargs[key] for key in table_columns}
    user_data["password"] = bcrypt.hashpw(kwargs["password"].encode(), bcrypt.gensalt()).decode()
    user_data["role"] = "CLIENT"
    user_data["shipping_address"] = json.dumps(kwargs["shipping_address"])
    user_data["billing_address"] = json.dumps(kwargs["billing_address"])
    user_data["cart"] = []
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO product_table ({", ".join(user_data.keys())})
            VALUES ({", ".join(['?' for _ in user_data])})
        """, tuple(user_data.values()))
        conn.commit()


    
class Image():
    non_update = ['id', 'product_id']
    def __init__(self, **kwargs):
        table_columns = get_columns(schema, "image_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            setattr(self, arg, kwargs[arg])

    def getattr(self, key):
        return getattr(self, key)

    def update(self):
        table_columns = get_columns(schema, "image_table")
        for key in non_update:
            table_columns.remove(key)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE image_table SET {" = ?, ".join[table_columns]} WHERE id = ?"
            data = [self.getattr(key) for key in table_columns]
            data.append(self.id)
            cursor.execute(query,data)
            conn.commit()
        return True

      
    def delete(self):
        with sqlite3.connect(db_path) as connection:
            query = "DELETE FROM image_table WHERE id = ?"
            data = [self.id]
            cursor = connection.cursor()
            cursor.execute(query,data)
            connection.commit()


      
class Order():
    non_update = ['id', 'user_id', 'created_at', 'updated_at']
    def __init__(self, **kwargs):
        table_columns = get_columns(schema, "order_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            setattr(self, arg, kwargs[arg])

    def getattr(self, key):
        return getattr(self, key)

    def update(self):
        table_columns = get_columns(schema, "order_table")
        for key in non_update:
            table_columns.remove(key)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE order_table SET {" = ?, ".join[table_columns]}, updated_at = TIMESTAMP WHERE id = ?"
            data = [self.getattr(key) for key in table_columns]
            data.append(self.id)
            cursor.execute(query,data)
            conn.commit()
        return True
    
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






class Category():
    def __init__(self, **kwargs):
        table_columns = get_columns(schema, "category_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            setattr(self, arg, kwargs[arg])
            
    def getattr(self, key):
        return getattr(self, key)

    def update(self, *args):
        table_columns = get_columns(schema, "category_table")
        table_columns.remove("id")  #Exclude 'id' as not updateable

        if not args:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                query = f"UPDATE user_table SET {"=?, ".join[table_columns]}"
                data = [self.getattr(key) for key in table_columns]
                cursor.execute(query,data)
                conn.commit()
            return True

        not_common = [key for key in args if key not in table_columns]
        if not_common:
            raise KeyError(f"Key not recognized: {", ".join[not_common]}")

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE user_table SET {"=?, ".join[args]}"
            data = [self.getattr(key) for key in args]
            cursor.execute(query,data)
            conn.commit()
        return True
        
    def delete(self):
        with sqlite3.connect(db_path) as connection:
            query = "DELETE FROM category_table WHERE id=?"
            data = [self.id]
            cursor = connection.cursor()
            cursor.execute(query,data)
            connection.commit()
    
def get_categories():
    pass


            
class Supplier():
    def __init__(self, **kwargs):
        table_columns = get_columns(schema, "supplier_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            setattr(self, arg, kwargs[arg])
            
    def getattr(self, key):
        return getattr(self, key)

    def update(self, *args):
        table_columns = get_columns(schema, "supplier_table")
        table_columns.remove("id")  #Exclude 'id' as not updateable
        self.updated_at = int(time.time())

        if not args:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                query = f"UPDATE user_table SET {"=?, ".join[table_columns]}"
                data = [self.getattr(key) for key in table_columns]
                cursor.execute(query,data)
                conn.commit()
            return True

        not_common = [key for key in args if key not in table_columns]
        if not_common:
            raise KeyError(f"Key not recognized: {", ".join[not_common]}")

        args = list(args).append('updated_at')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE user_table SET {"=?, ".join[args]}"
            data = [self.getattr(key) for key in args]
            cursor.execute(query,data)
            conn.commit()
        return True
    
    def get_products(self):
        pass





class PaymentProcessor():
    def __init__(self, **kwargs):
        table_columns = get_columns(schema, "payment_processor_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            setattr(self, arg, kwargs[arg])

    def getattr(self, key):
        return getattr(self, key)

    def update(self, *args):
        table_columns = get_columns(schema, "payment_processor_table")
        table_columns.remove("id")  #Exclude 'id' as not updateable
        self.updated_at = int(time.time())

        if not args:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                query = f"UPDATE user_table SET {"=?, ".join[table_columns]}"
                data = [self.getattr(key) for key in table_columns]
                cursor.execute(query,data)
                conn.commit()
            return True

        not_common = [key for key in args if key not in table_columns]
        if not_common:
            raise KeyError(f"Key not recognized: {", ".join[not_common]}")

        args = list(args).append('updated_at')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE user_table SET {"=?, ".join[args]}"
            data = [self.getattr(key) for key in args]
            cursor.execute(query,data)
            conn.commit()
        return True

def get_payment_processors():
    pass

        
class Review():
    def __init__(self, **kwargs):
        table_columns = get_columns(schema, "review_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns.keys():
            setattr(self, arg, kwargs[arg])

    def getattr(self, key):
        return getattr(self, key)

    def update(self, *args):
        table_columns = get_columns(schema, "review_table")
        table_columns.remove("id")  #Exclude 'id' as not updateable
        self.updated_at = int(time.time())

        if not args:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                query = f"UPDATE user_table SET {"=?, ".join[table_columns]}"
                data = [self.getattr(key) for key in table_columns]
                cursor.execute(query,data)
                conn.commit()
            return True

        not_common = [key for key in args if key not in table_columns]
        if not_common:
            raise KeyError(f"Key not recognized: {", ".join[not_common]}")
        args = list(args).append('updated_at')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE user_table SET {"=?, ".join[args]}"
            data = [self.getattr(key) for key in args]
            cursor.execute(query,data)
            conn.commit()
        return True

def add_review(product_id):
    pass

def get_reviews(product_id):
    if product_id is None:
        raise KeyError('Expected product_id')
    reviews = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        data = cursor.execute("SELECT * FROM review_table WHERE product_id=?",product_id).fetchall()
        if data:
            for entry in data:
                reviews.append(Review(**product_data))
    return reviews

class Addon():
    non_update = ['id', 'name', 'created_at', 'updated_at']
    def __init__(self,**kwargs):
        table_columns = get_columns(schema, "addon_table")
        missing = [arg for arg in table_columns if arg not in kwargs]
        excess = [arg for arg in kwargs if arg not in table_columns]
        if missing:
            raise KeyError(f"Missing required arguments: {', '.join(missing)}")
        if excess:
            raise KeyError(f"Unknown arguments: {', '.join(excess)}")
        for arg in table_columns:
            setattr(self, arg, kwargs[arg])
    
    def getattr(self, key):
        return getattr(self, key)
    
    def update(self):
        table_columns = get_columns(schema, "addon_table")
        for key in non_update:
            table_columns.remove(key)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE addon_table SET {" = ?, ".join[table_columns]}, updated_at = TIMESTAMP WHERE id = ?"
            data = [self.getattr(key) for key in table_columns]
            data.append(self.id)
            cursor.execute(query,data)
            conn.commit()
        return True

def get_addons():
    pass

class ConfigData():
    def __init__(self, **kwargs):
        self._parent = kwargs.pop('parent', None)
        self._attr_name = kwargs.pop('attr_name', None)
        self._value = kwargs.pop('value')
        for arg in kwargs.keys():
            setattr(self, arg, kwargs[arg])
            
    def __getattr__(self, name):
        return getattr(self._value, name)
    def __str__(self):
        return str(self._value)
    def __repr__(self):
        return repr(self._value)

    def delete(self):
        with sqlite3.connect(db_path) as connection:
            query = "DELETE FROM setup_table WHERE id=?"
            data = [self.id]
            cursor = connection.cursor()
            cursor.execute(query,data)
            connection.commit()
        if self._parent and self._attr_name:
            delattr(self._parent, self._attr_name)
        

class Config():
    non_update = ['id', 'key', 'addon_id', 'created_at', 'updated_at']
    def __init__(self, addon_id = None):
        self.type = 'ADDON' if addon_id else 'GLOBAL'

    def set_config(self, key, **kwargs):
        setattr(self, key, ConfigData(parent=self, attr_name=key, **kwargs))

    def list_keys(self):
        return [key for key in self.__dict__.keys() if key != 'type']

    def data(self):
        """Returns only 'value' from ConfigData, instead of all meta-data"""
        data = {}
        for key in self.list_keys():
            data[key] = str(getattr(self, key))
        return data
            
    def update(self):
        success = True
        data = {}
        for key, value in self.__dict__.items():
            data['key'] = key
            for meta_key, meta_value in value.__dict__.items():
                data[meta_key] = meta_value
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                set_clauses = []
                params = []
                for key, value in data.items():
                    if key in self.non_update:  #Keys not no be updated
                        continue
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
                where_clause = 'WHERE id = ?'
                params.append(data['id'])
                query = f'UPDATE setup_table SET {set_query}, updated_at = CURRENT_TIMESTAMP {where_clause}'
                cursor.execute(query, params)
                if cursor.rowcount == 0:
                    success = False
                conn.commit()
        except sqlite3.Error as e:
            print(f'Config update error: {e}')
            success = False
        return success
    
def get_config(addon_name = None, addon_id = None):
    config = None

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        if addon_name:
            data = cursor.execute("SELECT * FROM addon_table WHERE name=?",(addon_name,)).fetchone()
            if data:
                addon_id = data['id']
            else:
                raise KeyError(f"Addon '{addon_name}' not installed")

        query = f"SELECT * FROM setup_table WHERE addon_id {'= ?' if addon_id else 'IS NULL'}"
        params = (addon_id,) if addon_id else ()
        data = cursor.execute(query,params).fetchall()
        if data:
            config = Config(addon_id)
            for entry in data:
                config_key = entry.pop('key')
                config.set_config(config_key, **entry)
        else:
            raise ValueError('Setup Table not found! Please restart the Oshkelosh app.')
    return config

def set_configs():
    addon = {}
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        data = cursor.execute("SELECT * FROM addon_table")
        if data:
            for entry in data:
                addon[entry["id"]] = entry["name"]
    configs = {}
    configs["site_config"] = get_config()
    for id, name in addon.items():
        configs[f'{name}_style'] = get_config(addon_id=id)
    return configs

