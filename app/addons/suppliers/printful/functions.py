import requests
import json


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


def get_sync_products(token):
        
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
    for product in json_result["result"]:
        print(json.dumps(product, indent=4))


