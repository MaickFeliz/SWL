import os
from datetime import timedelta

class Config:
    # Seguridad básica
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-para-desarrollo'
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Logging
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'library.log')

    # Identidad Corporativa
    APP_NAME = "SWL"
    LIBRARY_NAME = "SWL"
    
    # CORRECCIÓN: Configuración de Roles estandarizada con los que usa la DB
    USER_ROLES = {
        'admin': 'Administrador del Sistema',
        'bibliotecario': 'Bibliotecario / Staff',
        'premium': 'Usuario Premium',
        'cliente': 'Estudiante / Cliente Regular'
    }