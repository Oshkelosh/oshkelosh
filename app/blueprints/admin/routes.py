from flask import (
    current_app,
    render_template,
    redirect,
    url_for,
    flash,
    abort
)
import jinja2, os
from . import bp
from app.utils import site_config

from flask_login import current_user, login_required

from functools import wraps

from app.models import models, get_previews

from app.utils.site_config import invalidate_config_cache
import app.processor as processors

from . import forms

import json


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_view(*args, **kwargs):
        if current_user.role != 'ADMIN':
            abort(403)
        return f(*args, **kwargs)
    return decorated_view


@bp.route("/")
@admin_required
def index():
    return render_template("core/index.html")


@bp.route("/sync-suppliers", methods=["POST"])
@admin_required
def sync_suppliers():
    processors.sync_products()
    flash('Syncing Products')
    return redirect(url_for('admin.index'))


@bp.route("/settings", methods=["GET", "POST"])
@bp.route("/settings/<style_name>", methods=["GET", "POST"])
@admin_required
def settings(style_name = None):
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
def users():
    data = models.User.get()
    users = [user for user in data if user.role == 'CLIENT']
    admins = [user for user in data if user.role == 'ADMIN']
    return render_template(
        "core/users.html",
        users = users,
        admins = admins
    )

@bp.route('/set-user/<int:id>/<direction>', methods=["POST"])
@admin_required
def set_user_role(id, direction):
    users = models.User.get(id=id)
    if not users:
        abort(404, description="User not found")
    user = users[0]
    if user.role == 'CLIENT' and direction == 'ADD':
        user.role = 'ADMIN'
        user.update()
        flash(f"{user.name} is now an Admin", "success")
    elif user.role == 'ADMIN' and direction == 'REMOVE':
        user.role = 'CLIENT'
        user.update()
        flash(f"{user.name} as been removed as Admin", "success")
    else:
        flash("Invalid operation!", "danger")
    
    return redirect(url_for('admin.users'))

@bp.route('/products')
@admin_required
def products():
    products = get_previews()
    categories = models.Category.get()
    return render_template(
        "core/products.html",
        products = products,
        categories = categories
    )

@bp.route('/products/<product_id>', methods=["GET", "POST"])
@admin_required
def product(product_id):
    product = models.Product.get(id = product_id)
    if not product:
        abort(404)
    product = product[0]
    product_form = forms.create_product_form(product)
    images = models.Image.get(product_id = product_id)
    if product_form.validate_on_submit():
        update = False
        for field in product_form:
            if field.name in ["submit", "csrf_token"]:
                continue
            if getattr(product, field.name) != field.data:
                setattr(product,field.name, field.data)
                update = True
        if update:
            product.update()
        return redirect(url_for('admin.product', product_id=product_id))

    return render_template(
        'core/product.html',
        product = product_form,
        images = images,
    )

@bp.route('/images')
@admin_required
def images():
    images = models.Image.get()
    return render_template(
        'core/images.html',
        images=images
    )

@bp.route('/images/<image_id>', methods=["GET", "POST"])
@admin_required
def image(image_id):
    image = models.Image.get(id=image_id)
    if not image:
        abort(404)
    image = image[0]
    form = forms.create_image_form(image)
    if form.validate_on_submit():
        update = False
        for field in form:
            if field.name in ["submit", "csrf_token"]:
                continue
            if getattr(product, field.name) != field.data:
                setattr(product,field.name, field.data)
                update = True
        if update:
            image.update()
        return redirect(url_for('admin.image', image_id=image.id))

    return render_template(
        'core/image.html',
        image = image,
        form = form
    )

@bp.route('/images/remove/<image_id>', methods=["DELETE"])
@admin_required
def remove_image(image_id):
    image = models.Image.get(id=image_id)
    if not image:
        abort(404)
    image = image[0]
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
def suppliers():
    addons = models.Addon.get(type="SUPPLIER")
    supplier_data = []
    for supplier in addons:
        config = models.Config(addon_id = supplier.id)
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
                supplier.update()
                flash(f"{supplier.name.capitalize()} data updated")
                return redirect(url_for('admin.suppliers'))

        data = {
            "name": supplier.name.capitalize(),
            "description": supplier.description.capitalize(),
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
def payment_processors():
    return render_template("core/payment_processors.html")

@bp.route("/addons")
@admin_required
def addons():
    return render_template("core/addons.html")

