from flask import Flask
from flask_login import LoginManager

import jinja2
import redis

import os
from flask_config import flask_configs
from dotenv import dotenv_values
import json

from .database import migrations, schema, models



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

    print(f"Strating Oshkelosh Flask {env_config['FLASK_ENV']} server for {__name__}\n")
    return app
