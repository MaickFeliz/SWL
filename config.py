import os

class Config:
    # Seguridad básica
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-para-desarrollo'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Identidad Open Source (Marca Blanca)
    APP_NAME = "OpenLib Manager"
    LIBRARY_NAME = "Biblioteca Institucional"
    
    # Configuración de Roles estandarizada
    USER_ROLES = {
        'admin': 'Administrador',
        'staff': 'Bibliotecario',
        'user': 'Estudiante/Usuario'
    }