from . import models
from app.utils.logging import get_logger
from typing import List

log = get_logger(__name__)

def get_previews(list_type: str = "ALL") -> List[models.Product]:
    query = models.Product.query.filter_by(is_base=False)
    if list_type == "ACTIVE":
        query = query.filter_by(active=True)
    products = query.all()
    product_list: List[models.Product] = []
    for product in products:
        preview = models.Product.get_preview(product.id)
        if preview:
            product_list.append(preview)
    return product_list
