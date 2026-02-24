from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Decorador genérico para proteger rutas basadas en roles.
    Si el usuario actual no tiene ninguno de los roles proporcionados,
    se le deniega el acceso.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor inicie sesión para acceder a esta página.', 'warning')
                return redirect(url_for('auth.login'))
                
            if current_user.role not in roles:
                flash('Acceso denegado. No tienes permisos suficientes.', 'danger')
                
                # Redireccionamiento seguro según el rol
                if current_user.role == 'bibliotecario':
                    return redirect(url_for('admin.admin_dashboard'))
                elif current_user.role == 'premium':
                    return redirect(url_for('main.premium_dashboard'))
                else:
                    return redirect(url_for('main.index'))
                    
            return f(*args, **kwargs)
        return decorated_function
    return decorator
