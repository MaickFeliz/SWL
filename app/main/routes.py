from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from markupsafe import escape
from app.services.inventory_service import InventoryService, CatalogService
from app.main import bp
from app import db
from app.models import Loan, Catalog, ItemInstance, User, LibraryLog
from app.services.loan_service import LoanService
from app.utils.decorators import role_required
from datetime import datetime
from app.forms import RequestItemForm, VisitForm

@bp.route('/fast_loan', methods=['GET', 'POST'])
def fast_loan():
    page = request.args.get('page', 1, type=int) # Paginación
    
    if request.method == 'GET':
        return render_template('main/fast_loan.html')

    if request.form.get('search_doc'):
        document_id = request.form.get('document_id')
        user = User.query.filter_by(document_id=document_id).first()
        if not user:
            flash('Usuario no encontrado. Debes estar registrado.', 'danger')
            return redirect(url_for('main.fast_loan'))
        
        # Paginación y prevención de problema N+1
        exclude_cat = 'general' if user.role == 'premium' else None
        paginated_items = CatalogService.get_paginated_catalog(page=page, per_page=12, exclude_category=exclude_cat)
        
        return render_template('main/fast_loan.html', user=user, items=paginated_items)

    if request.form.get('confirm_loan'):
        user_id = request.form.get('user_id')
        item_type = request.form.get('item_type')
        environment = request.form.get('environment')
        catalog_id = request.form.get('catalog_id')
        quantity = 1 if item_type == 'computo' else int(request.form.get('quantity', 1))

        if quantity <= 0:
            flash('La cantidad solicitada debe ser mayor a cero.', 'danger')
            return redirect(url_for('main.fast_loan'))

        try:
            # La lógica de validación ahora confía más en el servicio
            success, reserved_ids, msg = InventoryService.reserve_instances(catalog_id, quantity)
            if not success:
                flash(msg, 'warning')
                return redirect(url_for('main.fast_loan'))
                
            for inst_id in reserved_ids:
                LoanService.create_loan(user_id=user_id, instance_id=inst_id, environment=environment)
            
            db.session.commit()
            flash('Préstamo rápido registrado con éxito.', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud. Intente nuevamente.', 'danger')

        return redirect(url_for('main.index'))
    return redirect(url_for('main.fast_loan'))

@bp.route('/visit', methods=['GET', 'POST'])
def register_visit():
    if request.method == 'POST':
        # Sanitización de entradas manuales contra XSS
        document_id = escape(request.form.get('document_id', '').strip())
        activity = escape(request.form.get('activity', '').strip())
        manual_name = escape(request.form.get('visitor_name', '').strip())
        
        user = User.query.filter_by(document_id=document_id).first()
        
        if user:
            name, role = user.full_name, user.role
        else:
            if not manual_name:
                flash('Documento no registrado. Por favor ingrese su Nombre.', 'warning')
                return render_template('main/visit.html', pre_doc=document_id)
            name, role = manual_name, 'Visitante'
            
        visit = LibraryLog(visitor_name=name, visitor_id=document_id, role=role, activity=activity)
        db.session.add(visit)
        db.session.commit()
        
        flash(f'Bienvenido/a {name}. Actividad: {activity}', 'success')
        return redirect(url_for('main.register_visit'))
        
    return render_template('main/visit.html')

@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.manage_users'))
        elif current_user.role == 'bibliotecario':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role in ['premium', 'cliente']:
            return redirect(url_for('main.premium_dashboard'))
    return render_template('main/index.html')

@bp.route('/dashboard')
@role_required('premium', 'cliente')
def premium_dashboard():
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.request_date.desc()).all()
    return render_template('premium/dashboard.html', loans=loans)

@bp.route('/profile')
@login_required
def profile():
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.request_date.desc()).all()
    return render_template('main/profile.html', loans=loans)

@bp.route('/request/laptop', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_laptop():
    form = RequestItemForm()
    # Usamos el servicio para evitar el N+1
    available_computers = CatalogService.get_catalog_with_counts(category_filter='computo')

    if form.validate_on_submit(): # Validación segura CSRF
        # 1. Validación de reglas de negocio en el servicio
        can_request, msg = LoanService.can_request_laptop(current_user.id)
        if not can_request:
            flash(msg, 'warning')
            return redirect(url_for('main.premium_dashboard'))

        # 2. Configuración de parámetros
        quantity = form.quantity.data if current_user.role == 'premium' else 1
        catalog_id = form.catalog_id.data
        environment = form.environment.data

        # 3. Reserva Transaccional
        success, reserved_ids, r_msg = InventoryService.reserve_instances(catalog_id, quantity)
        if not success:
            flash(r_msg, 'danger')
            return redirect(url_for('main.premium_dashboard'))
            
        try:
            for inst_id in reserved_ids:
                LoanService.create_loan(user_id=current_user.id, instance_id=inst_id, environment=environment)
            db.session.commit()
            flash('Solicitud de portátil enviada correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al generar el préstamo.', 'danger')
            
        return redirect(url_for('main.premium_dashboard'))
        
    return render_template('premium/request_laptop.html', items=available_computers, form=form)

@bp.route('/request/accessory', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_accessory():
    form = RequestItemForm()
    # Validación de negocio
    can_request, msg = LoanService.can_request_accessory(current_user.id)
    if not can_request:
        flash(msg, 'warning')
        return redirect(url_for('main.index'))
    
    # N+1 resuelto
    exclude_cat = 'computo' if current_user.role == 'cliente' else None
    available_items = CatalogService.get_catalog_with_counts(exclude_category=exclude_cat)

    if form.validate_on_submit():
        catalog_id = form.catalog_id.data
        quantity = form.quantity.data
        
        success, reserved_ids, r_msg = InventoryService.reserve_instances(catalog_id, quantity)
        if not success:
            flash(r_msg, 'danger')
            return redirect(url_for('main.request_accessory'))

        try:
            for inst_id in reserved_ids:
                LoanService.create_loan(user_id=current_user.id, instance_id=inst_id)
            db.session.commit()
            flash('Solicitud realizada con éxito.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud.', 'danger')
            
        return redirect(url_for('main.premium_dashboard'))
        
    return render_template('premium/request_accessory.html', items=available_items, form=form)

@bp.route('/request/book', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_book():
    available_books = Catalog.query.filter_by(category='libro').all()

    if request.method == 'POST':
        catalog_id = request.form.get('catalog_id')
        book_item = Catalog.query.get(catalog_id)
        
        if not book_item or book_item.category != 'libro' or book_item.available_count < 1:
            flash('Ese libro no existe o no hay copias disponibles en este momento.', 'danger')
            return redirect(url_for('main.request_book'))

        try:
            # CORRECCIÓN 3: Uso centralizado del servicio transaccional para evitar libros fantasma
            success, reserved_ids, msg = InventoryService.reserve_instances(book_item.id, 1)
            if not success:
                flash(msg, 'danger')
                return redirect(url_for('main.request_book'))
                
            LoanService.create_loan(user_id=current_user.id, instance_id=reserved_ids[0])
            db.session.commit()
            flash('Solicitud de libro registrada. Acércate al mostrador.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error al registrar la solicitud transaccional.', 'danger')
            
        return redirect(url_for('main.premium_dashboard'))
    return render_template('premium/request_book.html', items=available_books)

    