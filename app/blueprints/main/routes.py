from flask import (
    current_app,
    render_template,
    send_from_directory,
    Response,
)
from . import bp
from app.models import models, get_previews

from app.utils import site_config
import random
from pathlib import Path

@bp.route("/index")
@bp.route("/")
def index() -> str:
    products = get_previews("ACTIVE")
    return render_template(
        "main/index.html",
        site = site_config.get_config("site_config"),
        products = products,
    )


@bp.route("/about")
def about() -> str:
    return render_template(
        "main/about.html",
        site = site_config.get_config("site_config")
    )

@bp.route("/category/<category_id>")
def category(category_id: str) -> str:
    category = models.Category.query.get(category_id)
    if not category:
        from flask import abort
        abort(404)
    products = category.products.all()
    random.shuffle(products)
    categories = models.Category.query.all()
    return render_template(
        "main/category.html",
        site = site_config.get_config("site_config"),
        category = category,
        products = products,
        categories = categories,
    )

@bp.route('/product/<product_id>')
def product(product_id: str) -> str:
    product = models.Product.query.get(product_id)
    if not product:
        from flask import abort
        abort(404)
    images = models.Image.query.filter_by(product_id=product.id).order_by(models.Image.position).all()
    return render_template(
        "main/product.html",
        site = site_config.get_config("site_config"),
        product = product,
        images = images
    )

@bp.route('/image/<filename>')
def serve_image(filename: str) -> Response:
    image_dir = Path(current_app.instance_path) / 'images'
    return send_from_directory(image_dir, filename)
