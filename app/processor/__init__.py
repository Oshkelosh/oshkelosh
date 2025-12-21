from app.models import models
from .processors import check_products, save_image

from app.utils.logging import get_logger

log = get_logger(__file__)

import importlib
import json



def sync_products():
    addon_list = models.Addon.get(type='SUPPLIER')
    for supplier in addon_list:
        config = models.Config(addon_id=supplier.id)
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


