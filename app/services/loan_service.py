from app import db
from app.models import Loan, Inventory
from datetime import datetime, timedelta
from flask import current_app

class LoanService:
    @staticmethod
    def create_loan(user_id, loan_type, item_name, quantity=1, item_code=None, environment=None, days=15):
        try:
            due_date = datetime.utcnow() + timedelta(days=days)
            new_loan = Loan(
                user_id=user_id,
                loan_type=loan_type,
                item_name=item_name,
                item_code=item_code,
                quantity=quantity,
                environment=environment,
                status='pendiente',
                due_date=due_date
            )
            db.session.add(new_loan)
            db.session.commit()
            return new_loan
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def approve_loan(loan_id, item_code):
        loan = Loan.query.get_or_404(loan_id)
        
        # Validar que si piden más de 1 equipo, se ingresen todos los seriales separados por coma
        if loan.quantity > 1 and item_code:
            seriales = [s.strip() for s in item_code.split(',') if s.strip()]
            if len(seriales) != loan.quantity:
                return False, f"Se solicitaron {loan.quantity} equipos, pero ingresaste {len(seriales)} serial(es)."

        loan.item_code = item_code
        loan.status = 'activo'
        loan.approval_date = datetime.utcnow()
        db.session.commit()
        return True, "Préstamo aprobado correctamente."
        
    @staticmethod
    def return_loan(loan_id):
        loan = Loan.query.get_or_404(loan_id)
        if loan.status == 'devuelto':
            return False, "El préstamo ya fue devuelto."
            
        loan.status = 'devuelto'
        loan.return_date = datetime.utcnow()
        db.session.commit()
        return True, "Préstamo marcado como devuelto."
        
    @staticmethod
    def check_overdue_loans():
        """
        Marca como 'atrasado' los préstamos activos que superen su fecha límite.
        Esta función ahora sí hace el trabajo.
        """
        # Buscamos todos los préstamos activos cuya fecha de vencimiento ya pasó
        overdue_loans = Loan.query.filter(Loan.status == 'activo', Loan.due_date < datetime.utcnow()).all()
        
        count = 0
        for loan in overdue_loans:
            loan.status = 'atrasado'
            count += 1
            
        # Solo hacemos commit si realmente hubo préstamos que actualizar
        if count > 0:
            db.session.commit()
            
        return count
