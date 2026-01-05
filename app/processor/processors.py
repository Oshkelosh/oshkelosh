from app.models import models
from app.database import db
import pathlib
import requests
import mimetypes
import os
import zipfile
import tempfile
import shutil
import importlib.util
import json
from typing import Any, Dict, List, Optional, Tuple

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
                product["supplier_id"] = supplier_id
                db_product = models.Product(**product)
                db.session.add(db_product)
                db.session.commit()
            
            if images:
                check_images(images, db_product.id)

        db_products = models.Product.query.filter_by(supplier_id=supplier_id).all()
        ids_in_data = [str(p["product_id"]) for p in product_data]
        log.debug(f"IDs in data: {ids_in_data}")
        for product in db_products:
            log.debug(f"Product: {product.product_id} - {product.product_id in ids_in_data}")
            if str(product.product_id) not in ids_in_data:
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


def download_addon_from_url(url: str) -> pathlib.Path:
    """Download ZIP file from URL to temporary directory."""
    temp_dir = pathlib.Path(tempfile.mkdtemp())
    zip_path = temp_dir / "addon.zip"
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in ["application/zip", "application/x-zip-compressed", "application/octet-stream"]:
            # Some servers don't set proper content-type, so we'll check the URL extension
            if not url.lower().endswith('.zip'):
                log.warning(f"Content-Type is {content_type}, but proceeding with download")
        
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verify it's a valid ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.testzip()
        
        return zip_path
    except requests.RequestException as e:
        if zip_path.exists():
            zip_path.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        raise ValueError(f"Failed to download addon from URL: {str(e)}") from e
    except zipfile.BadZipFile:
        if zip_path.exists():
            zip_path.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()
        raise ValueError("Downloaded file is not a valid ZIP file") from e


def validate_addon_structure(addon_path: pathlib.Path) -> Dict[str, Any]:
    """Validate addon structure and return addon_data and default_list."""
    init_file = addon_path / "__init__.py"
    if not init_file.exists():
        raise ValueError("Addon must contain __init__.py file")
    
    # Try to import the module
    try:
        spec = importlib.util.spec_from_file_location("addon_module", init_file)
        if not spec or not spec.loader:
            raise ValueError("Could not load addon module")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check for addon_data
        if not hasattr(module, 'addon_data'):
            raise ValueError("Addon __init__.py must contain 'addon_data' dict")
        
        addon_data = module.addon_data
        if not isinstance(addon_data, dict):
            raise ValueError("'addon_data' must be a dictionary")
        
        if 'type' not in addon_data:
            raise ValueError("'addon_data' must contain 'type' key")
        if 'name' not in addon_data:
            raise ValueError("'addon_data' must contain 'name' key")
        
        # Validate type
        valid_types = ['STYLE', 'PAYMENT', 'SUPPLIER', 'MESSAGING']
        if addon_data['type'] not in valid_types:
            raise ValueError(f"'type' must be one of: {', '.join(valid_types)}")
        
        # Check for default_list
        if not hasattr(module, 'default_list'):
            raise ValueError("Addon __init__.py must contain 'default_list'")
        
        default_list = module.default_list
        if not isinstance(default_list, list):
            raise ValueError("'default_list' must be a list")
        
        return {
            'addon_data': addon_data,
            'default_list': default_list
        }
    except ImportError as e:
        raise ValueError(f"Failed to import addon module: {str(e)}") from e
    except Exception as e:
        raise ValueError(f"Error validating addon structure: {str(e)}") from e


def check_defaults_compatibility(existing_addon_id: int, new_default_list: List[Dict]) -> Tuple[bool, List[str]]:
    """Check if new defaults are compatible with existing ones."""
    # Get existing ConfigData records
    existing_configs = models.ConfigData.query.filter_by(addon_id=existing_addon_id).all()
    existing_keys = {config.key for config in existing_configs}
    
    # Extract keys from new default_list
    new_keys = set()
    for entry in new_default_list:
        if 'key' in entry:
            new_keys.add(entry['key'])
    
    # Compatible if new is superset (all existing keys exist in new)
    incompatible_keys = existing_keys - new_keys
    is_compatible = len(incompatible_keys) == 0
    
    return is_compatible, list(incompatible_keys)


def delete_incompatible_defaults(addon_id: int, incompatible_keys: List[str]) -> None:
    """Delete ConfigData records for incompatible keys."""
    for key in incompatible_keys:
        config = models.ConfigData.query.filter_by(addon_id=addon_id, key=key).first()
        if config:
            config.delete()
    log.info(f"Deleted {len(incompatible_keys)} incompatible config keys for addon {addon_id}")


