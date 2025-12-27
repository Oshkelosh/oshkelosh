from .limit_session import session
import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

def check_token(token: Optional[str]) -> bool:
    if token is None:
        return False
    url = "https://api.printful.com/oauth/scopes"
    header = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = session.get(url=url, headers=header)
        response.raise_for_status()
        result = response.json()
        scope_result = [entry["scope"] for entry in result["result"]["scopes"]]
        return True
    except Exception as e:
        log.error(f"Error during check token: {e}")
        return False


def get_products(token: str) -> List[Dict[str, Any]]:
    header = {
        "Authorization" : f"Bearer {token}"
    }
    offset = 0
    result_list: List[Dict[str, Any]] = []
    try:
        while True:
            url = f"https://api.printful.com/store/products?offset={offset}"
            response = session.get(url = url, headers = header)
            response.raise_for_status()
            result = response.json()
            result_list.extend(result["result"])
            next_offset = result["paging"]["offset"] + len(result["result"])
            if next_offset <= result["paging"]["total"]:
                break
            offset = next_offset
        return result_list
    except Exception as e:
        log.error(f"Error during sync products: {e}")
    return result_list

def get_product_details(token: str, product_id: str) -> Optional[Dict[str, Any]]:
    header = {
        "Authorization" : f"Bearer {token}"
    }
    try:
        url = f"https://api.printful.com/store/products/{product_id}"
        response = session.get(url = url, headers = header)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error(f"Error during sync product details: {e}")
        return None


