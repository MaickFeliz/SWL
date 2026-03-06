from __future__ import annotations

from io import BytesIO
from typing import Final

import pandas as pd
from flask import current_app

from app import db
from app.models import Catalog, InventoryStatus, ItemInstance, Loan, LoanStatus, User


EXCEL_MIME_TYPE: Final[str] = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


class ReportService:
    """Agrega datos de negocio para reportes administrativos sin escribir a disco.

    Separamos esta capa para poder optimizar o cambiar el formato de salida
    (Excel, CSV, etc.) sin impactar controladores ni plantillas.
    """

    @staticmethod
    def generate_overdue_users_report() -> BytesIO:
        """Genera un Excel con los usuarios con mayor mora acumulada.

        Se basa en los préstamos con estado LoanStatus.OVERDUE y reutiliza
        la lógica de penalización de dominio para evitar duplicar reglas.
        """
        overdue_loans = (
            db.session.query(Loan, User)
            .join(User, Loan.user_id == User.id)
            .filter(Loan.status == LoanStatus.OVERDUE)
            .all()
        )

        rows = []
        for loan, user in overdue_loans:
            rows.append(
                {
                    "Usuario": user.full_name,
                    "Documento": user.document_id,
                    "Correo": user.email,
                    "Teléfono": user.phone,
                    "Días de mora": max(
                        0,
                        (
                            loan.penalty_fee
                            / current_app.config.get("PENALTY_FEE_PER_DAY", 5000.0)
                        )
                        if loan.penalty_fee
                        else 0,
                    ),
                    "Multa estimada": float(loan.penalty_fee),
                }
            )

        df = pd.DataFrame(rows)

        if not df.empty:
            df = (
                df.groupby(["Usuario", "Documento", "Correo", "Teléfono"], as_index=False)
                .agg({"Días de mora": "sum", "Multa estimada": "sum"})
                .sort_values(by=["Multa estimada", "Días de mora"], ascending=False)
                .head(10)
            )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Usuarios Morosos")
        output.seek(0)
        return output

    @staticmethod
    def generate_inventory_status_report() -> BytesIO:
        """Genera un Excel con el estado agregado del inventario por tipo de estado."""
        items = db.session.query(ItemInstance, Catalog).join(
            Catalog, ItemInstance.catalog_id == Catalog.id
        )

        rows = []
        for instance, catalog in items:
            rows.append(
                {
                    "Categoría": catalog.category,
                    "Ítem": catalog.title_or_name,
                    "Estado": instance.status.value
                    if isinstance(instance.status, InventoryStatus)
                    else str(instance.status),
                }
            )

        df = pd.DataFrame(rows)
        if not df.empty:
            df = (
                df.groupby(["Categoría", "Ítem", "Estado"], as_index=False)
                .size()
                .rename(columns={"size": "Cantidad"})
                .sort_values(by=["Categoría", "Ítem", "Estado"])
            )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Inventario Actual")
        output.seek(0)
        return output


# Casos de prueba principales a cubrir en tests:
# 1) generate_overdue_users_report() con base vacía debe devolver un Excel válido sin filas
#    y sin lanzar excepciones al abrirlo con openpyxl.
# 2) generate_overdue_users_report() con múltiples préstamos atrasados del mismo usuario
#    debe agregar correctamente multas y días de mora y ordenar por mayor monto.
# 3) generate_inventory_status_report() debe agrupar y contar instancias por categoría,
#    ítem y estado, reflejando con precisión los datos cargados en la base de pruebas.

