from flask import (
    current_app,
    render_template,
    send_from_directory,
    render_template_string,
    Response,
)
from . import bp
from app.database import models
import app.helpers as helpers
import json, os, random


@bp.route("/index")
@bp.route("/")
def index():
    data = models.Category.get()
    categories = [{entry.name: entry.id} for entry in data]
    data = models.Product.get()
    random.shuffle(data)
    products = [entry.data() for entry in data]

    return render_template(
        helpers.template_route("main/index.html"),
        site=helpers.site_data(),
        categories=categories,
        products=products,
    )


@bp.route("/about")
def about():
    return render_template(
        helpers.template_route("main/about.html"), site=helpers.site_data()
    )


@bp.route("/static/<path:filename>")
def static(filename):
    if filename == "style.css":
        css_path = os.path.join("app", helpers.static_route(), filename)
        with open(css_path, "r") as f:
            css_content = f.read()
        rendered = render_template_string(css_content, style=helpers.style_data())
        return Response(rendered, mimetype="text/css")
    return send_from_directory(helpers.static_route(), filename)
