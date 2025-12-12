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

from app.models import models
from app.utils.site_config import invalidate_config_cache

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
def products():
    return render_template(
        "core/products.html"
    )

@bp.route("/suppliers", methods=["GET", "POST"])
@admin_required
def suppliers():
    addons = models.Addon.get(type="SUPPLIER")
    supplier_configs = [models.Config(addon_id = addon.id) for addon in addons]
    form_instance = {}

    submitted_id = None

    for supplier in supplier_configs:
        formClass = forms.dynamic_form(supplier)
        form = formClass()
        forms.append(form)
        if form.validate_on_submit():
            update = False
            for field in form:
                if field.name in ["submit", "csrf_token"]:
                    continue
                if supplier[field.name] != field.data:
                    setattr(supplier, field.name, field.data)
                    update = True
            if update:
                supplier.update()
    return render_template(
        "core/suppliers.html",
        suppliers = forms
    )

@bp.route("/payment-processors")
@admin_required
def payment_processors():
    return render_template("core/payment_processors.html")

@bp.route("/addons")
@admin_required
def addons():
    return render_template("core/addons.html")

