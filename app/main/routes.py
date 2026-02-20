from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.main import bp
from app import db
from app.models import Loan, Inventory, User, LibraryLog
from app.services.loan_service import LoanService
from app.utils.decorators import role_required
from datetime import datetime

# app/main/routes.py
@bp.route('/fast_loan', methods=['POST'])
def fast_loan():
    document_id = request.form.get('document_id')
    item_id = request.form.get('item_id')
    
    user = User.query.filter_by(document_id=document_id).first()
    item = Inventory.query.get_or_404(item_id)
    
    if not user:
        flash('Usuario no encontrado. Debes estar registrado para esta acción.', 'danger')
        return redirect(url_for('main.index'))
        
    try:
        LoanService.create_loan(user.id, 'elemento', item.name, quantity=1)
        flash('Solicitud rápida creada con éxito. Esperando validación en el mostrador.', 'success')
    except Exception as e:
        db.session.rollback()  # ESTO ES VITAL. Si hay un fallo, se revierte la transacción.
        flash('Error de base de datos al procesar la solicitud. Intenta nuevamente.', 'danger')
        # app.logger.error(f"Fallo en préstamo rápido: {str(e)}") # Así lo logueas en un sistema real
        
    return redirect(url_for('main.index'))

@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'bibliotecario':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('main.premium_dashboard'))
    return render_template('main/index.html')

@bp.route('/dashboard')
@role_required('premium', 'cliente')
def premium_dashboard():
    # Consulta los préstamos del usuario actual (tu plantilla los está esperando en el ciclo for)
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.request_date.desc()).all()
    
    return render_template('premium/dashboard.html', loans=loans)

@bp.route('/request/laptop', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_laptop():
    if request.method == 'POST':
        environment = request.form.get('environment')
        if current_user.role == 'premium':
            quantity = int(request.form.get('quantity'))
        else:
            quantity = 1

        active_loans_query = Loan.query.filter(
            Loan.user_id == current_user.id,
            Loan.status.in_(['pendiente', 'aprobado']),
            Loan.loan_type == 'computo'
        )

        if current_user.role == 'cliente' and active_loans_query.first():
            flash('Ya tienes un equipo pendiente o en uso.', 'warning')
            return redirect(url_for('main.premium_dashboard'))

        LoanService.create_loan(
            user_id=current_user.id,
            loan_type='computo',           
            item_name='Computador Portátil',
            quantity=quantity,
            environment=environment
        )
        flash('Solicitud de portátil enviada.', 'success')
        return redirect(url_for('main.premium_dashboard'))
    return render_template('premium/request_laptop.html')

# --- ACCESORIOS (MOUSE/VIDEOBEAM) ---
@bp.route('/request/accessory', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_accessory():
    if current_user.role == 'cliente':
        available_items = Inventory.query.filter_by(category='general').all()
    else:
        available_items = Inventory.query.all()

    if request.method == 'POST':
        item_id = request.form.get('item_id')
        quantity = int(request.form.get('quantity'))
        inventory_item = Inventory.query.get(item_id)
        
        if not inventory_item or inventory_item.available_quantity < quantity:
            flash('Stock insuficiente o ítem inválido.', 'danger')
            return redirect(url_for('main.request_accessory'))

        # El stock se restará cuando el admin apruebe el préstamo
        LoanService.create_loan(
            user_id=current_user.id,
            loan_type='elemento',
            item_name=inventory_item.name,
            quantity=quantity
        )
        flash(f'Solicitud de {inventory_item.name} realizada.', 'success')
        return redirect(url_for('main.premium_dashboard'))
    return render_template('premium/request_accessory.html', items=available_items)

@bp.route('/request/book', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_book():
    if request.method == 'POST':
        title = request.form.get('book_title')
        code = request.form.get('book_code')
        
        LoanService.create_loan(
            user_id=current_user.id,
            loan_type='libro',
            item_name=title,
            item_code=code,
            quantity=1
        )
        flash('Solicitud de libro registrada. Acércate al mostrador.', 'success')
        return redirect(url_for('main.premium_dashboard'))
    return render_template('premium/request_book.html')

@bp.route('/visit', methods=['GET', 'POST'])
def register_visit():
    if request.method == 'POST':
        document_id = request.form.get('document_id')
        activity = request.form.get('activity')
        manual_name = request.form.get('visitor_name')
        
        user = User.query.filter_by(document_id=document_id).first()
        
        if user:
            name = user.full_name
            role = user.role
        else:
            
            if not manual_name:
                flash('Documento no registrado. Por favor ingrese su Nombre.', 'warning')
                return render_template('main/visit.html', pre_doc=document_id)
            name = manual_name
            role = 'Visitante'
            
        visit = LibraryLog(
            visitor_name=name,
            visitor_id=document_id,
            role=role,
            activity=activity
        )
        db.session.add(visit)
        db.session.commit()
        
        flash(f'Bienvenido/a {name}. Actividad: {activity}', 'success')
        return redirect(url_for('main.register_visit'))
        
    return render_template('main/visit.html')