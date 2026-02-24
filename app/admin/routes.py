from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app import db
from app.models import Loan, User, Inventory
from app import db
from app.models import Loan, User, Inventory
from datetime import datetime
from sqlalchemy import or_
from functools import wraps
from sqlalchemy import func
from app.services.loan_service import LoanService
from app.services.inventory_service import InventoryService
from app.utils.decorators import role_required
from app.forms import AdminUserForm, ImportForm
import pandas as pd
from werkzeug.utils import secure_filename

# app/admin/routes.py
@bp.route('/users')
@role_required('admin')
def manage_users():
    page = request.args.get('page', 1, type=int)
    users_pagination = User.query.paginate(page=page, per_page=10, error_out=False)
    
    form = AdminUserForm()
    import_form = ImportForm()
    return render_template('admin/users.html', users=users_pagination, form=form, import_form=import_form)

@bp.route('/users/search')
@role_required('admin')
def search_users():
    search = request.args.get('search')
    if search:
        users = User.query.filter(or_(
            User.full_name.ilike(f'%{search}%'),
            User.document_id.ilike(f'%{search}%')
        )).all()
    else:
        users = User.query.order_by(User.full_name).limit(50).all() # Limitamos a 50 para no saturar

    form = AdminUserForm()
    import_form = ImportForm()
    return render_template('admin/users.html', users=users, form=form, import_form=import_form)

