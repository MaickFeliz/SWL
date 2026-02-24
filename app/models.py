from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 1. REGISTRO (Clientes y Premium)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False) # Para login
    email = db.Column(db.String(120), unique=True, nullable=True)
    
    # Nuevos campos requeridos
    document_id = db.Column(db.String(20), unique=True, nullable=False) # Cédula/TI
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    
    role = db.Column(db.String(20), nullable=False) # 'cliente', 'premium', 'bibliotecario'
    
    # Específico para clientes (nullable porque los premium no tienen esto)
    program_name = db.Column(db.String(100), nullable=True)

    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Para manejar el inventario (Punto 3: Mouse, VideoBeam, etc.)
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True) # Ej: Mouse, VideoBeam, HDMI
    total_quantity = db.Column(db.Integer, default=0)
    available_quantity = db.Column(db.Integer, default=0)
    
    # Tipo de item para filtrar qué pueden pedir los clientes vs premium
    category = db.Column(db.String(20), default='general') # 'general', 'premium_only', 'lego'

# 2, 3, 5 y 6. PRÉSTAMOS (Unificamos lógica pero con campos flexibles)
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Tipo de préstamo para saber qué formulario usar
    loan_type = db.Column(db.String(20), nullable=False) # 'computo', 'elemento', 'libro'
    
    # Detalles del elemento
    item_name = db.Column(db.String(100), nullable=False) # Nombre del equipo o Título del libro
    item_code = db.Column(db.String(50), nullable=True) # Serial del PC o Código del libro
    quantity = db.Column(db.Integer, default=1) # Para mouses o cables
    
    # Contexto (Puntos 2 y 6)
    environment = db.Column(db.String(50), nullable=True) # Área o Sala

    # Tiempos
    request_date = db.Column(db.DateTime, default=datetime.utcnow) # Fecha automática solicitud
    approval_date = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True) # Fecha límite para devolución
    return_date = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(20), default='pendiente') # pendiente, activo, devuelto, rechazado, atrasado
    observation = db.Column(db.Text, nullable=True) # Por si devuelven algo dañado

    requester = db.relationship('User', backref=db.backref('loans', lazy='dynamic'))

    @property
    def is_overdue(self):
        """Devuelve True si el artículo no ha sido devuelto y ya pasó la fecha límite."""
        if self.status not in ['devuelto', 'rechazado'] and self.due_date:
            return datetime.utcnow() > self.due_date
        return False

    @property
    def penalty_fee(self):
        """Calcula una multa de $5,000 COP por cada día de retraso (Ajustar según necesidad)."""
        if self.is_overdue:
            days_late = (datetime.utcnow() - self.due_date).days
            # Evita cobros negativos si apenas es el mismo día
            if days_late > 0:
                return days_late * 5000.0
        return 0.0

# 4. USO DE BIBLIOTECA (Registro de visitas)
class LibraryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # No usamos ForeignKey estricta porque puede ser un "visitante" externo no registrado
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_id = db.Column(db.String(20), nullable=False)
    role = db.Column(db.String(20), nullable=False) # Cliente, Premium, Visitante
    
    entry_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    activity = db.Column(db.String(50), nullable=False) 
    # Opciones: Asesoría, Lectura, Reunión, Capacitación, PC mesa, Tablero, Otro, LEGO (Solo premium)