def preserve_compatible_configs(addon_id: int, compatible_keys: List[str]) -> List[Dict]:
    """Get ConfigData records for compatible keys to preserve."""
    preserved = []
    for key in compatible_keys:
        config = models.ConfigData.query.filter_by(addon_id=addon_id, key=key).first()
        if config:
            preserved.append({
                'key': config.key,
                'value': config.value,  # This will decrypt if secure
                'type': config.type,
                'secure': config.secure,
                'description': config.description,
                'editable': config.editable
            })
    return preserved


def install_addon(
    zip_path: pathlib.Path,
    upload_type: str,
    replace_existing: bool = False,
    existing_addon_id: Optional[int] = None,
    preserved_configs: Optional[List[Dict]] = None
) -> None:
    """Install addon from ZIP file."""
    temp_extract_dir = None
    try:
        # Extract ZIP to temp directory
        temp_extract_dir = pathlib.Path(tempfile.mkdtemp())
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        
        # Find the addon directory (could be root or in a subdirectory)
        addon_path = temp_extract_dir
        if not (addon_path / "__init__.py").exists():
            # Look for subdirectories
            subdirs = [d for d in addon_path.iterdir() if d.is_dir()]
            if len(subdirs) == 1:
                addon_path = subdirs[0]
            else:
                raise ValueError("Could not find addon directory in ZIP file")
        
        # Validate structure
        validation_result = validate_addon_structure(addon_path)
        addon_data = validation_result['addon_data']
        default_list = validation_result['default_list']
        
        addon_name = addon_data['name'].lower()
        addon_type = addon_data['type']
        
        # Determine target directory
        base_path = pathlib.Path(current_app.root_path)
        if addon_type == "STYLE":
            target_dir = base_path / 'styles' / addon_name
        elif addon_type == "SUPPLIER":
            target_dir = base_path / 'addons' / 'suppliers' / addon_name
        elif addon_type == "MESSAGING":
            target_dir = base_path / 'addons' / 'messaging' / addon_name
        elif addon_type == "PAYMENT":
            target_dir = base_path / 'addons' / 'payments' / addon_name
        else:
            raise ValueError(f"Invalid addon type: {addon_type}")
        
        # Handle replacement
        if replace_existing and existing_addon_id:
            existing_addon = models.Addon.query.get(existing_addon_id)
            if existing_addon:
                # Delete old files
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                
                # Delete old addon record (will cascade to ConfigData)
                db.session.delete(existing_addon)
                db.session.commit()
                log.info(f"Deleted existing addon {existing_addon.name} (ID: {existing_addon_id})")
        
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files to target directory
        for item in addon_path.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(addon_path)
                target_file = target_dir / relative_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_file)
        
        # Create Addon record (this will set defaults)
        addon_kwargs = {
            'name': addon_data['name'],
            'type': addon_type,
            'description': addon_data.get('description'),
            'version': addon_data.get('version', '1.0'),
            'download_url': addon_data.get('download_url'),
            'active': addon_data.get('active', False)
        }
        new_addon = models.Addon.new(**addon_kwargs)
        
        # If we preserved configs, restore them (after set_defaults has run)
        if preserved_configs:
            # Build a map of new default_list entries by key for structure reference
            default_map = {}
            for entry in default_list:
                if entry.get('object_name') == 'SETUP' and 'key' in entry:
                    default_map[entry['key']] = entry.get('data', {})
            
            for config_data in preserved_configs:
                key = config_data['key']
                # Check if it was already created by Addon.new() via set_defaults
                existing = models.ConfigData.query.filter_by(
                    addon_id=new_addon.id,
                    key=key
                ).first()
                
                if existing:
                    # Update with preserved value, but keep new structure if available
                    if key in default_map:
                        # Use structure from new default_list
                        default_data = default_map[key]
                        if 'type' in default_data:
                            existing.type = default_data['type']
                        if 'secure' in default_data:
                            existing.secure = default_data['secure']
                        if 'description' in default_data:
                            existing.description = default_data['description']
                        if 'editable' in default_data:
                            existing.editable = default_data['editable']
                    # Always preserve the value
                    existing.value = config_data['value']
                    db.session.commit()
                else:
                    # Config not in new default_list, but we want to preserve it
                    # Use preserved structure
                    new_config = models.ConfigData(
                        key=key,
                        addon_id=new_addon.id,
                        type=config_data['type'],
                        secure=config_data['secure'],
                        description=config_data['description'],
                        editable=config_data['editable']
                    )
                    new_config.value = config_data['value']
                    db.session.add(new_config)
                    db.session.commit()
            
            log.info(f"Restored {len(preserved_configs)} preserved config values")
        
        log.info(f"Successfully installed addon {addon_name} (type: {addon_type})")
        
    finally:
        # Cleanup temp files
        if temp_extract_dir and temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)
        if zip_path.exists():
            zip_path.unlink()
            zip_path.parent.rmdir()  # Remove temp directory
