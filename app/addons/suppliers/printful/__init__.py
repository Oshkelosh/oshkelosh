from tarfile import data_filter
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

def calculate_shipping(printful_data):
    try:
        log.info("Calculating shipping cost . . .")
        token = printful_data["supplier_data"]["token"]
        address = printful_data["address"]
        user = printful_data["user"]
        order = printful_data["order"]
        currency = printful_data["currency"]
        country_code, state_code = functions.get_country_code(address)
        if country_code is None:
            raise Exception("Country code not found")

        recipient_data = {
            "address1": address["address1"],
            "address2": address["address2"],
            "city": address["city"],
            "state_code": state_code,
            "country_code": country_code,
            "zip": address["postal_code"],
            "phone": user["phone"],
        }

        items = []
        for item in order:
            data = {
                "variant_id": item["product_id"],
                "quantity": item["quantity"],
            }
            items.append(data)
        rates = functions.get_shipping_rates(recipient_data, items, currency, token)
        if rates["code"] != 200:
            raise Exception("Failed to get shipping rates")
        return rates["result"]
    except Exception:
        raise
