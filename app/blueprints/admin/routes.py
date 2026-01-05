from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    Response,
    request,
    session as flask_session
)
from . import bp
from app.utils import site_config

from flask_login import current_user, login_required

from functools import wraps
from typing import Callable, Any
import json
import tempfile
import pathlib

from app.models import models, get_previews
from app.database import db

from app.utils.site_config import invalidate_config_cache
from app.utils.logging import get_logger

import app.processor as processors

from . import forms

log = get_logger(__name__)

def admin_required(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    @login_required
    def decorated_view(*args: Any, **kwargs: Any) -> Any:
        if current_user.role != 'ADMIN':
            abort(403)
        return f(*args, **kwargs)
    return decorated_view


@bp.route("/")
@admin_required
def index() -> str:
    upload_form = forms.AddonUploadForm()
    return render_template("core/index.html", upload_form=upload_form)


@bp.route("/sync-suppliers", methods=["POST"])
@admin_required
def sync_suppliers() -> Response:
    processors.sync_products()
    flash('Syncing Products')
    return redirect(url_for('admin.index'))


@bp.route("/settings", methods=["GET", "POST"])
@bp.route("/settings/<style_name>", methods=["GET", "POST"])
@admin_required
def settings(style_name: str | None = None) -> str | Response:
    setup = models.get_config(addon_name = style_name)
    formClass = forms.dynamic_form(setup)
    form = formClass()
    style = site_config.get_config("style_config")  #Get current style details
    if form.validate_on_submit():
        update = False
        for field in form:
            if field.name in ["submit", "csrf_token"]:
                continue
            if setup[field.name] != field.data:
                setup[field.name] = field.data
                update = True
        if update:
            invalidate_config_cache("site_config")
            invalidate_config_cache("style_config")


        return redirect(url_for('admin.settings', style_name=style_name))

    return render_template(
        "core/settings.html",
        form = form,
        style = style
    )


@bp.route('/users')
@admin_required
def users() -> str:
    data = models.User.query.all()
    users = [user for user in data if user.role == 'CLIENT']
    admins = [user for user in data if user.role == 'ADMIN']
    return render_template(
        "core/users.html",
        users = users,
        admins = admins
    )

@bp.route('/set-user/<int:id>/<direction>', methods=["POST"])
@admin_required
def set_user_role(id: int, direction: str) -> Response:
    user = models.User.query.get(id)
    if not user:
        abort(404, description="User not found")
    if user.role == 'CLIENT' and direction == 'ADD':
        user.role = 'ADMIN'
        db.session.commit()
        flash(f"{user.name} is now an Admin", "success")
    elif user.role == 'ADMIN' and direction == 'REMOVE':
        user.role = 'CLIENT'
        db.session.commit()
        flash(f"{user.name} as been removed as Admin", "success")
    else:
        flash("Invalid operation!", "danger")
    
    return redirect(url_for('admin.users'))

@bp.route('/products', methods=["GET", "POST"])
@admin_required
def products() -> str:
    add_product_form = forms.create_manual_product_form()
    if add_product_form.validate_on_submit():
        name = add_product_form.name.data
        description = add_product_form.description.data
        price = add_product_form.price.data
        stock = add_product_form.stock.data
        active = add_product_form.active.data
        supplier_id = add_product_form.supplier_id.data
        if processors.manual.add_product(name, description, price, stock, supplier_id, active):
            flash(f"Product {name} added successfully", "success")
        else:
            flash(f"Failed to add product {name}", "error")
        return redirect(url_for('admin.products'))

    products = get_previews()
    categories = models.Category.query.all()
    return render_template(
        "core/products.html",
        products = products,
        categories = categories,
        add_product_form = add_product_form
    )

@bp.route('/products/<product_id>', methods=["GET", "POST"])
@admin_required
def product(product_id: str) -> str | Response:
    product = models.Product.query.get(product_id)
    if not product:
        abort(404)
    product_form = forms.create_product_form(product)
    images = models.Image.query.filter_by(product_id=product_id).all()
    if product_form.validate_on_submit():
        update = False
        for field in product_form:
            if field.name in ["submit", "csrf_token", "supplier"]:
                continue
            if getattr(product, field.name) != field.data:
                setattr(product, field.name, field.data)
                update = True
        if update:
            db.session.commit()
            flash(f"Product {product.name} updated successfully", "success")
        else:
            flash(f"Failed to update product {product.name}", "error")
        return redirect(url_for('admin.product', product_id=product_id))

    return render_template(
        'core/product.html',
        product = product_form,
        images = images,
    )

@bp.route('/images')
@admin_required
def images() -> str:
    images = models.Image.query.all()
    return render_template(
        'core/images.html',
        images=images
    )

@bp.route('/images/<image_id>', methods=["GET", "POST"])
@admin_required
def image(image_id: str) -> str | Response:
    image = models.Image.query.get(image_id)
    if not image:
        abort(404)
    form = forms.create_image_form(image)
    if form.validate_on_submit():
        update = False
        for field in form:
            if field.name in ["submit", "csrf_token"]:
                continue
            if getattr(image, field.name) != field.data:
                setattr(image, field.name, field.data)
                update = True
        if update:
            db.session.commit()
        return redirect(url_for('admin.image', image_id=image.id))

    return render_template(
        'core/image.html',
        image = image,
        form = form
    )


@bp.route('/images/add/<product_id>', methods=["GET", "POST"])
@admin_required
def add_iamge(product_id: str) -> str | Response:
    form = forms.AddImageForm()
    if form.validate_on_submit():
        new_image = None
        try:
            images = models.Image.query.filter_by(product_id=product_id).all()
            new_position = len(images) + 1
            file = form.image.data
            new_image = models.Image(
                title=form.title.data,
                alt_text=form.alt_text.data,
                product_id=product_id,
                position=new_position
            )
            db.session.add(new_image)
            db.session.flush()  # Get the ID
            filename = f"productimage_{new_image.product_id}_{new_image.id}"
            new_image.filename = filename
            db.session.commit()
            processors.save_image(filename, file)

        except Exception as e:
            log.error(f'An error occured while uploading a new product image: {e}')
            db.session.rollback()
            flash("An unexpected error occured during file upload", "error")
            if new_image is not None:
                try:
                    db.session.delete(new_image)
                    db.session.commit()
                except:
                    pass
        return redirect(url_for('admin.product', product_id=product_id))
    return render_template(
        'core/add_image.html',
        form=form
    )




@bp.route('/images/remove/<image_id>', methods=["POST"])
@admin_required
def remove_image(image_id: str) -> Response:
    image = models.Image.query.get(image_id)
    if not image:
        abort(404)
    status = image.delete()
    if "success" in status:
        flash(status["success"])
    elif "failed" in status:
        flash(status["failed"], "warning")
    else:
        flash("Something went wrong", "error")
    return redirect(url_for('admin.images'))

@bp.route("/suppliers", methods=["GET", "POST"])
@admin_required
def suppliers() -> str | Response:
    manual_form = forms.AddSupplierForm()
    if manual_form.validate_on_submit():
        name = manual_form.name.data
        contact_name = manual_form.contact_name.data
        email = manual_form.email.data
        phone = manual_form.phone.data
        if processors.manual.add_supplier(name, contact_name, email, phone):
            flash(f"Supplier {name} added successfully", "success")
        else:  
            flash(f"Failed to add supplier {name}", "error")
        return redirect(url_for('admin.suppliers'))


    addons = models.Addon.query.filter_by(type="SUPPLIER", active=True).all()
    supplier_data = []
    for supplier in addons:
        config = models.get_config(addon_id=supplier.id)
        formClass = forms.dynamic_form(config)

        class extendedForm(formClass):
            pass
        form = extendedForm(prefix = f"supplier-{supplier.id}-")
        
        if form.submit.data and form.validate_on_submit():
            update = False
            for field in form:
                if field.short_name in ["submit", "csrf_token"]:
                    continue
                if config[field.short_name] != field.data:
                    config[field.short_name] = field.data
                    update = True
            if update:
                db.session.commit()
                flash(f"{supplier.name.capitalize()} data updated")
                return redirect(url_for('admin.suppliers'))

        data = {
            "name": supplier.name.capitalize(),
            "description": supplier.description.capitalize() if supplier.description else "",
            "updated_at": supplier.updated_at or supplier.created_at,
            "version": supplier.version,
            "form": form
        }
        supplier_data.append(data)

    return render_template(
        "core/suppliers.html",
        manual_form = manual_form,
        suppliers = supplier_data
    )

@bp.route("/payment-processors")
@admin_required
def payment_processors() -> str:
    return render_template("core/payment_processors.html")

@bp.route("/addons")
@admin_required
def addons() -> str:
    addons = models.Addon.query.all()
    for addon in addons:
        if addon.type == "STYLE":
            addons.remove(addon)
    return render_template("core/addons.html", addons=addons)

@bp.route("/addons/toggle/<addon_id>", methods=["POST"])
@admin_required
def set_addon_active(addon_id: str) -> Response:
    addon = models.Addon.query.get(addon_id)
    if not addon:
        abort(404)
    addon.active = not addon.active
    db.session.commit()
    flash(f"Addon {addon.name} set to {'Active' if addon.active else 'Inactive'}", "info")
    return redirect(url_for('admin.addons'))


@bp.route("/addons/upload", methods=["GET", "POST"])
@admin_required
def upload_addon() -> str | Response:
    form = forms.AddonUploadForm()
    
    if form.validate_on_submit():
        zip_path = None
        temp_dir = None
        
        try:
            # Determine upload type and get ZIP file
            if form.url.data:
                # Download from URL
                zip_path = processors.download_addon_from_url(form.url.data)
                upload_type = "url"
            elif form.zip_file.data:
                # Save uploaded file to temp
                temp_dir = pathlib.Path(tempfile.mkdtemp())
                zip_path = temp_dir / "addon.zip"
                form.zip_file.data.save(str(zip_path))
                upload_type = "file"
            else:
                flash("Please provide either a URL or upload a ZIP file", "error")
                return redirect(url_for('admin.index'))
            
            # Extract and validate
            temp_extract_dir = pathlib.Path(tempfile.mkdtemp())
            try:
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
                
                # Find addon directory
                addon_path = temp_extract_dir
                if not (addon_path / "__init__.py").exists():
                    subdirs = [d for d in addon_path.iterdir() if d.is_dir()]
                    if len(subdirs) == 1:
                        addon_path = subdirs[0]
                
                # Validate structure
                validation_result = processors.validate_addon_structure(addon_path)
                addon_data = validation_result['addon_data']
                default_list = validation_result['default_list']
                
                addon_name = addon_data['name']
                addon_type = addon_data['type']
                
                # Check if addon already exists
                existing_addon = models.Addon.query.filter_by(
                    name=addon_name,
                    type=addon_type
                ).first()
                
                if existing_addon:
                    # Check compatibility
                    is_compatible, incompatible_keys = processors.check_defaults_compatibility(
                        existing_addon.id,
                        default_list
                    )
                    
                    # Save ZIP to a more permanent temp location for confirmation
                    import shutil
                    confirmation_temp_dir = pathlib.Path(tempfile.mkdtemp())
                    confirmation_zip_path = confirmation_temp_dir / "addon.zip"
                    shutil.copy2(zip_path, confirmation_zip_path)
                    
                    # Store data in session for confirmation
                    flask_session['addon_upload_data'] = {
                        'zip_path': str(confirmation_zip_path),
                        'temp_dir': str(confirmation_temp_dir),
                        'upload_type': upload_type,
                        'addon_data': addon_data,
                        'default_list': default_list,
                        'existing_addon_id': existing_addon.id,
                        'is_compatible': is_compatible,
                        'incompatible_keys': incompatible_keys,
                        'existing_addon_name': existing_addon.name,
                        'existing_addon_version': existing_addon.version or 'N/A'
                    }
                    
                    # Cleanup original temp files (but keep confirmation copy)
                    if zip_path.exists():
                        zip_path.unlink()
                    if temp_dir and temp_dir.exists():
                        shutil.rmtree(temp_dir)
                    if temp_extract_dir.exists():
                        shutil.rmtree(temp_extract_dir)
                    
                    return redirect(url_for('admin.confirm_addon_upload'))
                else:
                    # New addon, install directly
                    processors.install_addon(zip_path, upload_type)
                    flash(f"Successfully installed addon '{addon_name}'", "success")
                    return redirect(url_for('admin.index'))
                    
            finally:
                # Cleanup temp extract dir
                if temp_extract_dir.exists():
                    import shutil
                    shutil.rmtree(temp_extract_dir)
                    
        except ValueError as e:
            flash(f"Addon validation error: {str(e)}", "error")
            log.error(f"Addon upload validation error: {e}")
        except Exception as e:
            flash(f"Error uploading addon: {str(e)}", "error")
            log.error(f"Addon upload error: {e}", exc_info=True)
        finally:
            # Cleanup temp files
            if zip_path and zip_path.exists():
                zip_path.unlink()
            if temp_dir and temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
    
    upload_form = forms.AddonUploadForm()
    return render_template("core/index.html", upload_form=upload_form)


@bp.route("/addons/upload/confirm", methods=["GET", "POST"])
@admin_required
def confirm_addon_upload() -> str | Response:
    # Get data from session
    upload_data = flask_session.get('addon_upload_data')
    if not upload_data:
        flash("Upload session expired. Please try uploading again.", "error")
        return redirect(url_for('admin.index'))
    
    form = forms.AddonConfirmForm()
    
    if form.validate_on_submit() and form.confirm.data:
        zip_path = pathlib.Path(upload_data['zip_path'])
        temp_dir = pathlib.Path(upload_data.get('temp_dir', ''))
        upload_type = upload_data['upload_type']
        existing_addon_id = upload_data['existing_addon_id']
        is_compatible = upload_data['is_compatible']
        incompatible_keys = upload_data['incompatible_keys']
        
        try:
            if not zip_path.exists():
                raise ValueError("Uploaded addon file no longer exists. Please upload again.")
            
            # Handle incompatible defaults
            if not is_compatible and incompatible_keys:
                processors.delete_incompatible_defaults(existing_addon_id, incompatible_keys)
            
            # Preserve compatible configs if compatible
            preserved_configs = None
            if is_compatible:
                existing_configs = models.ConfigData.query.filter_by(
                    addon_id=existing_addon_id
                ).all()
                compatible_keys = [config.key for config in existing_configs]
                preserved_configs = processors.preserve_compatible_configs(
                    existing_addon_id,
                    compatible_keys
                )
            
            # Install addon (replacing existing)
            processors.install_addon(
                zip_path,
                upload_type,
                replace_existing=True,
                existing_addon_id=existing_addon_id,
                preserved_configs=preserved_configs
            )
            
            # Cleanup temp files
            if temp_dir and temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
            
            # Cleanup session
            flask_session.pop('addon_upload_data', None)
            
            addon_name = upload_data['addon_data']['name']
            flash(f"Successfully replaced addon '{addon_name}'", "success")
            return redirect(url_for('admin.index'))
            
        except Exception as e:
            flash(f"Error replacing addon: {str(e)}", "error")
            log.error(f"Addon replacement error: {e}", exc_info=True)
            # Cleanup on error
            if temp_dir and temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
            flask_session.pop('addon_upload_data', None)
            return redirect(url_for('admin.index'))
    
    # GET request - show confirmation page
    existing_addon = models.Addon.query.get(upload_data['existing_addon_id'])
    if not existing_addon:
        flash("Existing addon not found", "error")
        flask_session.pop('addon_upload_data', None)
        return redirect(url_for('admin.index'))
    
    form.addon_data.data = json.dumps(upload_data)
    
    return render_template(
        "core/addon_confirm.html",
        form=form,
        existing_addon=existing_addon,
        new_addon_data=upload_data['addon_data'],
        is_compatible=upload_data['is_compatible'],
        incompatible_keys=upload_data['incompatible_keys']
    )

