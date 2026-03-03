from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app import db
from app.models import Loan, User, Catalog, ItemInstance
from datetime import datetime
from sqlalchemy import or_
from functools import wraps
from sqlalchemy import func
from app.services.loan_service import LoanService
from app.services.inventory_service import InventoryService
from app.utils.decorators import role_required
from app.forms import AdminUserForm, ImportForm

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
        users = User.query.order_by(User.full_name).limit(50).all()

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

@bp.route('/users/bulk_import', methods=['POST'])
@role_required('admin')
def bulk_import():
    import_form = ImportForm()
    if import_form.validate_on_submit():
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
    
    top_items = db.session.query(
        Catalog.title_or_name, 
        func.count(Loan.id).label('total')
    ).join(ItemInstance).join(Loan).group_by(Catalog.title_or_name).order_by(func.count(Loan.id).desc()).limit(5).all()

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
    success, msg = LoanService.approve_loan(id)
    
    if success:
        flash(msg, 'success')
        return redirect(url_for('admin.admin_dashboard', status='activo'))
    else:
        flash(msg, 'danger')
        return redirect(url_for('admin.admin_dashboard', status='pendiente'))

@bp.route('/loan/<int:loan_id>/return', methods=['POST'])
@role_required('admin', 'bibliotecario')
def return_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    
    if loan.status != 'devuelto':
        # 1. Congelamos la multa actual para el historial
        loan.final_penalty = loan.penalty_fee
        loan.status = 'devuelto'
        loan.return_date = datetime.utcnow()
        
        # 2. LIBERAMOS LA INSTANCIA FÍSICA USANDO EL SERVICIO TRANSSACIONAL
        success, msg = InventoryService.release_instance(loan.instance_id)
        
        if success:
            db.session.commit()
            flash('Ítem devuelto y reingresado al inventario con éxito.', 'success')
        else:
            db.session.rollback()
            flash(f'Error al liberar inventario: {msg}', 'danger')
            
    return redirect(request.referrer or url_for('admin.dashboard'))

@bp.route('/reject/<int:id>', methods=['POST'])
@role_required('bibliotecario')
def reject_loan(id):
    loan = Loan.query.get_or_404(id)
    if loan.status == 'pendiente':
        loan.status = 'rechazado'
        loan.observation = 'Rechazado por el bibliotecario.' 
        
        if loan.item_instance:
            loan.item_instance.status = 'disponible'

        db.session.commit()
        flash('Solicitud rechazada con éxito. Se liberó la reserva física de la biblioteca.', 'success')
    else:
        flash('Solo puedes rechazar solicitudes que estén pendientes.', 'warning')
    return redirect(url_for('admin.admin_dashboard', status='pendiente'))

# --- RUTAS DE GESTIÓN DE CATÁLOGO E INSTANCIAS (RESTUARADAS) ---

@bp.route('/catalog', methods=['GET', 'POST'])
@role_required('bibliotecario', 'admin')
def catalog_manage():
    if request.method == 'POST':
        title = request.form.get('title_or_name')
        category = request.form.get('category')
        author = request.form.get('author_or_brand')

        new_catalog_item = Catalog(title_or_name=title, category=category, author_or_brand=author)
        db.session.add(new_catalog_item)
        db.session.commit()
        flash(f'Elemento de catálogo "{title}" creado con éxito.', 'success')
        return redirect(url_for('admin.catalog_manage'))

    search_query = request.args.get('search', '')
    query = Catalog.query
    if search_query:
        query = query.filter(
            or_(
                Catalog.title_or_name.ilike(f'%{search_query}%'),
                Catalog.category.ilike(f'%{search_query}%')
            )
        )
    
    items = query.order_by(Catalog.title_or_name).all()
    return render_template('admin/catalog.html', items=items, search_query=search_query)

@bp.route('/catalog/delete/<int:id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def catalog_delete(id):
    item = Catalog.query.get_or_404(id)
    if item.total_count > 0:
        flash('No puedes eliminar un catálogo que tiene instancias físicas registradas.', 'danger')
    else:
        db.session.delete(item)
        db.session.commit()
        flash('Elemento de catálogo eliminado.', 'success')
    return redirect(url_for('admin.catalog_manage'))

@bp.route('/catalog/<int:catalog_id>/instances', methods=['GET', 'POST'])
@role_required('bibliotecario', 'admin')
def manage_instances(catalog_id):
    catalog_item = Catalog.query.get_or_404(catalog_id)

    if request.method == 'POST':
        unique_code = request.form.get('unique_code').strip()
        condition = request.form.get('condition')
        
        if ItemInstance.query.filter_by(unique_code=unique_code).first():
            flash(f'El código/serial "{unique_code}" ya está registrado en el sistema.', 'danger')
        else:
            new_instance = ItemInstance(
                catalog_id=catalog_id,
                unique_code=unique_code,
                condition=condition,
                status='disponible'
            )
            db.session.add(new_instance)
            db.session.commit()
            flash(f'Instancia "{unique_code}" agregada correctamente a {catalog_item.title_or_name}.', 'success')
            
        return redirect(url_for('admin.manage_instances', catalog_id=catalog_id))

    instances = catalog_item.instances.all()
    return render_template('admin/instances.html', catalog_item=catalog_item, instances=instances)

@bp.route('/instance/update_status/<int:instance_id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def update_instance_status(instance_id):
    instance = ItemInstance.query.get_or_404(instance_id)
    new_status = request.form.get('status')
    
    if new_status in ['disponible', 'mantenimiento', 'perdido']:
        instance.status = new_status
        db.session.commit()
        flash(f'Estado de la instancia {instance.unique_code} actualizado a {new_status}.', 'success')
    else:
        flash('Estado no válido.', 'danger')
        
    return redirect(url_for('admin.manage_instances', catalog_id=instance.catalog_id))

@bp.route('/instance/delete/<int:instance_id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def instance_delete(instance_id):
    instance = ItemInstance.query.get_or_404(instance_id)
    catalog_id = instance.catalog_id
    
    if instance.loans.filter(Loan.status.in_(['pendiente', 'activo', 'atrasado'])).first():
        flash('No puedes eliminar una instancia que se encuentra en un proceso de préstamo activo.', 'danger')
    else:
        db.session.delete(instance)
        db.session.commit()
        flash(f'Instancia {instance.unique_code} eliminada del sistema.', 'success')
        
    return redirect(url_for('admin.manage_instances', catalog_id=catalog_id))