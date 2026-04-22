from __future__ import annotations
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo
from flask import current_app
from flask_login import UserMixin
from sqlalchemy import Numeric
from app import db, login_manager


class InventoryStatus(Enum):
    """Enum de estados de inventario para garantizar integridad referencial."""

    AVAILABLE = "disponible"
    LOANED = "prestado"
    MAINTENANCE = "mantenimiento"
    LOST = "perdido"


class LoanStatus(Enum):
    """Enum de estados de préstamo para evitar inconsistencias de negocio."""

    PENDING = "pendiente"
    ACTIVE = "activo"
    OVERDUE = "atrasado"
    RETURNED = "devuelto"
    REJECTED = "rechazado"


@login_manager.user_loader
def load_user(user_id: str) -> Optional["User"]:
    """Resuelve el usuario actual para sesiones de login."""
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    """Entidad principal de usuarios del sistema de préstamos."""

    id: int = db.Column(db.Integer, primary_key=True)
    email: Optional[str] = db.Column(db.String(120), unique=True, nullable=True)
    document_id: str = db.Column(db.String(20), unique=True, nullable=False)
    full_name: str = db.Column(db.String(100), nullable=False)
    phone: Optional[str] = db.Column(db.String(20))
    role: str = db.Column(db.String(20), nullable=False)
    program_name: Optional[str] = db.Column(db.String(100), nullable=True)
    password_hash: str = db.Column(db.String(255))

    def set_password(self, password: str) -> None:
        """Centraliza el hashing de contraseñas para facilitar futuros cambios."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Permite intercambiar el backend de hashing sin tocar los controladores."""
        return check_password_hash(self.password_hash, password)


class Catalog(db.Model):
    """Catálogo lógico de ítems disponibles para préstamo."""

    id: int = db.Column(db.Integer, primary_key=True)
    title_or_name: str = db.Column(db.String(150), nullable=False)
    category: str = db.Column(db.String(50), nullable=False)
    author_or_brand: Optional[str] = db.Column(db.String(100), nullable=True)
    is_penalty_applicable: bool = db.Column(db.Boolean, default=False)
    
    available_count: int = 0 

    instances = db.relationship(
            "ItemInstance",
        backref="catalog_item",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

class ItemInstance(db.Model):
    """Instancia física de un ítem del catálogo."""

    id: int = db.Column(db.Integer, primary_key=True)
    catalog_id: int = db.Column(
        db.Integer, db.ForeignKey("catalog.id"), nullable=False, index=True
    )
    unique_code: str = db.Column(db.String(50), unique=True, nullable=False)
    status: InventoryStatus = db.Column(
        db.Enum(
            InventoryStatus,
            name="inventory_status_enum",
            create_constraint=True,
        ),
        default=InventoryStatus.AVAILABLE,
        nullable=False,
        index=True,
    )
    condition: Optional[str] = db.Column(db.String(100), nullable=True)

    loans = db.relationship("Loan", backref="item_instance", lazy="dynamic")


def _utc_now() -> datetime:
    """Provee un único punto de obtención de timestamps en UTC."""
    return datetime.now(timezone.utc)


class Loan(db.Model):
    """Préstamo asociado a una instancia física concreta."""

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    instance_id: int = db.Column(
        db.Integer, db.ForeignKey("item_instance.id"), nullable=False, index=True
    )
    environment: Optional[str] = db.Column(db.String(50), nullable=True)

    request_date: datetime = db.Column(db.DateTime, default=_utc_now)
    approval_date: Optional[datetime] = db.Column(db.DateTime, nullable=True)
    due_date: Optional[datetime] = db.Column(db.DateTime, nullable=True)
    return_date: Optional[datetime] = db.Column(db.DateTime, nullable=True)

    status: LoanStatus = db.Column(
        db.Enum(
            LoanStatus,
            name="loan_status_enum",
            create_constraint=True,
        ),
        default=LoanStatus.PENDING,
        nullable=False,
        index=True,
    )
    observation: Optional[str] = db.Column(db.Text, nullable=True)
    final_penalty: Decimal = db.Column(Numeric(10, 2), default=Decimal("0.00"))

    requester = db.relationship(
        "User", backref=db.backref("loans", lazy="dynamic")
    )

    @property
    def request_date_co(self) -> Optional[datetime]:
        """Convierte la fecha de solicitud a zona horaria operativa."""
        if not self.request_date:
            return None
        utc_dt = (
            self.request_date
            if self.request_date.tzinfo
            else self.request_date.replace(tzinfo=timezone.utc)
        )
        return utc_dt.astimezone(ZoneInfo("America/Bogota"))

    @property
    def due_date_co(self) -> Optional[datetime]:
        """Convierte la fecha de vencimiento a zona horaria operativa."""
        if not self.due_date:
            return None
        utc_dt = (
            self.due_date
            if self.due_date.tzinfo
            else self.due_date.replace(tzinfo=timezone.utc)
        )
        return utc_dt.astimezone(ZoneInfo("America/Bogota"))

    @property
    def is_overdue(self) -> bool:
        """Evalúa mora ignorando estados terminales para coherencia de negocio."""
        if self.status not in (LoanStatus.RETURNED, LoanStatus.REJECTED) and self.due_date:
            now = datetime.now(timezone.utc)
            due = (
                self.due_date
                if self.due_date.tzinfo
                else self.due_date.replace(tzinfo=timezone.utc)
            )
            return now > due
        return False

    def penalty_fee(self, fee_per_day: float = 5000.0) -> float:
        """Calcula la multa basada en días de mora."""
        if not self.item_instance or not self.item_instance.catalog_item.is_penalty_applicable:
            return 0.0

        if self.is_overdue and self.due_date:
            now = datetime.now(timezone.utc)
            due = (
                self.due_date
                if self.due_date.tzinfo
                else self.due_date.replace(tzinfo=timezone.utc)
            )
            days_late = (now - due).days
            if days_late > 0:
                return float(days_late * fee_per_day)
        return 0.0

class LibraryLog(db.Model):
    """Registro de uso de la biblioteca con fines estadísticos."""

    id: int = db.Column(db.Integer, primary_key=True)
    visitor_name: str = db.Column(db.String(100), nullable=False)
    visitor_id: str = db.Column(db.String(20), nullable=False)
    role: str = db.Column(db.String(20), nullable=False)
    entry_time: datetime = db.Column(db.DateTime, default=_utc_now)
    activity: str = db.Column(db.String(50), nullable=False)
