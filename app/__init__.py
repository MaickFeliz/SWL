from flask import Flask, session
from flask_apscheduler import APScheduler
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
scheduler = APScheduler()
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

    # <-- INICIO DE CONFIGURACIÓN DEL SCHEDULER -->
    scheduler.init_app(app)

    from app.services.loan_service import LoanService
    from app.services.email_service import EmailService

    @scheduler.task("cron", id="actualizar_moras", hour=0, minute=1)
    def tarea_actualizar_moras() -> None:
        """Tarea diaria que actualiza moras y dispara notificaciones por correo."""
        with app.app_context():
            from app.models import Loan, LoanStatus  # import local para evitar ciclos

            now_updated = LoanService.check_overdue_loans()
            app.logger.info(
                "Revisión de préstamos atrasados ejecutada. Nuevos atrasos: %s",
                now_updated,
            )

            overdue_loans = Loan.query.filter(Loan.status == LoanStatus.OVERDUE).all()
            for loan in overdue_loans:
                try:
                    if not loan.requester or not loan.due_date:
                        continue

                    days_late = max(
                        0,
                        (datetime.now(timezone.utc) - loan.due_date).days
                        if loan.due_date
                        else 0,
                    )
                    penalty = loan.penalty_fee

                    EmailService.send_overdue_warning(
                        user=loan.requester,
                        loan=loan,
                        days_overdue=days_late,
                        penalty=penalty,
                        app=app,
                    )
                except Exception as exc:  # noqa: BLE001
                    app.logger.exception(
                        "Error al enviar notificación de mora para el préstamo %s: %s",
                        loan.id,
                        exc,
                    )

    scheduler.start()
    # <-- FIN DE CONFIGURACIÓN DEL SCHEDULER -->

    if not os.path.exists("logs"):
        os.mkdir("logs")

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
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app