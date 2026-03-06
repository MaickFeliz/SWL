import os
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


class Config:
    """Configuración base segura, pensada para producción por defecto."""

    basedir = os.path.abspath(os.path.dirname(__file__))

    DEBUG = False

    flask_env = os.getenv("FLASK_ENV", "production")
    SECRET_KEY = os.getenv("SECRET_KEY")
    if flask_env == "production" and not SECRET_KEY:
        raise ValueError(
            "SECRET_KEY debe estar definido en el entorno para ejecución en producción."
        )

    database_url = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'app.db')}"
    )
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    PENALTY_FEE_PER_DAY = float(os.getenv("PENALTY_FEE_PER_DAY", 5000.0))

    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in {"true", "1", "yes"}
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME or None)

    LOG_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "logs", "library.log"
    )

    APP_NAME = "SWL"
    LIBRARY_NAME = "SWL"

    USER_ROLES = {
        "admin": "Administrador del Sistema",
        "bibliotecario": "Bibliotecario / Staff",
        "premium": "Usuario Premium",
        "cliente": "Estudiante / Cliente Regular",
    }


class DevelopmentConfig(Config):
    """Configuración específica para desarrollo local con debugging habilitado."""

    DEBUG = True