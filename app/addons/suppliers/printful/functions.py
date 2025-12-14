import requests
from ratelimit import limits, sleep_and_retry

import json

@sleep_and_retry
@limits(calls=120, period=60)
def session(method, url, headers) -> dict:
    if method == 'GET':
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        return response.json()
    if method == 'POST':
        response = requests.post(url=url, headers=headers)
        response.raise_for_status()
        return response.json()
    if method == 'PUT':
        response = requests.put(url=url, headers=headers)
        response.raise_for_status()
        return response.json()
    if method == 'DELTETE':
        response = requests.delete(url=url, headers=headers)
        response.raise_for_status()
        return response.json()
    raise KeyError("Unknown Method")

def check_token(token):
    if token is None:
        return False
    url = "https://api.printful.com/oauth/scopes"
    header = {
        "Authorization": f"Bearer {token}"
    }
    try:
        result = session("GET", url=url, headers=header)
        scope_result = [entry["scope"] for entry in result["result"]["scopes"]]
        print(json.dumps(scope_result, indent=4))
    except Exception as e:
        print(f"Error during check token: {e}")


def get_products(token):
        
    header = {
        "Authorization" : f"Bearer {token}"
    }
    offset = 0
    result_list = []
    try:
        while True:
            url = f"https://api.printful.com/store/products?offset={offset}"
            result = session('GET', url = url , headers = header)
            result_list.extend(result["result"])
            next_offset = result["paging"]["offset"] + len(result["result"])
            if next_offset <= result["paging"]["total"]:
                break
            offset = next_offset
        return result_list
    except Exception as e:
        print(f"Error during sync products: {e}")
    return result_list

def get_product_details(token, product_id):        
    header = {
        "Authorization" : f"Bearer {token}"
    }
    try:
        url = f"https://api.printful.com/store/products/{product_id}"
        return session('GET', url = url , headers = header)
    except Exception as e:
        print(f"Error during sync product details: {e}")


