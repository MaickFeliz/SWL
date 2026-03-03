from app import db, login_manager
from flask import current_app
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
    password_hash = db.Column(db.String(255))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 1. EL CATÁLOGO (Lo genérico)
class Catalog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title_or_name = db.Column(db.String(150), nullable=False) 
    category = db.Column(db.String(50), nullable=False) 
    author_or_brand = db.Column(db.String(100), nullable=True) 
    
    instances = db.relationship('ItemInstance', backref='catalog_item', lazy='dynamic', cascade="all, delete-orphan")

    @property
    def available_count(self):
        return self.instances.filter_by(status='disponible').count()
        
    @property
    def total_count(self):
        return self.instances.count()

# 2. LAS INSTANCIAS (El objeto físico real)
class ItemInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    catalog_id = db.Column(db.Integer, db.ForeignKey('catalog.id'), nullable=False)
    unique_code = db.Column(db.String(50), unique=True, nullable=False) 
    status = db.Column(db.String(20), default='disponible') # disponible, prestado, mantenimiento, perdido
    condition = db.Column(db.String(100), nullable=True) 
    
    loans = db.relationship('Loan', backref='item_instance', lazy='dynamic')

# 3. EL PRÉSTAMO REAL
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instance_id = db.Column(db.Integer, db.ForeignKey('item_instance.id'), nullable=False)
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
        # Leemos la categoría directamente de la instancia vinculada
        if not self.item_instance or self.item_instance.catalog_item.category != 'libro':
            return 0.0

        if self.is_overdue:
            days_late = (datetime.utcnow() - self.due_date).days
            if days_late > 0:
                # Obtenemos el valor de la multa desde la configuración
                fee = current_app.config.get('PENALTY_FEE_PER_DAY', 5000.0)
                return days_late * fee
        return 0.0

# 4. USO DE BIBLIOTECA
class LibraryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_id = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False) 
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    activity = db.Column(db.String(50), nullable=False)
