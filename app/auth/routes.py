from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app import db
from app.models import User
from app.forms import LoginForm, RegistrationForm

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(document_id=form.document_id.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Documento o contraseña inválidos.', 'danger')
            return render_template('auth/login.html', form=form)
        
        login_user(user, remember=False)
        
        if user.role == 'admin':
            return redirect(url_for('admin.manage_users'))
        elif user.role == 'bibliotecario':
            return redirect(url_for('admin.admin_dashboard'))
        elif user.role == 'premium':
            return redirect(url_for('main.premium_dashboard'))
        return redirect(url_for('main.index'))
        
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Validar que no exista ni el documento ni el email
        if User.query.filter_by(document_id=form.document_id.data).first():
            flash('El número de documento ya está registrado.', 'warning')
            return render_template('auth/register.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('La dirección de correo electrónico ya está registrada.', 'warning')
            return render_template('auth/register.html', form=form)

        user = User(
            full_name=form.full_name.data,
            document_id=form.document_id.data,
            email=form.email.data,
            phone=form.phone.data,
            role=form.role.data
        )
        if form.role.data == 'cliente':
            user.program_name = form.program_name.data

        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('¡Registro exitoso! Ahora puede iniciar sesión con su número de documento.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    flash('Ha cerrado la sesión exitosamente.', 'info')
    return redirect(url_for('auth.login'))