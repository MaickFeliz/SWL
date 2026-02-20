from app import db
from app.models import Inventory
from flask import current_app

class InventoryService:
    @staticmethod
    def deduct_stock(item_name, quantity):
        item = Inventory.query.filter_by(name=item_name).first()
        if not item:
            return False, "Ítem no encontrado en el inventario."
            
        if item.available_quantity < quantity:
            return False, f"Stock insuficiente. Disponibles: {item.available_quantity}"
            
        item.available_quantity -= quantity
        db.session.commit()
        
        # Log critical warning si el stock llega a cero
        if item.available_quantity == 0:
            current_app.logger.warning(f"¡ALERTA DE STOCK! El ítem '{item.name}' ha llegado a cero unidades disponibles.")
            
        return True, "Stock descontado exitosamente."

    @staticmethod
    def add_stock(item_name, quantity):
        item = Inventory.query.filter_by(name=item_name).first()
        if not item:
            return False, "Ítem no encontrado para restaurar stock."
            
        item.available_quantity += quantity
        
        # Evitar sobreflujo del total original (opcional, pero buena práctica)
        if item.available_quantity > item.total_quantity:
             item.available_quantity = item.total_quantity
             
        db.session.commit()
        return True, "Stock restaurado."
        
    @staticmethod
    def create_item(name, category, quantity):
        if Inventory.query.filter_by(name=name).first():
            return False, "El elemento ya existe."
            
        new_item = Inventory(
            name=name, 
            category=category, 
            total_quantity=quantity, 
            available_quantity=quantity
        )
        db.session.add(new_item)
        db.session.commit()
        return True, "Elemento creado."
