import os
import json
from flask import Flask, redirect, url_for, flash
from dotenv import load_dotenv

from .config import config_by_name
from .themes import get_active_theme_loader, get_active_theme_static
from .models import models  
from .blueprints import init_blueprints
from .error_handlers import register_error_handlers

load_dotenv()  


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory.
    Keeps startup side-effects isolated and testable.
    """
    config_name = config_name or os.getenv("FLASK_ENV", "default")
    app = Flask(
        __name__,
        instance_relative_config=True,
        # We will set static/template folders dynamically per-theme
        static_folder=None,
        template_folder=None,
    )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    app.config.from_object(config_by_name[config_name])
    config_by_name[config_name].init_app(app)
    app.config.from_envvar("OSHKELOSH_SETTINGS", silent=True)  # optional overrides

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    from utils.logging import setup_logging
    setup_logging(app)

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    from .utils.extensions import db, login_manager, redis_client
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "user.login"
    login_manager.login_message_category = "warning"

    redis_client.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: int):
        return models.User.get(id=user_id)

    # ------------------------------------------------------------------
    # Theme / Template / Static resolution (your modular style system)
    # ------------------------------------------------------------------
    theme_loader = get_active_theme_loader(app)
    theme_static_folder, theme_static_url = get_active_theme_static(app)

    app.jinja_loader = theme_loader
    app.static_folder = theme_static_folder
    app.static_url_path = theme_static_url

    # ------------------------------------------------------------------
    # Database & defaults (idempotent – safe to run on every startup)
    # ------------------------------------------------------------------
    with app.app_context():
        from app.database import default
        db.set_default(default_list = default.default_list)

        # Cache site config in Redis for fast non-DB reads
        from .utils.site_config import cache_config
        cache_config()

    # ------------------------------------------------------------------
    # Blueprints & error handlers
    # ------------------------------------------------------------------
    init_blueprints(app)
    register_error_handlers(app)

    app.logger.info("Oshkelosh %s server ready (theme: %s)", config_name, app.config.get("ACTIVE_THEME"))

    return app


'''
from flask import Flask, redirect, url_for, flash
from flask_login import LoginManager

import jinja2
import redis

import os
from flask_config import flask_configs
from dotenv import dotenv_values
import json

from .database import migrations, schema, models
import exceptions





def create_app():
    env_config = dotenv_values(".env")
    if "FLASK_ENV" not in env_config:
        print(
            "Please set FLASK_ENV in the .env file. Possible environments: 'development', 'production', 'testing', 'default'"
        )
        return False

    app = Flask(__name__, static_folder=None, static_url_path=None)
    app.config.from_object(flask_configs[env_config["FLASK_ENV"]])
    flask_configs[env_config["FLASK_ENV"]].init_app(env_config["APP_SECRET"])

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'user.login'

    @login_manager.user_loader
    def load_user(user_id: int):
        users = models.User.get(id = user_id)
        return users[0] if users else None

    print("Setting up Redis")
    app.redis = redis.Redis(host="localhost", port=6379, db=0)

    print("Setting up DB")
    migrations.setupDB(schema=schema.schema, db_path=schema.db_path)
    from .admin import default

    print("Setting Defaults")
    success = models.set_defaults(default_list=default.default_list)
    if not success:
        return False

    print("Setting up Oshkelosh Configs")
    oshkelosh = models.set_configs()
    for key, config in oshkelosh.items():
        app.redis.set(key, json.dumps(config.data()))

    # login.init_app(app)

    print("Loading Blueprints")
    from app.main import bp as main_bp

    app.register_blueprint(main_bp, url_prefix="")

    from app.admin import bp as admin_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.user import bp as user_bp

    app.register_blueprint(user_bp, url_prefix="/user")


    print("Loading Jinja2 ChoiseLoader")
    addons_path = os.path.join(app.root_path, "addons", "style")
    admin_bp = app.blueprints['admin']
    admin_path = os.path.join(admin_bp.root_path, admin_bp.template_folder or 'templates')
    print(admin_path)
    oshkelosh_loader = jinja2.ChoiceLoader([
        jinja2.FileSystemLoader(addons_path),
        jinja2.FileSystemLoader(admin_path)
    ])
    app.jinja_loader = oshkelosh_loader

    print("Registering error handlers")
    @app.errorhandler(exceptions.AuthorizationError)
    def handle_auth_error(error):
        admins = models.User.get(role="ADMIN")
        for admin in admins:
            continue    #Create new messages
        flash("An un-authorized action has occured, and you have been logged out.", "WARNING")
        return redirect(url_for('user.logout'))

    print(f"Strating Oshkelosh Flask {env_config['FLASK_ENV']} server for {__name__}\n")
    return app
    '''
