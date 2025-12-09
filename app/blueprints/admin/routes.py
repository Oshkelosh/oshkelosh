from flask import (
    current_app,
    render_template,
    redirect,
    url_for,
    flash
)
import jinja2, os
from . import bp

from flask_login import current_user, login_required

from app.models import models
from app.utils.site_config import invalidate_config_cache

from . import forms

import json




@bp.route("/")
@login_required
def index():
    return render_template("core/index.html")

@bp.route("/settings", methods=["GET", "POST"])
@bp.route("/settings/<addon_id>", methods=["GET", "POST"])
@login_required
def settings(addon_id = None):
    setup = models.get_config(addon_id = addon_id)
    formClass = forms.dynamic_form(setup)
    form = formClass()
    addons = models.Addon.get()
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


        return redirect(url_for('admin.settings', addon_id=addon_id))

    return render_template(
        "core/settings.html",
        form = form,
        addons = addons
    )


@bp.route("/suppliers")
@login_required
def suppliers():
    return render_template("core/suppliers.html")

@bp.route("/payments")
@login_required
def payments():
    return render_template("core/payments.html")

