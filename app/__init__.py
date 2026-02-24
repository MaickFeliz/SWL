from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import session

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Por favor, inicie sesión para acceder al sistema."

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Configuración del Directorio de Logs
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Handler del log: Archivo máximo 1MB, con backup hasta 3 versiones
    file_handler = RotatingFileHandler(app.config['LOG_FILE'], maxBytes=1024000, backupCount=3)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('LMS Startup - Technical Specs Initialized')

    # Hacer las sesiones persistentes respecto al TIEMPO de expiración
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    # Registrar Blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app