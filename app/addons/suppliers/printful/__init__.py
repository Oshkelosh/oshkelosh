from . import functions
from . import limit_session
import json
import logging

log = logging.getLogger(__name__)
session = limit_session.session

def sync_product(printful_data):
    try:
        log.info("Syncing Printful products . . .")
        token = printful_data["token"]
        product_list = functions.get_products(token)
        product_data = []
        for product in product_list:
            base = {
                "product_id": product["id"],
                "name": product["name"],
                "is_base": True,
                "variants": []
            }
            variant_data = functions.get_product_details(token, product["id"])
            for variant in variant_data["result"]["sync_variants"]:
                if variant["availability_status"] != "active":
                    continue
                data = {
                    "product_id":variant["id"],
                    "name": variant["name"],
                    "description": variant["product"]["name"],
                    "price": float(variant["retail_price"]),
                    "images":[],
                    "is_base": False,
                    "base_product_id": base["product_id"]
                }
                for file in variant["files"]:
                    if file["status"] == "ok" and file["type"] == "preview":
                        data["images"].append({
                            "image_id": file["id"],
                            "supplier_url":file["preview_url"],
                        })
                base["variants"].append(data)
            product_data.append(base)
        return product_data
    except Exception:
        raise

addon_data = {
    "name": "printful",
    "type": "SUPPLIER"
}
default_list = [
    {
        "object_name": "SETUP",
        "type": "NOT_NULL",
        "key": "key",
        "value": "token",
        "data": {
            "value": "your private token",
            "description": "Bearer token for Printful",
            "secure":True,
        },
    },
]
options = []
