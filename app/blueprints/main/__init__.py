from flask import Blueprint
from app.blueprints import register_blueprint

bp = Blueprint('main',__name__)

from . import routes

register_blueprint(bp)
