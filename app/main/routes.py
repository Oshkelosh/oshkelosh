from flask import current_app, render_template, send_from_directory
from . import bp
from app.database import models
import app.helpers as helpers
import json, os


@bp.route('/index')
@bp.route('/')
def index():
    return render_template(helpers.template_route('main/index.html'), site=helpers.site_data() ,style=helpers.style_data())

@bp.route('/static/<path:filename>')
def static(filename):
    return send_from_directory(helpers.static_route(), filename)
