from flask import (
    current_app,
    render_template,
    send_from_directory,
    render_template_string,
    Response,
)
from . import bp
from app.models import models, get_previews

from app.utils import site_config
import json, os, random
from pathlib import Path
import inspect

@bp.route("/index")
@bp.route("/")
def index():
    products = get_previews("ACTIVE")
    return render_template(
        "main/index.html",
        site = site_config.get_config("site_config"),
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
def product(product_id):
    product = models.Product.get(id=product_id)
    product = product[0]
    images = models.Image.get(product_id = product.id)
    images = sorted(images, key=lambda d: d.positon) 
    return render_template(
        "main/product.html",
        site = site_config.get_config("site_config"),
        product = product,
        images = images
    )

@bp.route('/image/<filename>')
def serve_image(filename):
    image_dir =Path(current_app.instance_path) / 'images'
    return send_from_directory(image_dir, filename)