@bp.route('/users/create', methods=['POST'])
@role_required('admin')
def create_user():
    form = AdminUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(document_id=form.document_id.data).first() or \
           User.query.filter_by(email=form.email.data).first():
            flash('El documento o correo ya está registrado.', 'warning')
            return redirect(url_for('admin.manage_users'))

        user = User(
            username=form.email.data,
            full_name=form.full_name.data,
            document_id=form.document_id.data,
            email=form.email.data,
            phone=form.phone.data,
            role=form.role.data,
            program_name=form.program_name.data if form.role.data == 'cliente' else None
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuario creado con éxito.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error ({field}): {error}", 'danger')
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/edit/<int:id>', methods=['POST'])
@role_required('admin')
def edit_user(id):
    user = User.query.get_or_404(id)
    user.full_name = request.form.get('full_name')
    user.phone = request.form.get('phone')
    user.role = request.form.get('role')
    
    db.session.commit()
    flash(f'Usuario {user.full_name} actualizado.', 'success')
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_user(id):
    if id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('admin.manage_users'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {user.full_name} eliminado.', 'success')
    return redirect(url_for('admin.manage_users'))

@bp.route('/dashboard')
@role_required('bibliotecario', 'admin')
def admin_dashboard():
    LoanService.check_overdue_loans()
    
    status_filter = request.args.get('status', 'pendiente')
    
    pending_count = Loan.query.filter_by(status='pendiente').count()
    activo_count = Loan.query.filter_by(status='activo').count()
    returned_count = Loan.query.filter_by(status='devuelto').count()
    atrasado_count = Loan.query.filter_by(status='atrasado').count()
    
    top_items = db.session.query(Loan.item_name, func.count(Loan.id).label('total')).group_by(Loan.item_name).order_by(func.count(Loan.id).desc()).limit(5).all()

    query = Loan.query.filter(Loan.status == status_filter)

    loans = query.order_by(Loan.request_date.desc()).all()
    
    stats = {
        'pending': pending_count,
        'activo': activo_count,
        'returned': returned_count,
        'atrasado': atrasado_count
    }
    
    return render_template('admin/dashboard.html', loans=loans, current_status=status_filter, stats=stats, top_items=top_items)

@bp.route('/approve/<int:id>', methods=['POST'])
@role_required('bibliotecario')
def approve(id):
    serial = request.form.get('serial')
    loan = Loan.query.get_or_404(id)
    
    # CORRECCIÓN: Solo exigir serial obligatoriamente si es equipo o libro
    if loan.loan_type in ['computo', 'libro'] and not serial:
        flash('Falta el serial o código del elemento', 'danger')
        return redirect(url_for('admin.admin_dashboard', status='pendiente'))
        
    # Restar inventario si es un elemento
    if loan.loan_type == 'elemento':
        success, msg = InventoryService.deduct_stock(loan.item_name, loan.quantity)
        if not success:
            flash(msg, 'danger')
            return redirect(url_for('admin.admin_dashboard', status='pendiente'))

    success, msg = LoanService.approve_loan(id, serial)
    
    if success:
        flash(msg, 'success')
        return redirect(url_for('admin.admin_dashboard', status='activo'))
    else:
        flash(msg, 'danger')
        return redirect(url_for('admin.admin_dashboard', status='pendiente'))

@bp.route('/return/<int:id>')
@role_required('bibliotecario')
def return_item(id):
    loan = Loan.query.get_or_404(id)
    
    if loan.loan_type == 'elemento' and loan.status != 'devuelto':
        InventoryService.add_stock(loan.item_name, loan.quantity)

    success, msg = LoanService.return_loan(id)
    
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'warning')

    return redirect(url_for('admin.admin_dashboard', status='devuelto'))

@bp.route('/reject/<int:id>', methods=['POST'])
@role_required('bibliotecario')
def reject_loan(id):
    loan = Loan.query.get_or_404(id)
    if loan.status == 'pendiente':
        loan.status = 'rechazado'
        loan.observation = 'Rechazado por el bibliotecario.' 
        db.session.commit()
        flash('Solicitud rechazada con éxito. A otra cosa.', 'success')
    else:
        flash('Solo puedes rechazar solicitudes que estén pendientes.', 'warning')
    return redirect(url_for('admin.admin_dashboard', status='pendiente'))

@bp.route('/inventory', methods=['GET', 'POST'])
@role_required('bibliotecario')
def inventory_manage():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        quantity = int(request.form.get('quantity'))

        success, msg = InventoryService.create_item(name, category, quantity)
        
        if success:
            flash(msg, 'success')
        else:
            flash(msg, 'warning')
            
        return redirect(url_for('admin.inventory_manage'))

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')

    query = Inventory.query
    if search_query:
        query = query.filter(
            or_(
                Inventory.name.ilike(f'%{search_query}%'),
                Inventory.category.ilike(f'%{search_query}%')
            )
        )
    
    paginated_inventory = query.paginate(page=page, per_page=10, error_out=False)

    import_form = ImportForm()
    return render_template('admin/inventory.html', 
                           items=paginated_inventory.items, 
                           pagination=paginated_inventory,
                           search_query=search_query,
                           import_form=import_form)

@bp.route('/inventory/update/<int:id>', methods=['POST'])
@role_required('bibliotecario')
def inventory_update(id):
    item = Inventory.query.get_or_404(id)
    action = request.form.get('action') # 'add' o 'remove'
    amount = int(request.form.get('amount'))

    if action == 'add':
        item.total_quantity += amount
        item.available_quantity += amount
        flash(f'Se agregaron {amount} unidades a {item.name}.', 'success')
    elif action == 'remove':
        # No dejar bajar de 0
        if item.available_quantity >= amount:
            item.total_quantity -= amount
            item.available_quantity -= amount
            flash(f'Se eliminaron {amount} unidades de {item.name}.', 'warning')
        else:
            flash('No puedes eliminar más de lo que hay disponible.', 'danger')

    db.session.commit()
    return redirect(url_for('admin.inventory_manage'))

@bp.route('/inventory/delete/<int:id>')
@role_required('bibliotecario')
def inventory_delete(id):
    item = Inventory.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Elemento eliminado del sistema.', 'info')
    return redirect(url_for('admin.inventory_manage'))

@bp.route('/inventory/edit_details/<int:id>', methods=['POST'])
@role_required('bibliotecario')
def inventory_edit_details(id):
    item = Inventory.query.get_or_404(id)
    item.name = request.form.get('name')
    item.category = request.form.get('category')
    
    db.session.commit()
    flash(f'Detalles de "{item.name}" actualizados.', 'success')
    return redirect(url_for('admin.inventory_manage'))

@bp.route('/import', methods=['POST'])
@role_required('admin')
def bulk_import():
    form = ImportForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1].lower()
        source_type = request.form.get('import_type', 'users')
        
        try:
            if ext == 'csv':
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
                
            added = 0
            if source_type == 'users':
                for _, row in df.iterrows():
                    doc = str(row.get('document_id', '')).strip()
                    email = str(row.get('email', '')).strip()
                    if not doc or not email or doc == 'nan' or email == 'nan':
                        continue
                        
                    # Verificar si existe en DB
                    if User.query.filter((User.document_id == doc) | (User.email == email)).first():
                        continue
                        
                    user = User(
                        username=email,
                        full_name=str(row.get('full_name', '')),
                        document_id=doc,
                        email=email,
                        phone=str(row.get('phone', '')),
                        role=str(row.get('role', 'cliente')).lower(),
                        program_name=str(row.get('program_name', '')) if 'program_name' in row else None
                    )
                    user.set_password(str(row.get('password', '12345678')))
                    db.session.add(user)
                    added += 1
            elif source_type == 'inventory':
                for _, row in df.iterrows():
                    name = str(row.get('name', '')).strip()
                    if not name or name == 'nan':
                        continue
                    if Inventory.query.filter_by(name=name).first():
                        continue
                    qty = int(row.get('total_quantity', 1) if not pd.isna(row.get('total_quantity')) else 1)
                    item = Inventory(
                        name=name,
                        total_quantity=qty,
                        available_quantity=qty,
                        category=str(row.get('category', 'general')).lower()
                    )
                    db.session.add(item)
                    added += 1
            
            db.session.commit()
            flash(f'Importación masiva completada: {added} nuevos registros agregados.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al procesar el archivo: revise el formato de las columnas. {str(e)}', 'danger')
    else:
        flash('Seleccione un archivo CSV o Excel válido.', 'danger')
        
    return redirect(request.referrer or url_for('admin.admin_dashboard'))