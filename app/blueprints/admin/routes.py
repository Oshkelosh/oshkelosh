from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    abort,
    Response
)
from . import bp
from app.utils import site_config

from flask_login import current_user, login_required

from functools import wraps
from typing import Callable, Any

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
    return render_template("core/index.html")


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

@bp.route('/products')
@admin_required
def products() -> str:
    products = get_previews()
    categories = models.Category.query.all()
    return render_template(
        "core/products.html",
        products = products,
        categories = categories
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
            if field.name in ["submit", "csrf_token"]:
                continue
            if getattr(product, field.name) != field.data:
                setattr(product, field.name, field.data)
                update = True
        if update:
            db.session.commit()
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
    addons = models.Addon.query.filter_by(type="SUPPLIER").all()
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
        suppliers = supplier_data
    )

@bp.route("/payment-processors")
@admin_required
def payment_processors() -> str:
    return render_template("core/payment_processors.html")

@bp.route("/addons")
@admin_required
def addons() -> str:
    return render_template("core/addons.html")

