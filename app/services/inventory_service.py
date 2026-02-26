from app import db
from app.models import Catalog, ItemInstance
from flask import current_app

class InventoryService:
    @staticmethod
    def reserve_instances(catalog_id, quantity):
        catalog = Catalog.query.get(int(catalog_id))
        if not catalog:
            return False, [], "Catálogo no encontrado."
            
        # Buscar las instancias físicas que estén disponibles
        available_instances = catalog.instances.filter_by(status='disponible').limit(quantity).all()
        
        if len(available_instances) < quantity:
            return False, [], f"Stock insuficiente. Disponibles: {catalog.available_count}"
            
        reserved_ids = []
        for instance in available_instances:
            # Cambiamos su estado de inmediato para que nadie más lo tome
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
        