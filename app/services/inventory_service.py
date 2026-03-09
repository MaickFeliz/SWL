from app import db
from app.models import Catalog, ItemInstance, InventoryStatus
from flask import current_app
from sqlalchemy.sql import func
import sqlalchemy.exc

class InventoryService:
    @staticmethod
    def reserve_instances(catalog_id: int, quantity: int):
        try:
            catalog = db.session.get(Catalog, int(catalog_id))
            if not catalog:
                return False, [], "Catálogo no encontrado."
                
            # skip_locked=True evita que la app se cuelgue esperando si otro usuario ya bloqueó la fila
            available_instances = catalog.instances.filter_by(status=InventoryStatus.AVAILABLE)\
                .limit(quantity).with_for_update(skip_locked=True).all()
            
            if len(available_instances) < quantity:
                return False, [], "Stock físico insuficiente o temporalmente bloqueado por otra transacción."
                
            reserved_ids = []
            for instance in available_instances:
                instance.status = InventoryStatus.LOANED
                reserved_ids.append(instance.id)
                
            return True, reserved_ids, "Instancias reservadas exitosamente."
            
        except sqlalchemy.exc.OperationalError as e:
            db.session.rollback()
            current_app.logger.error(f"Error de concurrencia en reserva: {str(e)}")
            return False, [], "El sistema está procesando otra solicitud para este ítem. Intente nuevamente."
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error inesperado: {str(e)}")
            return False, [], "Error interno al procesar el inventario."

    @staticmethod
    def release_instance(instance_id: int):
        instance = db.session.get(ItemInstance, instance_id)
        if not instance:
            return False, "Instancia física no encontrada."
            
        instance.status = InventoryStatus.AVAILABLE
        return True, "Instancia liberada y devuelta al inventario."

class CatalogService:
    @staticmethod
    def get_catalog_with_counts(category_filter=None, exclude_category=None):
        """
        Retorna la lista de ítems sin paginación (para combos y listas pequeñas)
        inyectando dinámicamente 'available_count' para no romper el frontend.
        """
        query = db.session.query(
            Catalog, 
            func.count(ItemInstance.id).label('avail_count')
        ).outerjoin(
            ItemInstance,
            (ItemInstance.catalog_id == Catalog.id)
            & (ItemInstance.status == InventoryStatus.AVAILABLE),
        ).group_by(Catalog.id)

        if category_filter:
            query = query.filter(Catalog.category == category_filter)
        if exclude_category:
            query = query.filter(Catalog.category != exclude_category)

        results = query.all()
        items = []
        for catalog_obj, count in results:
            # Inyección dinámica: el frontend puede seguir usando item.available_count
            catalog_obj.available_count = count 
            items.append(catalog_obj)
        return items

    @staticmethod
    def get_paginated_catalog(page, per_page=12, category_filter=None, exclude_category=None):
        """
        Retorna los ítems del catálogo paginados junto con su conteo de stock,
        solucionando el problema N+1 mediante un JOIN y GROUP BY.
        """
        query = db.session.query(
            Catalog, 
            func.count(ItemInstance.id).label('avail_count')
        ).outerjoin(
            ItemInstance,
            (ItemInstance.catalog_id == Catalog.id)
            & (ItemInstance.status == InventoryStatus.AVAILABLE),
        ).group_by(Catalog.id)

        if category_filter:
            query = query.filter(Catalog.category == category_filter)
        if exclude_category:
            query = query.filter(Catalog.category != exclude_category)

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        items = []
        for catalog_obj, count in pagination.items:
            catalog_obj.available_count = count
            items.append(catalog_obj)
        pagination.items = items
        return pagination