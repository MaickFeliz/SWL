"""Fixtures de Pytest compartidos por toda la suite de pruebas.

La aplicación se crea con una base de datos en memoria (SQLite) para que
cada sesión de pruebas parta de un estado limpio y sin efectos secundarios
sobre la base de datos de desarrollo.
"""
from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, db as _db


class TestingConfig:
    """Configuración mínima y segura exclusiva para el entorno de pruebas."""

    TESTING: bool = True
    DEBUG: bool = False
    SECRET_KEY: str = "test-secret-key-insecure"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    WTF_CSRF_ENABLED: bool = False
    LOGIN_DISABLED: bool = False
    MAIL_SUPPRESS_SEND: bool = True
    MAIL_SERVER: str = ""
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_DEFAULT_SENDER: str = "noreply@test.local"
    LOG_FILE: str = "logs/library.log"
    PENALTY_FEE_PER_DAY: float = 5000.0
    DEFAULT_LOAN_DAYS: int = 15


@pytest.fixture(scope="session")
def app() -> Flask:
    """Crea una instancia de Flask configurada para pruebas (scope=session).

    Usa ``sqlite:///:memory:`` para aislar completamente el estado de la DB.
    """
    flask_app = create_app(config_class=TestingConfig)  # type: ignore[arg-type]

    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Cliente HTTP de pruebas que no mantiene cookies entre peticiones."""
    return app.test_client()


@pytest.fixture()
def app_context(app: Flask):
    """Activa el contexto de aplicación para pruebas que acceden directamente a la DB."""
    with app.app_context():
        yield app
