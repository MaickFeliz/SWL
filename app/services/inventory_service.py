from app import db
from app.models import Catalog, ItemInstance
from flask import current_app
from sqlalchemy.sql import func

class InventoryService:
    @staticmethod
    def reserve_instances(catalog_id, quantity):
        catalog = Catalog.query.get(int(catalog_id))
        if not catalog:
            return False, [], "Catálogo no encontrado."
            
        # BLOQUEO DE FILA: Evita condiciones de carrera en bases de datos reales
        available_instances = catalog.instances.filter_by(status='disponible')\
            .limit(quantity).with_for_update().all()
        
        if len(available_instances) < quantity:
            return False, [], f"Stock insuficiente. Disponibles: {len(available_instances)}"
            
        reserved_ids = []
        for instance in available_instances:
            # Cambiamos su estado de inmediato
            instance.status = 'prestado' 
            reserved_ids.append(instance.id)
            
        if catalog.available_count == 0:
            current_app.logger.warning(f"¡ALERTA DE STOCK! El catálogo '{catalog.title_or_name}' se ha quedado sin unidades disponibles.")
            
        return True, reserved_ids, "Instancias físicas reservadas exitosamente."

    @staticmethod
    def release_instance(instance_id):
        instance = ItemInstance.query.get(instance_id)
        if not instance:
            return False, "Instancia física no encontrada."
            
        instance.status = 'disponible'
        return True, "Instancia liberada y devuelta al inventario."

class CatalogService:
    @staticmethod
    def get_paginated_catalog(page, per_page=12, category_filter=None, exclude_category=None):
        """
        Retorna los ítems del catálogo paginados junto con su conteo de stock,
        solucionando el problema N+1 mediante un JOIN y GROUP BY.
        """
        query = db.session.query(
            Catalog, 
            func.count(ItemInstance.id).label('available_count')
        ).outerjoin(
            ItemInstance, (ItemInstance.catalog_id == Catalog.id) & (ItemInstance.status == 'disponible')
        ).group_by(Catalog.id)

        if category_filter:
            query = query.filter(Catalog.category == category_filter)
        if exclude_category:
            query = query.filter(Catalog.category != exclude_category)

        return query.paginate(page=page, per_page=per_page, error_out=False)