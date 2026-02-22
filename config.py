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
    APP_NAME = "LMS - Library Management System"
    LIBRARY_NAME = "LMS"
    
    # Configuración de Roles estandarizada
    USER_ROLES = {
        'admin': 'Administrador',
        'staff': 'Bibliotecario',
        'user': 'Estudiante/Usuario'
    }