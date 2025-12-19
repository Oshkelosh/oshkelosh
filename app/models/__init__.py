from . import models
from app.utils.logging import get_logger

log = get_logger(__name__)

def get_previews(list_type="ALL"):
    params = {"is_base": False}
    if list_type == "ALL":
        pass
    elif list_type == "ACTIVE":
        params["active"] = True
    products = models.Product.get(**params)
    product_list = []
    for product in products:
        product_list.append(models.Product.get_preview(product.id))
    return product_list
