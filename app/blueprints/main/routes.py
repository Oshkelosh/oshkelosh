from flask import (
    current_app,
    render_template,
    send_from_directory,
    render_template_string,
    Response,
)
from . import bp
from app.models import models
from app.utils import site_config
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
        "main/index.html",
        site = site_config.get_config("site_config"),
        categories = categories,
        products = products,
    )


@bp.route("/about")
def about():
    return render_template(
        "main/about.html",
        site = site_config.get_config("site_config")
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
        "main/category.html",
        site = site_config.get_config("site_config"),
        category = category,
        products = products,
    )

@bp.route('/product/<product_id>')
def product(id):
    product = models.Product.get(id=id)
    product = product[0].data()
    categories = models.Category.get()
    categories = [entry.data() for entry in categories]
    return render_template(
        "main/product.html",
        site = site_config.get_config("site_config"),
        product = product,
    )


