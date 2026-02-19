from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.main import bp
from app import db
from app.models import Loan, Inventory, User, LibraryLog # <--- IMPORTANTE: LibraryLog AÑADIDO
from datetime import datetime

@bp.route('/fast-loan', methods=['GET', 'POST'])
def fast_loan():
    # Paso 1: Buscar usuario
    if request.method == 'POST' and 'search_doc' in request.form:
        doc = request.form.get('document_id')
        user = User.query.filter_by(document_id=doc).first()
        if not user:
            flash('Usuario no encontrado. Debe registrarse primero.', 'danger')
            return redirect(url_for('main.fast_loan'))
        
        # Cargar inventario para el paso 2
        items = Inventory.query.all()
        return render_template('main/fast_loan.html', user=user, items=items)

    # Paso 2: Procesar el préstamo
    if request.method == 'POST' and 'confirm_loan' in request.form:
        user_id = request.form.get('user_id')
        item_type = request.form.get('item_type') # 'computo' o 'elemento'
        
        # Datos del formulario
        user = User.query.get(user_id)
        
        if item_type == 'computo':
            # Lógica Portátil
            environment = request.form.get('environment')
            new_loan = Loan(user_id=user.id, loan_type='computo', item_name='Computador Portátil', 
                          quantity=1, environment=environment, associated_ficha=user.ficha, status='pendiente')
        
        elif item_type == 'elemento':
            # Lógica Elemento
            item_inventory_id = request.form.get('inventory_id')
            qty = int(request.form.get('quantity'))
            inv_item = Inventory.query.get(item_inventory_id)
            
            # Validación de categoría rápida
            if user.role == 'aprendiz' and inv_item.category == 'instructor':
                flash(f'🚫 El usuario es Aprendiz y no puede pedir {inv_item.name}.', 'danger')
                return redirect(url_for('main.fast_loan'))

            if inv_item.available_quantity < qty:
                flash('🚫 Stock insuficiente.', 'danger')
                return redirect(url_for('main.fast_loan'))

            inv_item.available_quantity -= qty
            new_loan = Loan(user_id=user.id, loan_type='elemento', item_name=inv_item.name, 
                          quantity=qty, status='pendiente')
        
        db.session.add(new_loan)
        db.session.commit()
        flash(f'✅ Solicitud creada para {user.full_name}. Pendiente de aprobación.', 'success')
        return redirect(url_for('main.fast_loan'))

    return render_template('main/fast_loan.html')

@bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'bibliotecario':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('main.instructor_dashboard'))
    return render_template('main/index.html')

@bp.route('/dashboard')
@login_required
def instructor_dashboard():
    # Consulta los préstamos del usuario actual (tu plantilla los está esperando en el ciclo for)
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.request_date.desc()).all()
    
    return render_template('instructor/dashboard.html', loans=loans)

@bp.route('/request/laptop', methods=['GET', 'POST'])
@login_required
def request_laptop():
    if request.method == 'POST':
        environment = request.form.get('environment')
        if current_user.role == 'instructor':
            quantity = int(request.form.get('quantity'))
            associated_ficha = request.form.get('associated_ficha')
        else:
            quantity = 1
            associated_ficha = current_user.ficha

        active_loans_query = Loan.query.filter(
            Loan.user_id == current_user.id,
            Loan.status.in_(['pendiente', 'aprobado']),
            Loan.loan_type == 'computo'
        )

        if current_user.role == 'aprendiz' and active_loans_query.first():
            flash('Ya tienes un equipo pendiente o en uso.', 'warning')
            return redirect(url_for('main.instructor_dashboard'))
        elif current_user.role == 'instructor':
            if active_loans_query.filter_by(associated_ficha=associated_ficha).first():
                flash(f'Ya tienes equipos pedidos para la ficha {associated_ficha}.', 'warning')
                return redirect(url_for('main.instructor_dashboard'))

        new_loan = Loan(
            user_id=current_user.id,
            loan_type='computo',           
            item_name='Computador Portátil',
            quantity=quantity,
            environment=environment,
            associated_ficha=associated_ficha,
            status='pendiente'
        )
        db.session.add(new_loan)
        db.session.commit()
        flash('Solicitud de portátil enviada.', 'success')
        return redirect(url_for('main.instructor_dashboard'))
    return render_template('instructor/request_laptop.html')

# --- ACCESORIOS (MOUSE/VIDEOBEAM) ---
@bp.route('/request/accessory', methods=['GET', 'POST'])
@login_required
def request_accessory():
    if current_user.role == 'aprendiz':
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

        new_loan = Loan(
            user_id=current_user.id,
            loan_type='elemento',
            item_name=inventory_item.name,
            quantity=quantity,
            status='pendiente'
        )
        inventory_item.available_quantity -= quantity
        db.session.add(new_loan)
        db.session.commit()
        flash(f'Solicitud de {inventory_item.name} realizada.', 'success')
        return redirect(url_for('main.instructor_dashboard'))
    return render_template('instructor/request_accessory.html', items=available_items)

@bp.route('/request/book', methods=['GET', 'POST'])
@login_required
def request_book():
    if request.method == 'POST':
        title = request.form.get('book_title')
        code = request.form.get('book_code')
        
        new_loan = Loan(
            user_id=current_user.id,
            loan_type='libro',
            item_name=title,
            item_code=code,
            quantity=1,
            status='pendiente'
        )
        db.session.add(new_loan)
        db.session.commit()
        flash('📖 Solicitud de libro registrada. Acércate al mostrador.', 'success')
        return redirect(url_for('main.instructor_dashboard'))
    return render_template('instructor/request_book.html')

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