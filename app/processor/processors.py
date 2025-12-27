from app.models import models
from app.database import db
import pathlib
import requests
import mimetypes
import os
from typing import Any, Dict, List, Optional

from PIL import Image as PilImage

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.utils.logging import get_logger

from werkzeug.utils import secure_filename

log = get_logger(__file__)

session: Any = None

def check_products(product_data: List[Dict[str, Any]], supplier_id: int, addon_session: Any = None) -> None:
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
            db_product = models.Product.query.filter_by(product_id=product["product_id"]).first()
            if not db_product:
                if not product["is_base"]:
                    base_product_id = product.pop('base_product_id')
                    base_product = models.Product.query.filter_by(product_id=base_product_id).first()
                    if not base_product:
                        log.error(f"Base product with product_id {base_product_id} not found")
                        continue
                    product["variant_of_id"] = base_product.id
                db_product = models.Product(**product)
                db.session.add(db_product)
                db.session.commit()
            
            if not db_product.active:
                db_product.active = True
                db.session.commit()

            if images:
                check_images(images, db_product.id)

        db_products = models.Product.query.filter_by(supplier_id=supplier_id).all()
        product_ids_in_data = [p["product_id"] for p in product_data]
        for product in db_products:
            if product.product_id not in product_ids_in_data:
                product.active = False
        db.session.commit()
    except Exception as e:
        log.error(f"Exception during check_products: {e}")
        db.session.rollback()
        raise

def check_images(image_list: List[Dict[str, Any]], product_id: int) -> None:
    if not image_list:
        return
    try:
        product_image_list = models.Image.query.filter_by(product_id=product_id).all()
        for image in image_list:
            exists = False
            for product_image in product_image_list:
                if str(product_image.image_id) == str(image["image_id"]):
                    exists = True
                    break
            if not exists:
                db_image = models.Image(product_id=product_id, **image)
                db.session.add(db_image)
                db.session.flush()  # Get the ID
                base_name = f"productimage_{db_image.product_id}_{db_image.id}"
                filename = download_image(db_image.supplier_url, base_name)
                db_image.filename = filename
                db_image.position = len(product_image_list) + 1
                db.session.commit()

    except Exception as e:
        log.error(f"Exception during check_images: {e}")
        db.session.rollback()
        raise


# ALLOWED_EXTENSIONS will be accessed via current_app.config.get() when needed

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
        allowed_extensions = current_app.config.get("IMAGE_EXTENSIONS", {'png', 'jpg', 'jpeg', 'gif', 'webp'})
        if ext not in allowed_extensions:
            raise ValueError(f"Invalid file extension: {ext}. Allowed: {', '.join(allowed_extensions)}")


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

def save_image(filename: str, file: FileStorage) -> None:
    save_path = pathlib.Path(current_app.instance_path) / "images"
    original_filename = secure_filename(file.filename)
    ext = os.path.splitext(original_filename)[1].lower().lstrip('.')
    
    # Validate extension
    allowed_extensions = current_app.config.get("IMAGE_EXTENSIONS", {'png', 'jpg', 'jpeg', 'gif', 'webp'})
    if not ext or ext not in allowed_extensions:
        raise ValueError(f"Invalid file extension: {ext}. Allowed: {', '.join(allowed_extensions)}")
    
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
