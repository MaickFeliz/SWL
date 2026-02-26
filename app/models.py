from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# REGISTRO (Clientes y Premium)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    
    document_id = db.Column(db.String(20), unique=True, nullable=False) 
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    
    role = db.Column(db.String(20), nullable=False) 
    program_name = db.Column(db.String(100), nullable=True)

    # CORRECCIÓN: Ampliación a 255 caracteres para el hash de la contraseña
    password_hash = db.Column(db.String(255))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Para manejar el inventario
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True) 
    total_quantity = db.Column(db.Integer, default=0)
    available_quantity = db.Column(db.Integer, default=0)
    
    category = db.Column(db.String(20), default='general') 

# PRÉSTAMOS
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    loan_type = db.Column(db.String(20), nullable=False) 
    
    item_name = db.Column(db.String(100), nullable=False) 
    item_code = db.Column(db.Text, nullable=True) 
    quantity = db.Column(db.Integer, default=1) 

    environment = db.Column(db.String(50), nullable=True) 

    request_date = db.Column(db.DateTime, default=datetime.utcnow) 
    approval_date = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True) 
    return_date = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(20), default='pendiente') 
    observation = db.Column(db.Text, nullable=True) 
    
    final_penalty = db.Column(db.Float, default=0.0) 

    requester = db.relationship('User', backref=db.backref('loans', lazy='dynamic'))

    @property
    def is_overdue(self):
        if self.status not in ['devuelto', 'rechazado'] and self.due_date:
            return datetime.utcnow() > self.due_date
        return False

    @property
    def penalty_fee(self):
        if self.loan_type != 'libro':
            return 0.0

        if self.is_overdue:
            days_late = (datetime.utcnow() - self.due_date).days
            if days_late > 0:
                return days_late * 5000.0
        return 0.0

# USO DE BIBLIOTECA (Registro de visitas)
class LibraryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_id = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    activity = db.Column(db.String(50), nullable=False)