from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'aprendiz', 'instructor', 'bibliotecario'
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    item_type = db.Column(db.String(50), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Lo llena el bibliotecario
    assigned_serial = db.Column(db.String(50), nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)
    return_date = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(20), default='pendiente') # pendiente, aprobado, devuelto

    requester = db.relationship('User', backref='loans')