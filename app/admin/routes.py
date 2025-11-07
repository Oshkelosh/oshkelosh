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

@bp.route("/category/<category_id>")
def category(category_id):
    category = models.Category.get(category_id=category_id)
    category = category[0].data()
    products = category.products()
    products = [entry.data() for entry in products]
    random.shuffel(products)
    categories = models.Category.get()
    categories = [entry.data() for entry in categories]
    return render_template(
        helpers.template_route('main/category.html'),
        site = helpers.site_data(),
        category = category,
        products = products,
        categories = categories
    )

@bp.route('product/<product_id>')
def product(id):
    product = models.Product.get(id=id)
    product = product[0].data()
    categories = models.Category.get()
    categories = [entry.data() for entry in categories]
    return render_template(
        helpers.template_route('main/product.html'),
        site = helpers.site_data(),
        product = product,
        categories = categories
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
