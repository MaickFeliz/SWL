from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Catalog, ItemInstance, Loan, LoanStatus, InventoryStatus

logger = logging.getLogger(__name__)


class LoanService:
    """Orquesta las reglas de negocio de préstamos desacopladas de las rutas."""

    @staticmethod
    def authorize_fast_loan(target_user_id: int, current_user_id: int, current_user_role: str) -> Tuple[bool, str]:
        """Valida si el usuario puede realizar un préstamo rápido en nombre del target.

        Args:
            target_user_id:    ID del usuario destino del préstamo.
            current_user_id:   ID del usuario autenticado que realiza la operación.
            current_user_role: Rol del usuario autenticado.

        Returns:
            (True, "Ok") si la operación está autorizada.
            (False, mensaje) si no lo está.
        """
        if current_user_role in ("admin", "bibliotecario"):
            return True, "Ok"
        if target_user_id != current_user_id:
            return False, "Operación no autorizada."
        return True, "Ok"

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
        catalog_id: int,
        quantity: int = 1,
        environment: Optional[str] = None,
        days: Optional[int] = None,
    ) -> List[Loan]:
        """Crea uno o varios préstamos bajo una única transacción atómica.

        Secuencia obligatoria:
          1. Validar reglas de negocio del usuario antes de tocar el inventario.
          2. Bloquear filas con SELECT ... FOR UPDATE SKIP LOCKED.
             SKIP LOCKED descarta ítems ya bloqueados por transacciones
             concurrentes en lugar de hacerlas esperar — ideal para alta
             concurrencia (varios usuarios solicitando el mismo catálogo).
          3. Verificar que hay stock suficiente (len >= quantity).
          4. Actualizar estado de cada ítem → LOANED.
          5. Crear los registros Loan en bloque dentro de la misma sesión.
          6. db.session.commit() — consolida todos los cambios atómicamente.

        Args:
            user_id:     ID del usuario solicitante.
            catalog_id:  ID del catálogo del que se solicitan instancias.
            quantity:    Número de instancias a prestar (default=1).
            environment: Sala/ambiente opcional (para equipos de cómputo).
            days:        Días de préstamo (default: DEFAULT_LOAN_DAYS).

        Returns:
            Lista de objetos Loan creados.

        Raises:
            ValueError: Regla de negocio violada o stock insuficiente.
            SQLAlchemyError: Error de base de datos (sesión en rollback).
        """
        try:
            # ── 0. OBTENER CATEGORÍA DEL CATÁLOGO ─────────────────────────────
            catalog = db.session.get(Catalog, catalog_id)
            if not catalog:
                raise ValueError(f"Catálogo con id={catalog_id} no encontrado.")

            category = catalog.category

            # ── 1. VALIDAR REGLAS DEL USUARIO ANTES DE TOCAR INVENTARIO ────────
            if category == "computo":
                can_request, msg = LoanService.can_request_laptop(user_id)
                if not can_request:
                    raise ValueError(msg)
            elif category not in ("libro", "computo"):
                can_request, msg = LoanService.can_request_accessory(user_id)
                if not can_request:
                    raise ValueError(msg)

            # ── 2. BLOQUEAR FILAS CON SKIP LOCKED ─────────────────────────────
            # skip_locked=True evita que la transacción espere por ítems ya
            # bloqueados por otra sesión concurrente; selecciona el siguiente
            # disponible de inmediato, eliminando cuellos de botella.
            instances: List[ItemInstance] = (
                db.session.query(ItemInstance)
                .filter(
                    ItemInstance.catalog_id == catalog_id,
                    ItemInstance.status == InventoryStatus.AVAILABLE,
                )
                .with_for_update(skip_locked=True)
                .limit(quantity)
                .all()
            )

            # ── 3. VERIFICAR STOCK SUFICIENTE ──────────────────────────────────
            if len(instances) < quantity:
                db.session.rollback()
                raise ValueError(
                    f"Stock insuficiente. Solicitados: {quantity}, "
                    f"disponibles (sin bloqueo): {len(instances)}."
                )

            # ── 4 & 5. ACTUALIZAR ESTADO + CREAR REGISTROS DE PRÉSTAMO ─────────
            loan_days = (
                days
                if days is not None
                else current_app.config.get("DEFAULT_LOAN_DAYS", 15)
            )
            due_date = datetime.now(timezone.utc) + timedelta(days=loan_days)

            created_loans: List[Loan] = []
            for instance in instances:
                instance.status = InventoryStatus.LOANED
                new_loan = Loan(
                    user_id=user_id,
                    instance_id=instance.id,
                    environment=environment,
                    status=LoanStatus.PENDING,
                    due_date=due_date,
                )
                db.session.add(new_loan)
                created_loans.append(new_loan)

            # ── 6. COMMIT ATÓMICO ─────────────────────────────────────────────
            db.session.commit()
            logger.info(
                "Préstamo(s) creado(s) — user_id=%s, catalog_id=%s, qty=%s, due=%s",
                user_id,
                catalog_id,
                quantity,
                due_date.isoformat(),
            )
            return created_loans

        except ValueError:
            db.session.rollback()
            raise

        except SQLAlchemyError as exc:
            db.session.rollback()
            logger.error(
                "Error de BD al crear préstamo (user=%s, catalog=%s, qty=%s): %s",
                user_id,
                catalog_id,
                quantity,
                exc,
            )
            raise

    @staticmethod
    def approve_loan(loan_id: int) -> Tuple[bool, str]:
        loan = db.session.get(Loan, loan_id)
        if not loan or loan.status is not LoanStatus.PENDING:
            return False, "Préstamo no válido o ya procesado."

        loan.status = LoanStatus.ACTIVE
        loan.approval_date = datetime.now(timezone.utc)

        db.session.commit()
        return True, "Préstamo aprobado con éxito."

    @staticmethod
    def return_loan(loan_id: int) -> Tuple[bool, str]:
        loan = db.session.get(Loan, loan_id)
        if not loan or loan.status not in (LoanStatus.ACTIVE, LoanStatus.OVERDUE):
            return False, "Préstamo no válido o no está activo."

        if loan.is_overdue:
            fee_per_day = current_app.config.get("PENALTY_FEE_PER_DAY", 5000.0)
            loan.final_penalty = loan.penalty_fee(fee_per_day=fee_per_day)

        loan.status = LoanStatus.RETURNED
        loan.return_date = datetime.now(timezone.utc)

        if loan.item_instance:
            loan.item_instance.status = InventoryStatus.AVAILABLE

        db.session.commit()
        return True, "Artículo devuelto exitosamente al inventario."

    @staticmethod
    def check_overdue_loans() -> int:
        """Marca préstamos vencidos como atrasados y notifica por correo."""
        from app.services.email_service import EmailService

        # Buscar todos los activos vencidos, o los que ya están vencidos para re-notificar
        # (Dependiendo de la regla de negocio, aquí notificamos al pasar a OVERDUE)
        overdue_loans = Loan.query.filter(
            Loan.status == LoanStatus.ACTIVE,
            Loan.due_date < datetime.now(timezone.utc),
        ).all()

        fee_per_day: float = current_app.config.get("PENALTY_FEE_PER_DAY", 5000.0)
        count = 0
        for loan in overdue_loans:
            loan.status = LoanStatus.OVERDUE
            # Calcular días y multa para el correo
            due = (
                loan.due_date
                if loan.due_date.tzinfo
                else loan.due_date.replace(tzinfo=timezone.utc)
            )
            days_late = (datetime.now(timezone.utc) - due).days
            penalty = loan.penalty_fee(fee_per_day=fee_per_day)

            # Enviar correo asíncrono
            EmailService.send_overdue_warning(
                user=loan.requester,
                loan=loan,
                days_overdue=days_late,
                penalty=penalty,
                app=current_app._get_current_object()  # Pasar app real, no proxy
            )
            count += 1

        if count > 0:
            db.session.commit()
            logger.info("Revisión automática: %d préstamos pasaron a estado atrasado.", count)

        return count