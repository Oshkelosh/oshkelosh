import requests
import json

from app.database import models
from app.exceptions import AuthorizationError

def check_token(token=None, scopes=None) -> bool:
    if token is None:
        return False
    url = "https://api.printful.com/oauth/scopes"
    header = {
        "Authorization": f"Bearer {token}"
    }
    try:
        result = requests.get(url=url, headers=header)
        result.raise_for_status()
        json_result = result.json()
        result_scopes = [entry["scope"] for entry in json_result["result"]["scopes"]]
        success = all(entry in result_scopes for entry in scopes)
        return success
    except Exception as e:
        return False


def get_sync_products(admin: models.User, printful: models.Config):
    if admin.role != 'ADMIN':
        raise AuthorizationError('Unauthorized action')
    token = printful.oauth_token
    url = "https://api.printful.com/store/products"
    header = {
        "Authorization" : f"Bearer {token}"
    }
    json_result = {}
    try:
        result = requests.get(url = url, headers = header)
        result.raise_for_status()
        json_result = result.json()
    except Exception as e:
        return
    synced_products = models.Product.get(supplier_id = printful.id)
    for product in json_result:
        found = False


