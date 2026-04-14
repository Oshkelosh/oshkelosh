from app.models import models
from app.utils.logging import get_logger

from flask import current_app

import importlib

log = get_logger(__file__)

def calculate_shipping(supplier, user, order, currency) -> float:
    try:
        module_path = f'app.addons.suppliers.{supplier.name}'
        module = importlib.import_module(module_path)
        calculate_shipping_function = getattr(module, 'calculate_shipping')
        data = {    # Must contain supplier_data, address, user, order, currency
            "supplier_data": supplier.to_dict(), 
            "address": user.addresses.filter_by(type='SHIPPING').first(),
            "user": user.to_dict(),
            "order": order,
            "currency": currency,
        }
        return calculate_shipping_function(data)
    except ImportError as e:
        log.warning(f"Failed importing supplier addon {supplier.name}: {e}")
    except AttributeError as e:
        log.warning(f"Supplier addon {supplier.name} missing attribute: {e}")
    except Exception as e:
        log.error(f"Error running calculate_shipping for supplier addon {supplier.name}: {e}")
    return 0.0