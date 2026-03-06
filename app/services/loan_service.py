from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from flask import current_app

from app import db
from app.models import Catalog, ItemInstance, Loan, LoanStatus, InventoryStatus


class LoanService:
    """Orquesta las reglas de negocio de préstamos desacopladas de las rutas."""

    @staticmethod
    def can_request_laptop(user_id: int) -> Tuple[bool, str]:
        active_loans = Loan.query.join(ItemInstance).join(Catalog).filter(
            Loan.user_id == user_id,
            Loan.status.in_(
                [LoanStatus.PENDING, LoanStatus.ACTIVE, LoanStatus.OVERDUE]
            ),
            Catalog.category == "computo",
        ).count()
        if active_loans > 0:
            return False, "Ya tienes un equipo pendiente, en uso o atrasado."
        return True, "Ok"

    @staticmethod
    def can_request_accessory(user_id: int) -> Tuple[bool, str]:
        active_accessories = Loan.query.join(ItemInstance).join(Catalog).filter(
            Loan.user_id == user_id,
            Catalog.category != "computo",
            Catalog.category != "libro",
            Loan.status.in_(
                [LoanStatus.PENDING, LoanStatus.ACTIVE, LoanStatus.OVERDUE]
            ),
        ).count()
        if active_accessories >= 2:
            return False, "Has alcanzado el límite de 2 accesorios simultáneos."
        return True, "Ok"

    @staticmethod
    def create_loan(
        user_id: int,
        instance_id: int,
        environment: Optional[str] = None,
        days: Optional[int] = None,
    ) -> Loan:
        loan_days = (
            days if days is not None else current_app.config.get("DEFAULT_LOAN_DAYS", 15)
        )
        due_date = datetime.now(timezone.utc) + timedelta(days=loan_days)

        new_loan = Loan(
            user_id=user_id,
            instance_id=instance_id,
            environment=environment,
            status=LoanStatus.PENDING,
            due_date=due_date,
        )
        db.session.add(new_loan)
        # El controlador (routes.py) se encarga de confirmar la transacción completa.
        return new_loan

    @staticmethod
    def approve_loan(loan_id: int) -> Tuple[bool, str]:
        loan = Loan.query.get(loan_id)
        if not loan or loan.status is not LoanStatus.PENDING:
            return False, "Préstamo no válido o ya procesado."

        loan.status = LoanStatus.ACTIVE
        loan.approval_date = datetime.now(timezone.utc)

        # El estado de la instancia física ya se puso en 'prestado'
        # en el InventoryService al momento de hacer la solicitud.
        db.session.commit()
        return True, "Préstamo aprobado con éxito."

    @staticmethod
    def return_loan(loan_id: int) -> Tuple[bool, str]:
        loan = Loan.query.get(loan_id)
        if not loan or loan.status not in (LoanStatus.ACTIVE, LoanStatus.OVERDUE):
            return False, "Préstamo no válido o no está activo."

        if loan.is_overdue:
            loan.final_penalty = loan.penalty_fee

        loan.status = LoanStatus.RETURNED
        loan.return_date = datetime.now(timezone.utc)

        if loan.item_instance:
            loan.item_instance.status = InventoryStatus.AVAILABLE

        db.session.commit()
        return True, "Artículo devuelto exitosamente al inventario."

    @staticmethod
    def check_overdue_loans() -> int:
        """Marca préstamos vencidos como atrasados sin bloquear controladores."""
        overdue_loans = Loan.query.filter(
            Loan.status == LoanStatus.ACTIVE,
            Loan.due_date < datetime.now(timezone.utc),
        ).all()

        count = 0
        for loan in overdue_loans:
            loan.status = LoanStatus.OVERDUE
            count += 1

        if count > 0:
            db.session.commit()

        return count