from app.models import models
from .processors import check_products, save_image
from . import manual
from . import checkout

from app.utils.logging import get_logger
from app.utils import site_config

log = get_logger(__file__)

import importlib

def sync_products() -> None:
    addon_list = models.Addon.query.filter_by(type='SUPPLIER').all()
    for supplier in addon_list:
        config = models.get_config(addon_id=supplier.id)
        data = config.data()

        try:
            module_path = f'app.addons.suppliers.{supplier.name}'
            module = importlib.import_module(module_path)
            sync_function = getattr(module, 'sync_product')
            session = getattr(module, 'session')
            base_products = []
            variant_products = []
            product_data = sync_function(data)
            for base in product_data:
                variants = base.pop("variants")
                if "is_base" not in base:
                    base["is_base"] = True
                for variant in variants:
                    if "is_base" not in variant:
                        variant["is_base"] = False
                    variant_products.append(variant)
                base_products.append(base)
            product_list = []
            product_list.extend(base_products)
            product_list.extend(variant_products)
            check_products(product_list, supplier.id, session)

        except ImportError as e:
            log.warning(f"Failed importing supplier addon {supplier.name}: {e}")
        except AttributeError as e:
            log.warning(f"Supplier addon {supplier.name} missing attribute: {e}")
        except Exception as e:
            log.error(f"Error running sync_products for supplier addon {supplier.name}: {e}")

def cart_to_checkout(user_id: int) -> None:
    user = models.User.query.filter_by(id=user_id).first()
    if not user:
        raise Exception("User not found")
    site = site_config.get_config("site_config")
    currency = site["currency"]
    cart_items = models.Cart.query.filter_by(user_id=user_id).all()
    supplier_data = {}
    for cart_item in cart_items:
        product = cart_item.product
        product_data = {
            "product": product,
            "quantity": cart_item.quantity,
        }
        if product.supplier_id not in supplier_data:
            supplier_data[product.supplier_id] = {
                "shipping_cost": 0.0,
                "products": [],
            }
            supplier_data.append(supplier_data)
        
        supplier_data[product.supplier_id]["products"].append(product_data)
    
    for supplier_id, supplier_data in supplier_data.items():
        supplier = models.Addon.query.filter_by(id=supplier_id).first()
        if supplier and not getattr(supplier, 'manual', False):
            shipping_cost = checkout.calculate_shipping(supplier, user, supplier_data["products"], currency)
            supplier_data["shipping_cost"] = shipping_cost

