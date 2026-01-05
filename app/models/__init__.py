from . import models
from app.utils.logging import get_logger
from typing import List
from sqlalchemy.orm import selectinload

log = get_logger(__name__)

def get_previews(list_type: str = "ALL") -> List[models.Product]:
    query = models.Product.query.filter_by(is_base=False)
    if list_type == "ACTIVE":
        query = query.filter_by(active=True)
    return query.options(selectinload(models.Product.images)).all()
