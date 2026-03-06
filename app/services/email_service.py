from __future__ import annotations

import smtplib
import threading
from typing import Any

from flask import current_app
from flask_mail import Message

from app import mail
from app.models import Loan, User


class EmailService:
    """Encapsula el envío de correos para permitir ejecución asíncrona y trazable.

    El uso de hilos secundarios requiere reenviar el contexto de aplicación,
    por lo que este servicio recibe explícitamente la instancia de Flask.
    """

    @staticmethod
    def send_async_email(app: Any, msg: Message) -> None:
        """Envía un correo en un hilo aparte usando el contexto de la app."""

        def _send() -> None:
            try:
                with app.app_context():
                    mail.send(msg)
            except (smtplib.SMTPException, ConnectionRefusedError) as exc:
                app.logger.error("Error SMTP al enviar correo: %s", exc)
            except Exception as exc:  # noqa: BLE001
                app.logger.exception("Error inesperado al enviar correo: %s", exc)

        thread = threading.Thread(target=_send, daemon=True)
        thread.start()

    @staticmethod
    def send_overdue_warning(
        user: User,
        loan: Loan,
        days_overdue: int,
        penalty: float,
        app: Any,
    ) -> None:
        """Construye y dispara un aviso de mora para un préstamo atrasado."""
        if not user.email:
            current_app.logger.info(
                "Usuario %s sin correo electrónico. Se omite notificación de mora.",
                user.id,
            )
            return

        item_name = (
            loan.item_instance.catalog_item.title_or_name
            if loan.item_instance and loan.item_instance.catalog_item
            else "ítem en préstamo"
        )

        subject = f"Aviso de mora en préstamo de {item_name}"
        body = (
            f"Hola {user.full_name},\n\n"
            f"Tu préstamo del ítem '{item_name}' presenta una mora de {days_overdue} día(s). "
            f"La multa estimada actual es de {penalty:.2f}.\n\n"
            "Por favor acércate a la biblioteca para regularizar tu situación.\n\n"
            "Este es un mensaje automático, por favor no responder."
        )

        msg = Message(
            subject=subject,
            recipients=[user.email],
            body=body,
        )

        EmailService.send_async_email(app=app, msg=msg)

