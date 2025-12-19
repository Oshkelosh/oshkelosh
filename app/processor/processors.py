from app.models import models
import json
import pathlib
import requests
import mimetypes

from flask import current_app

from app.utils.logging import get_logger

log = get_logger(__file__)

session = None

def check_products(product_data, supplier_id, addon_session = None):
    if not product_data:
        return

    global session
    if addon_session is not None:
        session = addon_session
    elif session is None:
        session = requests

    try:
        for product in product_data:
            images = []
            if "images" in product:
                images = product.pop("images")
            db_product = models.Product.get(product_id = product["product_id"])
            if not db_product:
                if not product["is_base"]:
                    base_product_id = product.pop('base_product_id')
                    base_product = models.Product.get(product_id=base_product_id)
                    product["variant_of_id"] = base_product[0].id
                db_product = models.Product.new(**product)
            else:
                db_product = db_product[0]
            
            if not db_product.active:
                db_product.active = True
                db_product.update()

            if images:
                check_images(images, db_product.id)

        db_products = models.Product.get(supplier_id=supplier_id)
        for product in db_products:
            if product.product_id not in [product_info["product_id"] for product_info in product_data]:
                product.active = False
                product.update()
    except Exception as e:
        log.error(f"Exception during check_products: {e}")
        raise

def check_images(image_list, product_id):
    if not image_list:
        return
    try:
        product_image_list = models.Image.get(product_id = product_id)
        for image in image_list:
            exists = False
            for product_image in product_image_list:
                if product_image.image_id == image["image_id"]:
                    exists = True
                    break
            if not exists:
                db_image = models.Image.new(**image, product_id=product_id)
                base_name = f"productimage_{db_image.product_id}_{db_image.id}"
                filename = download_image(db_image.supplier_url, base_name)
                db_image.filename = filename
                db_image.position = len(product_image_list)+1
                db_image.update()

    except Exception as e:
        log.error(f"Exception during check_images: {e}")
        raise

def download_image(url: str, base_filename: str) -> str:
    save_dir = pathlib.Path(current_app.instance_path) / "images"
    save_dir.mkdir(parents=True, exist_ok=True)

    secured_base = pathlib.Path(base_filename).name

    with session.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        if not content_type.startswith("image/"):
            raise ValueError(f"URL does not point to an image (Content-Type: {content_type})")

        # Infer extension from Content-Type (std lib, no extra deps)
        extension = mimetypes.guess_extension(content_type)
        if not extension:
            raise ValueError(f"Could not determine extension for Content-Type: {content_type}")
        
        filename = f"{secured_base}{extension}"
        save_path = save_dir / filename

        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        print(str(save_path))

    return filename

