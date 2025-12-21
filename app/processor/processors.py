from app.models import models
import json
import pathlib
import requests
import mimetypes
import os

from PIL import Image as PilImage

from flask import current_app

from app.utils.logging import get_logger

from werkzeug.utils import secure_filename

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
                if str(product_image.image_id) == str(image["image_id"]):
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


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

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
        ext = extension.lstrip('.').lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid file extension: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")


        filename = f"{secured_base}{extension}"
        save_path = save_dir / filename

        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
    try:
        img = PilImage.open(str(save_path))
        
        # Resize to fit within 1000x1000 while preserving aspect ratio
        max_size = 1000
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, PilImage.Resampling.LANCZOS)  # High-quality resampling
        
        # Format-specific options (compression/quality)
        save_kwargs = {}
        if ext in {'jpg', 'jpeg'}:
            save_kwargs['quality'] = 85  # Balanced compression
            save_kwargs['optimize'] = True
        elif ext == 'png':
            save_kwargs['optimize'] = True
            save_kwargs['compress_level'] = 6  # Moderate compression
        elif ext == 'webp':
            save_kwargs['quality'] = 80  # Lossy compression
        elif ext == 'gif':
            save_kwargs['optimize'] = True
        
        img.save(str(save_path), **save_kwargs)  # Infer format from extension
        
    except Exception as e:
        os.remove(str(save_path))  # Clean up on failure
        raise ValueError(f"Image processing failed: {str(e)}") from e
    
    return filename

def save_image(filename, file):
    save_path = pathlib.Path(current_app.instance_path) / "images"
    original_filename = secure_filename(file.filename)
    ext = os.path.splitext(original_filename)[1].lower().lstrip('.')
    
    # Validate extension
    if not ext or ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid file extension: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Build full filename and path
    full_filename = f"{filename}.{ext}"
    save_path = pathlib.Path(current_app.instance_path) / "images"
    save_path.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    file_path = save_path / full_filename
    
    # Process image with PIL
    try:
        img = PilImage.open(file.stream)
        
        # Resize to fit within 1000x1000 while preserving aspect ratio
        max_size = 1000
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, PilImage.Resampling.LANCZOS)  # High-quality resampling
        
        # Save with format-specific options (compression/quality)
        save_kwargs = {}
        if ext in {'jpg', 'jpeg'}:
            save_kwargs['quality'] = 85  # Balanced compression
            save_kwargs['optimize'] = True
        elif ext == 'png':
            save_kwargs['optimize'] = True
            save_kwargs['compress_level'] = 6  # Moderate compression
        elif ext == 'webp':
            save_kwargs['quality'] = 80  # Lossy compression
        elif ext == 'gif':
            save_kwargs['optimize'] = True
        
        img.save(file_path, format=ext.upper(), **save_kwargs)
        
    except Exception as e:
        raise ValueError(f"Image processing failed: {str(e)}") from e
