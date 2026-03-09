from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Catalog, ItemInstance, Loan, LoanStatus, InventoryStatus

logger = logging.getLogger(__name__)


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
        """Crea un préstamo bajo una transacción atómica estricta.

        Secuencia obligatoria:
          1. Bloquear fila del ItemInstance con SELECT ... FOR UPDATE
             (evita condiciones de carrera ante solicitudes concurrentes).
          2. Validar disponibilidad del ítem (status == AVAILABLE).
          3. Validar reglas del usuario según categoría del ítem.
          4. Actualizar estado del ítem → LOANED.
          5. Crear registro Loan y añadirlo a la sesión.
          6. db.session.commit() — consolida todos los cambios atómicamente.

        Raises:
            ValueError: Si el ítem no existe, no está disponible o el usuario
                        viola alguna regla de negocio.
            SQLAlchemyError: Si ocurre un error a nivel de base de datos
                             (la sesión queda en rollback automático).
        """
        try:
            # ── 1. BLOQUEAR FILA ──────────────────────────────────────────────
            # with_for_update() emite SELECT ... FOR UPDATE en PostgreSQL,
            # garantizando exclusividad hasta el commit/rollback.
            instance: Optional[ItemInstance] = (
                db.session.query(ItemInstance)
                .filter(ItemInstance.id == instance_id)
                .with_for_update()
                .first()
            )

            if instance is None:
                raise ValueError(
                    f"El ítem con id={instance_id} no existe en el inventario."
                )

            # ── 2. VALIDAR DISPONIBILIDAD DEL ÍTEM ────────────────────────────
            if instance.status != InventoryStatus.AVAILABLE:
                raise ValueError(
                    f"El ítem '{instance.unique_code}' no está disponible "
                    f"(estado actual: {instance.status.value})."
                )

            # ── 3. VALIDAR REGLAS DEL USUARIO POR CATEGORÍA ───────────────────
            category = instance.catalog_item.category if instance.catalog_item else None

            if category == "computo":
                can_request, msg = LoanService.can_request_laptop(user_id)
                if not can_request:
                    raise ValueError(msg)
            elif category not in ("libro", "computo", None):
                # Accesorios / categorías generales
                can_request, msg = LoanService.can_request_accessory(user_id)
                if not can_request:
                    raise ValueError(msg)

            # ── 4. ACTUALIZAR ESTADO DEL ÍTEM ─────────────────────────────────
            instance.status = InventoryStatus.LOANED

            # ── 5. CREAR REGISTRO DE PRÉSTAMO ─────────────────────────────────
            loan_days = (
                days
                if days is not None
                else current_app.config.get("DEFAULT_LOAN_DAYS", 15)
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

            # ── 6. COMMIT ATÓMICO ─────────────────────────────────────────────
            db.session.commit()
            logger.info(
                "Préstamo creado — user_id=%s, instance_id=%s, due=%s",
                user_id,
                instance_id,
                due_date.isoformat(),
            )
            return new_loan

        except ValueError:
            db.session.rollback()
            raise

        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.error(
                "Error de base de datos al crear préstamo (user=%s, instance=%s): %s",
                user_id,
                instance_id,
                exc,
            )
            raise

    @staticmethod
    def approve_loan(loan_id: int) -> Tuple[bool, str]:
        loan = Loan.query.get(loan_id)
        if not loan or loan.status is not LoanStatus.PENDING:
            return False, "Préstamo no válido o ya procesado."

        loan.status = LoanStatus.ACTIVE
        loan.approval_date = datetime.now(timezone.utc)

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