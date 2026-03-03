import os
from datetime import timedelta

class Config:
    # Seguridad básica
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-para-desarrollo'
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Base de datos: Usa PostgreSQL si está en las variables de entorno, sino cae en SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # --- PARÁMETROS DE NEGOCIO ---
    # Multa por día de retraso (Adiós números quemados)
    PENALTY_FEE_PER_DAY = float(os.environ.get('PENALTY_FEE_PER_DAY', 5000.0))
    
    # Logging
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'library.log')

    # Identidad Corporativa
    APP_NAME = "SWL"
    LIBRARY_NAME = "SWL"
    
    # Configuración de Roles estandarizada
    USER_ROLES = {
        'admin': 'Administrador del Sistema',
        'bibliotecario': 'Bibliotecario / Staff',
        'premium': 'Usuario Premium',
        'cliente': 'Estudiante / Cliente Regular'
    }