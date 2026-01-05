from sqlalchemy import Boolean
from app.models import models
from app.utils.logging import get_logger

log = get_logger(__file__)


def add_supplier(name: str, contact_name: str, email: str, phone: str) -> Boolean:
    addon_data = {
        "name": name,
        "type": "MANUAL_SUPPLIER",
        "description": "Manual Supplier(Non-API)",
        "active": True,
        "default_list": [
            {
                "object_name": "SETUP",
                "type": "NOT_NULL",
                "key": "key",
                "value": "contact_name",
                "data": {
                    "value": contact_name,
                    "description": "Contact Person Name",
                },
            },
            {
                "object_name": "SETUP",
                "type": "NOT_NULL",
                "key": "key",
                "value": "email",
                "data": {
                    "value": email,
                    "description": "Contact email for the supplier",
                },
            },
            {
                "object_name": "SETUP",
                "type": "NOT_NULL",
                "key": "key",
                "value": "phone",
                "data": {
                    "value": phone,
                    "description": "Contact phone for the supplier",
                },
            },
            {
                "object_name": "SETUP",
                "type": "NOT_NULL",
                "key": "key",
                "value": "manual",
                "data": {
                    "value": True,
                    "description": "Is manual supplier",
                    "editable": False,
                    "type": "BOOLEAN",
                },
            }
        ],
    }
    try:
        supplier = models.Addon.new(**addon_data)
        return True
    except Exception as e:
        log.error(f"Failed to add supplier {name}: {e}")
        return False

def add_product(name: str, description: str, price: float, stock: int, supplier_id: int, active: bool) -> Boolean:
    product = models.Product(name=name, description=description, price=price, stock=stock, supplier_id=supplier_id, active=active)
    db.session.add(product)
    db.session.commit()
    return True