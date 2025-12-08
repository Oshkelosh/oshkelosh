from pathlib import Path
from flask import Blueprint
from app.blueprints import register_blueprint

bp = Blueprint(
        'admin',
        __name__,
        template_folder = 'templates',
        static_folder =  'static'
)

from . import routes

register_blueprint(bp, url_prefix='/admin')
