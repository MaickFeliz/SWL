"""Pruebas de integración de rutas HTTP.

Cubre:
- GET /admin/reports/inventory/export retorna 302 si el usuario no está autenticado.
- GET /admin/reports/inventory/export retorna 200 si el usuario tiene rol 'admin'.
"""
from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_login import login_user

from app import db
from app.models import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_admin_user(unique_suffix: str = "A") -> User:
    """Crea y persiste un usuario con rol 'admin' para las pruebas de rutas."""
    user = User(
        document_id=f"ADMIN{unique_suffix}",
        full_name="Admin Test",
        role="admin",
        password_hash="hash_test",
        email=f"admin{unique_suffix}@test.local",
    )
    db.session.add(user)
    db.session.commit()
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInventoryExportRoute:
    """Valida el acceso al endpoint /admin/reports/inventory/export."""

    ENDPOINT = "/admin/reports/inventory/export"

    def test_unauthenticated_user_is_redirected(self, client: FlaskClient) -> None:
        """Un usuario no autenticado debe recibir HTTP 302 hacia el login.

        El decorador ``@role_required('admin')`` redirige a ``auth.login``
        cuando ``current_user.is_authenticated`` es ``False``.
        """
        response = client.get(self.ENDPOINT)
        assert response.status_code == 302, (
            f"Se esperaba 302, se obtuvo {response.status_code}"
        )
        location = response.headers.get("Location", "")
        assert "login" in location.lower() or location != self.ENDPOINT, (
            "La redirección debe apuntar hacia la vista de login"
        )

    def test_admin_user_receives_200(self, app_context: Flask) -> None:
        """Un usuario autenticado con rol 'admin' debe recibir HTTP 200 con el Excel.

        Usa un cliente con ``use_cookies=True`` e inyecta ``_user_id`` en la
        sesión de Flask-Login para simular autenticación sin pasar por el
        formulario de login.

        El fixture ``app_context`` garantiza que el usuario creado y el
        ``load_user`` de Flask-Login compartan la misma sesión de SQLAlchemy.
        """
        import uuid

        suffix = uuid.uuid4().hex[:8]
        admin_user = _create_admin_user(suffix)
        admin_id: int = admin_user.id

        test_client = app_context.test_client(use_cookies=True)

        with test_client.session_transaction() as sess:
            sess["_user_id"] = str(admin_id)
            sess["_fresh"] = True

        response = test_client.get(self.ENDPOINT)
        assert response.status_code == 200, (
            f"Se esperaba 200 para usuario admin, se obtuvo {response.status_code}"
        )
        content_type = response.content_type
        assert "spreadsheetml" in content_type or "octet-stream" in content_type, (
            f"Se esperaba un tipo MIME de Excel, se obtuvo: {content_type}"
        )
