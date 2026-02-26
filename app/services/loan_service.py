from app import db
from app.models import Loan, ItemInstance
from datetime import datetime, timedelta

class LoanService:
    @staticmethod
    def create_loan(user_id, instance_id, environment=None, days=15):
        # Calculamos la fecha límite de entrega
        due_date = datetime.utcnow() + timedelta(days=days)
        
        # Creamos el préstamo atado a la instancia física real
        new_loan = Loan(
            user_id=user_id,
            instance_id=instance_id,
            environment=environment,
            status='pendiente',
            due_date=due_date
        )
        db.session.add(new_loan)
        
        # Recuerda: NO HAGAS COMMIT AQUÍ. 
        # El controlador (routes.py) se encarga de confirmar la transacción completa.
        return new_loan

    @staticmethod
    def approve_loan(loan_id):
        loan = Loan.query.get(loan_id)
        if not loan or loan.status != 'pendiente':
            return False, "Préstamo no válido o ya procesado."
        
        loan.status = 'activo'
        loan.approval_date = datetime.utcnow()
        
        # El estado de la instancia física ya se puso en 'prestado' 
        # en el InventoryService al momento de hacer la solicitud.
        db.session.commit()
        return True, "Préstamo aprobado con éxito."

    @staticmethod
    def return_loan(loan_id):
        loan = Loan.query.get(loan_id)
        if not loan or loan.status not in ['activo', 'atrasado']:
            return False, "Préstamo no válido o no está activo."
        
        # Si el préstamo está atrasado, calculamos y guardamos la multa final
        if loan.is_overdue:
            loan.final_penalty = loan.penalty_fee
            
        loan.status = 'devuelto'
        loan.return_date = datetime.utcnow()
        
        # ¡Paso crucial! Liberamos la instancia física para que otro usuario la pueda pedir
        if loan.item_instance:
            loan.item_instance.status = 'disponible'
            
        db.session.commit()
        return True, "Artículo devuelto exitosamente al inventario."

    @staticmethod
    def check_overdue_loans():
        # Buscamos todos los préstamos activos cuya fecha de entrega ya pasó
        overdue_loans = Loan.query.filter(
            Loan.status == 'activo', 
            Loan.due_date < datetime.utcnow()
        ).all()
        
        count = 0
        for loan in overdue_loans:
            loan.status = 'atrasado'
            count += 1
            
        if count > 0:
            db.session.commit()
            
        return count