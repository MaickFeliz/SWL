"""Comandos CLI de Flask para tareas programadas desacopladas del servidor web.

Desacoplamiento intencional
---------------------------
APScheduler fue eliminado del proceso web para evitar condiciones de carrera
e hilos duplicados bajo Gunicorn (multiple workers). En su lugar, las tareas
periódicas se ejecutan como procesos externos mediante el sistema Cron del PaaS.

Despliegue en producción (Railway / Render / Heroku)
----------------------------------------------------
Añadir una tarea Cron en el dashboard del PaaS con el comando::

    flask check-overdue

Ejemplo de expresión cron para ejecución diaria a las 00:01 (hora CO UTC-5)::

    1 5 * * *   flask check-overdue

El comando hereda el contexto de la aplicación completa (DB, configuración,
mail) gracias a ``@with_appcontext``, por lo que no requiere ningún ajuste
adicional en la configuración.
"""
from __future__ import annotations

import click
from datetime import datetime, timezone
from flask import Flask


def register_commands(app: Flask) -> None:
    """Registra todos los comandos CLI personalizados en la instancia de Flask."""

    @app.cli.command("check-overdue")
    def check_overdue() -> None:
        """Revisa préstamos vencidos, actualiza su estado y envía notificaciones.

        Uso en producción (Cron del PaaS)
        ----------------------------------
        Ejecutar una vez al día::

            flask check-overdue

        El comando marca como OVERDUE los préstamos en estado ACTIVE cuya
        ``due_date`` ya haya pasado, y posteriormente envía un correo de
        advertencia a cada usuario moroso mediante EmailService.

        No debe ejecutarse dentro del proceso Gunicorn; hacerlo en un worker
        independiente garantiza que corra una única vez y no consuma memoria
        de los workers HTTP.
        """
        from flask import current_app
        from app.models import Loan, LoanStatus
        from app.services.loan_service import LoanService
        from app.services.email_service import EmailService

        updated: int = LoanService.check_overdue_loans()
        current_app.logger.info(
            "check-overdue: préstamos actualizados a OVERDUE: %d", updated
        )

        overdue_loans = Loan.query.filter(
            Loan.status == LoanStatus.OVERDUE
        ).all()

        for loan in overdue_loans:
            try:
                if not loan.requester or not loan.due_date:
                    continue

                days_late: int = max(
                    0,
                    (
                        datetime.now(timezone.utc)
                        - (
                            loan.due_date
                            if loan.due_date.tzinfo
                            else loan.due_date.replace(tzinfo=timezone.utc)
                        )
                    ).days,
                )
                fee_per_day: float = current_app.config.get("PENALTY_FEE_PER_DAY", 5000.0)
                penalty: float = loan.penalty_fee(fee_per_day=fee_per_day)

                EmailService.send_overdue_warning(
                    user=loan.requester,
                    loan=loan,
                    days_overdue=days_late,
                    penalty=penalty,
                    app=current_app._get_current_object(),  # type: ignore[attr-defined]
                )
            except Exception as exc:  # noqa: BLE001
                current_app.logger.exception(
                    "check-overdue: error al notificar préstamo %d: %s",
                    loan.id,
                    exc,
                )

        click.echo(
            f"check-overdue completado. Nuevos atrasos: {updated}. "
            f"Notificaciones intentadas: {len(overdue_loans)}."
        )
