from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app import db
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.instructor_dashboard'))
    
    if request.method == 'POST':
        # Cambiamos 'username' por 'document_id' para el login
        document_id = request.form['username'] # En el login.html el campo se llama 'username' aunque metan la cédula
        password = request.form['password']
        
        # Buscamos por document_id (que ahora duplicamos como username)
        user = User.query.filter_by(document_id=document_id).first()
        
        if user and user.check_password(password):
            login_user(user)
            if user.role == 'bibliotecario':
                return redirect(url_for('admin.admin_dashboard'))
            return redirect(url_for('main.instructor_dashboard'))
        
        flash('Documento o contraseña incorrectos', 'danger')
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Recolectar datos del formulario nuevo
        document_id = request.form.get('document_id')
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        role = request.form.get('role')
        password = request.form.get('password')
        
        # Campos opcionales (solo aprendices)
        ficha = request.form.get('ficha') if role == 'aprendiz' else None
        program_name = request.form.get('program_name') if role == 'aprendiz' else None
        
        # Validar si ya existe
        if User.query.filter_by(document_id=document_id).first():
            flash('El usuario con este documento ya existe', 'warning')
            return redirect(url_for('auth.register'))
            
        # CREAR USUARIO
        # Truco: Usamos el document_id también como 'username' para cumplir el requisito de la BD
        user = User(
            username=document_id, 
            document_id=document_id,
            full_name=full_name,
            phone=phone,
            role=role,
            ficha=ficha,
            program_name=program_name
        )
        
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registro exitoso. Ingresa con tu documento.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))