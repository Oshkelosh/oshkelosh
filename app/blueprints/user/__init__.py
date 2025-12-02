from flask import Blueprint
from app.blueprints import register_blueprint

bp = Blueprint('user',__name__)

from . import routes

register_blueprint(bp, url_prefix='/user')
