from flask import Flask, session
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from logging.handlers import RotatingFileHandler
import logging
import os

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

login_manager.login_view = "auth.login"
login_manager.login_message = "Por favor, inicie sesión para acceder al sistema."


def create_app(config_class: type[Config] = Config) -> Flask:
    """Crea y configura la aplicación Flask siguiendo el patrón factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    os.makedirs("logs", exist_ok=True)

    file_handler = RotatingFileHandler(
        app.config["LOG_FILE"], maxBytes=1024000, backupCount=3
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("LMS Startup - Technical Specs Initialized")

    @app.before_request
    def make_session_permanent() -> None:
        session.permanent = True

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app import cli as app_cli
    app_cli.register_commands(app)

    return app
