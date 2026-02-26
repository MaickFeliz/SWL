from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.main import bp  # CORRECCIÓN 1: Blueprint correcto para evitar colisión de rutas
from app import db
from app.models import Loan, Catalog, ItemInstance, User, LibraryLog
from app.services.loan_service import LoanService
from app.services.inventory_service import InventoryService
from app.utils.decorators import role_required
from datetime import datetime

@bp.route('/fast_loan', methods=['GET', 'POST'])
def fast_loan():
    if request.method == 'GET':
        return render_template('main/fast_loan.html')

    if request.form.get('search_doc'):
        document_id = request.form.get('document_id')
        user = User.query.filter_by(document_id=document_id).first()
        if not user:
            flash('Usuario no encontrado. Debes estar registrado.', 'danger')
            return redirect(url_for('main.fast_loan'))
        
        items = Catalog.query.filter(Catalog.category != 'general').all() if user.role == 'premium' else Catalog.query.all()
        return render_template('main/fast_loan.html', user=user, items=items)

    if request.form.get('confirm_loan'):
        user_id = request.form.get('user_id')
        item_type = request.form.get('item_type')
        environment = request.form.get('environment')

        try:
            if item_type == 'computo':
                # CORRECCIÓN 2: El sistema ahora es dinámico y lee el ID del catálogo, no un texto quemado
                catalog_id = request.form.get('catalog_id')
                catalog_item = Catalog.query.get(catalog_id)
                
                if not catalog_item or catalog_item.category != 'computo' or catalog_item.available_count < 1:
                    flash('Equipo de cómputo inválido o sin stock físico disponible.', 'warning')
                    return redirect(url_for('main.fast_loan'))
                
                success, reserved_ids, msg = InventoryService.reserve_instances(catalog_item.id, 1)
                if not success:
                    flash(msg, 'danger')
                    return redirect(url_for('main.fast_loan'))
                    
                LoanService.create_loan(user_id=user_id, instance_id=reserved_ids[0], environment=environment)
            else:
                catalog_id = request.form.get('catalog_id')
                quantity = int(request.form.get('quantity', 1))
                if quantity <= 0:
                    flash('La cantidad solicitada debe ser mayor a cero.', 'danger')
                    return redirect(url_for('main.fast_loan'))
                    
                catalog_item = Catalog.query.get(catalog_id)
                
                if not catalog_item or catalog_item.available_count < quantity:
                    flash('Stock físico insuficiente para realizar el préstamo.', 'warning')
                    return redirect(url_for('main.fast_loan'))
                
                success, reserved_ids, msg = InventoryService.reserve_instances(catalog_item.id, quantity)
                if not success:
                    flash(msg, 'danger')
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
    available_computers = Catalog.query.filter_by(category='computo').all()

    if request.method == 'POST':
        environment = request.form.get('environment')
        quantity = int(request.form.get('quantity', 1)) if current_user.role == 'premium' else 1
        catalog_id = request.form.get('catalog_id')

        if quantity <= 0:
            flash('Cantidad inválida.', 'danger')
            return redirect(url_for('main.premium_dashboard'))

        active_loans_count = Loan.query.join(ItemInstance).join(Catalog).filter(
            Loan.user_id == current_user.id,
            Loan.status.in_(['pendiente', 'activo', 'atrasado']), 
            Catalog.category == 'computo'
        ).count()

        if active_loans_count > 0:
            flash('Ya tienes un equipo pendiente, en uso o atrasado.', 'warning')
            return redirect(url_for('main.premium_dashboard'))

        # CORRECCIÓN 2: Lógica dinámica de búsqueda de computadores
        laptop_item = Catalog.query.get(catalog_id)
        if not laptop_item or laptop_item.category != 'computo' or laptop_item.available_count < quantity:
            flash('Stock físico insuficiente o equipo inválido. Intenta más tarde.', 'warning')
            return redirect(url_for('main.premium_dashboard'))

        try:
            success, reserved_ids, msg = InventoryService.reserve_instances(laptop_item.id, quantity)
            if not success:
                flash(msg, 'danger')
                return redirect(url_for('main.premium_dashboard'))
                
            for inst_id in reserved_ids:
                LoanService.create_loan(user_id=current_user.id, instance_id=inst_id, environment=environment)
                
            db.session.commit()
            flash('Solicitud de portátil enviada correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al enviar la solicitud.', 'danger')
            
        return redirect(url_for('main.premium_dashboard'))
    return render_template('premium/request_laptop.html', items=available_computers)

@bp.route('/request/accessory', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_accessory():
    active_accessories_count = Loan.query.join(ItemInstance).join(Catalog).filter(
        Loan.user_id == current_user.id,
        Catalog.category != 'computo',
        Catalog.category != 'libro',
        Loan.status.in_(['pendiente', 'activo', 'atrasado'])
    ).count()

    if active_accessories_count >= 2:
        flash('Has alcanzado el límite de 2 accesorios simultáneos.', 'warning')
        return redirect(url_for('main.index'))
    
    available_items = Catalog.query.filter_by(category='general').all() if current_user.role == 'cliente' else Catalog.query.all()

    if request.method == 'POST':
        catalog_id = request.form.get('catalog_id')
        quantity = int(request.form.get('quantity'))
        
        if quantity <= 0:
            flash('Cantidad debe ser mayor a cero.', 'danger')
            return redirect(url_for('main.request_accessory'))
            
        catalog_item = Catalog.query.get(catalog_id)
        
        if not catalog_item or catalog_item.available_count < quantity:
            flash('Stock físico insuficiente o ítem inválido.', 'danger')
            return redirect(url_for('main.request_accessory'))

        try:
            success, reserved_ids, msg = InventoryService.reserve_instances(catalog_item.id, quantity)
            if not success:
                flash(msg, 'danger')
                return redirect(url_for('main.request_accessory'))
                
            for inst_id in reserved_ids:
                LoanService.create_loan(user_id=current_user.id, instance_id=inst_id)
                
            db.session.commit()
            flash(f'Solicitud de {catalog_item.title_or_name} realizada.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al procesar la solicitud.', 'danger')
            
        return redirect(url_for('main.premium_dashboard'))
    return render_template('premium/request_accessory.html', items=available_items)

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

@bp.route('/visit', methods=['GET', 'POST'])
def register_visit():
    if request.method == 'POST':
        document_id = request.form.get('document_id')
        activity = request.form.get('activity')
        manual_name = request.form.get('visitor_name')
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
    