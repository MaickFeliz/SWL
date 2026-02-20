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

from app.services.loan_service import LoanService
from app.services.inventory_service import InventoryService
from app.utils.decorators import role_required

# app/admin/routes.py
@bp.route('/users')
@role_required('admin')
def manage_users():
    # Obtener el número de página de la URL, por defecto la página 1
    page = request.args.get('page', 1, type=int)
    # Paginar a 10 usuarios por vista
    users_pagination = User.query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template('admin/users.html', users=users_pagination)

@bp.route('/users/search')
@role_required('admin', 'bibliotecario')
def search_users():
    search = request.args.get('search')
    if search:
        users = User.query.filter(or_(
            User.full_name.ilike(f'%{search}%'),
            User.document_id.ilike(f'%{search}%')
        )).all()
    else:
        users = User.query.order_by(User.full_name).limit(50).all() # Limitamos a 50 para no saturar

    return render_template('admin/users.html', users=users)

@bp.route('/users/edit/<int:id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def edit_user(id):
    user = User.query.get_or_404(id)
    user.full_name = request.form.get('full_name')
    user.phone = request.form.get('phone')
    user.role = request.form.get('role')
    
    db.session.commit()
    flash(f'Usuario {user.full_name} actualizado.', 'success')
    return redirect(url_for('admin.manage_users'))

@bp.route('/dashboard')
@role_required('bibliotecario', 'admin')
def admin_dashboard():
    status_filter = request.args.get('status', 'pendiente')
    
    pending_count = Loan.query.filter_by(status='pendiente').count()
    activo_count = Loan.query.filter_by(status='activo').count()
    returned_count = Loan.query.filter_by(status='devuelto').count()
    atrasado_count = Loan.query.filter_by(status='atrasado').count()
    
    # Items más solicitados (agrupando por nombre en Python o SQL simplificado)
    from sqlalchemy import func
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
@role_required('bibliotecario', 'admin')
def approve(id):
    serial = request.form.get('serial')
    if not serial:
        flash('Falta el serial o código del elemento', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
        
    loan = Loan.query.get_or_404(id)
    
    # Restar inventario si es un elemento
    if loan.loan_type == 'elemento':
        success, msg = InventoryService.deduct_stock(loan.item_name, loan.quantity)
        if not success:
            flash(msg, 'danger')
            return redirect(url_for('admin.admin_dashboard'))

    LoanService.approve_loan(id, serial)
    flash('Préstamo aprobado correctamente', 'success')
    return redirect(url_for('admin.admin_dashboard', status='activo'))

@bp.route('/return/<int:id>')
@role_required('bibliotecario', 'admin')
def return_item(id):
    loan = Loan.query.get_or_404(id)
    
    # LOGICA DE RESTOCK
    if loan.loan_type == 'elemento' and loan.status != 'devuelto':
        InventoryService.add_stock(loan.item_name, loan.quantity)

    success, msg = LoanService.return_loan(id)
    
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'warning')

    return redirect(url_for('admin.admin_dashboard', status='devuelto'))

# GESTIÓN DE INVENTARIO
@bp.route('/inventory', methods=['GET', 'POST'])
@role_required('bibliotecario', 'admin')
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

    items = Inventory.query.all()
    return render_template('admin/inventory.html', items=items)

@bp.route('/inventory/update/<int:id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
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
@role_required('admin')
def inventory_delete(id):
    item = Inventory.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Elemento eliminado del sistema.', 'info')
    return redirect(url_for('admin.inventory_manage'))

@bp.route('/inventory/edit_details/<int:id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def inventory_edit_details(id):
    item = Inventory.query.get_or_404(id)
    item.name = request.form.get('name')
    item.category = request.form.get('category')
    
    db.session.commit()
    flash(f'Detalles de "{item.name}" actualizados.', 'success')
    return redirect(url_for('admin.inventory_manage'))