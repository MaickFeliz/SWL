from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app import db
from app.models import Loan, User, Inventory
from datetime import datetime
from sqlalchemy import or_

@bp.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'bibliotecario':
        return redirect(url_for('main.instructor_dashboard'))

    # Búsqueda simple
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
@login_required
def edit_user(id):
    if current_user.role != 'bibliotecario':
        return redirect(url_for('main.instructor_dashboard'))
    
    user = User.query.get_or_404(id)
    user.full_name = request.form.get('full_name')
    user.phone = request.form.get('phone')
    user.role = request.form.get('role')
    user.ficha = request.form.get('ficha')
    
    db.session.commit()
    flash(f'Usuario {user.full_name} actualizado.', 'success')
    return redirect(url_for('admin.manage_users'))

@bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'bibliotecario':
        return redirect(url_for('main.instructor_dashboard'))
    
    status_filter = request.args.get('status', 'pendiente')
    
    query = Loan.query.filter(Loan.status == status_filter)

    loans = query.order_by(Loan.request_date.desc()).all()
    
    return render_template('admin/dashboard.html', loans=loans, current_status=status_filter)

@bp.route('/approve/<int:id>', methods=['POST'])
@login_required
def approve(id):
    loan = Loan.query.get_or_404(id)
    # En el formulario HTML el input debe llamarse 'serial' o 'item_code'
    serial = request.form.get('serial')
    
    if not serial:
        flash('Falta el serial o código del elemento', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
        
    # CORRECCIÓN: Guardar en item_code
    loan.item_code = serial
    loan.status = 'aprobado'
    loan.approval_date = datetime.utcnow()
    db.session.commit()
    
    flash('Préstamo aprobado correctamente', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/return/<int:id>')
@login_required
def return_item(id):
    loan = Loan.query.get_or_404(id)
    
    # Evitar devolver algo que ya estaba devuelto (para no duplicar inventario)
    if loan.status == 'devuelto':
        flash('Este elemento ya había sido devuelto.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    loan.status = 'devuelto'
    loan.return_date = datetime.utcnow()
    
    # LOGICA DE RESTOCK (Solo para elementos de inventario)
    if loan.loan_type == 'elemento':
        # Buscar el item en el inventario por nombre
        inventory_item = Inventory.query.filter_by(name=loan.item_name).first()
        if inventory_item:
            inventory_item.available_quantity += loan.quantity
            flash(f'Elemento devuelto y stock restaurado (+{loan.quantity}).', 'info')
    else:
        flash('Equipo de cómputo devuelto.', 'info')

    db.session.commit()

    return redirect(url_for('admin.admin_dashboard', status='aprobado'))

# GESTIÓN DE INVENTARIO
@bp.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory_manage():
    if current_user.role != 'bibliotecario':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('main.instructor_dashboard'))

    # AGREGAR NUEVO ITEM
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        quantity = int(request.form.get('quantity'))

        # Validar si ya existe
        if Inventory.query.filter_by(name=name).first():
            flash('El elemento ya existe en el inventario.', 'warning')
        else:
            new_item = Inventory(
                name=name, 
                category=category, 
                total_quantity=quantity, 
                available_quantity=quantity
            )
            db.session.add(new_item)
            db.session.commit()
            flash('Elemento creado exitosamente.', 'success')
        return redirect(url_for('admin.inventory_manage'))

    items = Inventory.query.all()
    return render_template('admin/inventory.html', items=items)

@bp.route('/inventory/update/<int:id>', methods=['POST'])
@login_required
def inventory_update(id):
    if current_user.role != 'bibliotecario':
        return redirect(url_for('main.instructor_dashboard'))
        
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
@login_required
def inventory_delete(id):
    if current_user.role != 'bibliotecario':
        return redirect(url_for('main.instructor_dashboard'))
        
    item = Inventory.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Elemento eliminado del sistema.', 'info')
    return redirect(url_for('admin.inventory_manage'))

@bp.route('/inventory/edit_details/<int:id>', methods=['POST'])
@login_required
def inventory_edit_details(id):
    if current_user.role != 'bibliotecario':
        return redirect(url_for('main.instructor_dashboard'))
        
    item = Inventory.query.get_or_404(id)
    item.name = request.form.get('name')
    item.category = request.form.get('category')
    
    db.session.commit()
    flash(f'Detalles de "{item.name}" actualizados.', 'success')
    return redirect(url_for('admin.inventory_manage'))