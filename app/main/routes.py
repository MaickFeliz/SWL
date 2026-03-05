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
from app.forms import RequestItemForm, VisitForm, FastLoanSearchForm, FastLoanForm

@bp.route('/fast_loan', methods=['GET', 'POST'])
@login_required
def fast_loan():
    search_form = FastLoanSearchForm()
    loan_form = FastLoanForm()

    user_id = request.form.get('user_id')
    user = None
    if user_id:
        user = User.query.get(user_id)
    elif search_form.validate_on_submit() and search_form.submit_search.data:
        user = User.query.filter_by(document_id=search_form.document_id.data).first()

    exclude_cat = 'general' if user and user.role == 'premium' else None
    all_items = CatalogService.get_catalog_with_counts(exclude_category=exclude_cat)
    # Populate the choices for SelectField here so validation doesn't fail
    loan_form.catalog_id.choices = [(i.id, f"{i.title_or_name} (Disponibles: {i.available_count})") for i in all_items if i.available_count > 0]

    # 1. FLUJO DE BÚSQUEDA DE USUARIO
    if search_form.validate_on_submit() and search_form.submit_search.data:
        if not user:
            flash('Usuario no encontrado. Debes estar registrado.', 'danger')
            return redirect(url_for('main.fast_loan'))
        
        return render_template('main/fast_loan.html', user=user, search_form=search_form, loan_form=loan_form)

    # 2. FLUJO DE CONFIRMACIÓN DE PRÉSTAMO
    if loan_form.validate_on_submit() and loan_form.submit_loan.data:
        target_user_id = loan_form.user_id.data
        if current_user.role not in ('admin', 'bibliotecario'):
            try:
                tid = int(target_user_id)
            except (TypeError, ValueError):
                tid = None
            if tid is None or tid != current_user.id:
                flash('Operación no autorizada.', 'danger')
                return redirect(url_for('main.index'))
        user_id = target_user_id
        item_type = loan_form.item_type.data
        environment = loan_form.environment.data
        catalog_id = loan_form.catalog_id.data
        quantity = 1 if item_type == 'computo' else loan_form.quantity.data

        success, reserved_ids, msg = InventoryService.reserve_instances(catalog_id, quantity)
        if not success:
            flash(msg, 'warning')
            return redirect(url_for('main.fast_loan'))
            
        try:
            for inst_id in reserved_ids:
                LoanService.create_loan(user_id=user_id, instance_id=inst_id, environment=environment)
            db.session.commit()
            flash('Préstamo rápido registrado con éxito.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud. Intente nuevamente.', 'danger')

        return redirect(url_for('main.index'))
        
    return render_template('main/fast_loan.html', search_form=search_form, loan_form=loan_form)

@bp.route('/visit', methods=['GET', 'POST'])
def register_visit():
    form = VisitForm()
    
    # Procesamos la visita modernamente con WTForms
    if form.validate_on_submit():
        document_id = form.document_id.data
        activity = form.activity.data
        manual_name = form.visitor_name.data or ''
        
        user = User.query.filter_by(document_id=document_id).first()
        
        if user:
            name, role = user.full_name, user.role
        else:
            if not manual_name:
                flash('Documento no registrado. Por favor ingrese su Nombre.', 'warning')
                return render_template('main/visit.html', form=form, pre_doc=document_id)
            name, role = manual_name, 'Visitante'
            
        visit = LibraryLog(visitor_name=name, visitor_id=document_id, role=role, activity=activity)
        db.session.add(visit)
        db.session.commit()
        
        flash(f'Bienvenido/a {name}. Actividad: {activity}', 'success')
        return redirect(url_for('main.register_visit'))
        
    return render_template('main/visit.html', form=form)

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
    form = RequestItemForm()
    # Usamos el servicio para evitar el N+1
    available_books = CatalogService.get_catalog_with_counts(category_filter='libro')

    if form.validate_on_submit():
        catalog_id = form.catalog_id.data
        
        # ¡BOMBA DESACTIVADA!
        # No consultamos el modelo Catalog en el controlador, y evitamos llamar a .available_count
        # El servicio de inventario hace todo el chequeo físico transaccional por nosotros.
        success, reserved_ids, msg = InventoryService.reserve_instances(catalog_id, 1)
        
        if not success:
            flash(msg, 'danger')
            return redirect(url_for('main.request_book'))
            
        try:
            LoanService.create_loan(user_id=current_user.id, instance_id=reserved_ids[0])
            db.session.commit()
            flash('Solicitud de libro registrada. Acércate al mostrador.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Ocurrió un error al registrar la solicitud.', 'danger')
            
        return redirect(url_for('main.premium_dashboard'))
        
    return render_template('premium/request_book.html', items=available_books, form=form)

    