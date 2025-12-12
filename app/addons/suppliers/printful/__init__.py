from .functions import get_sync_products

def sync_product(printful_data):
    get_sync_products(getattr(printful_data, "token"))




default_list = [
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "token",
        "data": {
            "value": "your private token",
            "description": "Bearer token for Printful",
        },
    },
]
options = []
