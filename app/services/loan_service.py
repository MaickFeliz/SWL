from app import db
from app.models import Loan, Inventory
from datetime import datetime
from flask import current_app

class LoanService:
    @staticmethod
    def create_loan(user_id, loan_type, item_name, quantity=1, item_code=None, environment=None):
        new_loan = Loan(
            user_id=user_id,
            loan_type=loan_type,
            item_name=item_name,
            item_code=item_code,
            quantity=quantity,
            environment=environment,
            status='pendiente'
        )
        db.session.add(new_loan)
        db.session.commit()
        return new_loan

    @staticmethod
    def approve_loan(loan_id, item_code):
        loan = Loan.query.get_or_404(loan_id)
        loan.item_code = item_code
        loan.status = 'activo'
        loan.approval_date = datetime.utcnow()
        db.session.commit()
        return loan

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
        Marca como 'atrasado' los préstamos activos que superen un tiempo determinado (ej. 24h).
        """
        # TODO: Implementar lógica de cronjob/tiempo
        pass
