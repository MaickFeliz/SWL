from flask import render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app.admin import bp
from app import db
from app.models import Loan, User, Catalog, ItemInstance, LoanStatus, InventoryStatus
from datetime import datetime, timezone
from sqlalchemy import or_
from functools import wraps
from sqlalchemy import func
from app.services.loan_service import LoanService
from app.services.inventory_service import InventoryService
from app.services.report_service import ReportService, EXCEL_MIME_TYPE
from app.utils.decorators import role_required
from app.forms import AdminUserForm, EditUserForm, ImportForm, CatalogForm, InstanceForm, UpdateInstanceStatusForm

@bp.route('/users')
@role_required('admin')
def manage_users():
    page = request.args.get('page', 1, type=int)
    users_pagination = User.query.paginate(page=page, per_page=10, error_out=False)
    
    form = AdminUserForm()
    import_form = ImportForm()
    edit_forms = {u.id: EditUserForm(obj=u) for u in users_pagination.items}
    return render_template(
        'admin/users.html',
        users=users_pagination,
        form=form,
        import_form=import_form,
        edit_forms=edit_forms,
    )

@bp.route('/users/search')
@role_required('admin')
def search_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search')
    query = User.query
    if search:
        query = query.filter(
            or_(
                User.full_name.ilike(f'%{search}%'),
                User.document_id.ilike(f'%{search}%'),
            )
        )
    users_pagination = query.order_by(User.full_name).paginate(page=page, per_page=10, error_out=False)

    form = AdminUserForm()
    import_form = ImportForm()
    edit_forms = {u.id: EditUserForm(obj=u) for u in users_pagination.items}
    return render_template(
        'admin/users.html',
        users=users_pagination,
        form=form,
        import_form=import_form,
        edit_forms=edit_forms,
    )

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
                flash(f"Error ({getattr(form, field).label.text}): {error}", 'danger')
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
    form = EditUserForm()

    if form.validate_on_submit():
        user.full_name = form.full_name.data
        user.phone = form.phone.data
        user.role = form.role.data
        user.program_name = form.program_name.data if form.role.data == 'cliente' else None

        if form.password.data:
            user.set_password(form.password.data)

        try:
            db.session.commit()
            flash(f'Usuario {user.full_name} actualizado.', 'success')
        except Exception:
            db.session.rollback()
            flash('Ocurrió un error al actualizar el usuario.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error ({getattr(form, field).label.text}): {error}", 'danger')

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
    status_filter = request.args.get('status', LoanStatus.PENDING.value)
    page = request.args.get('page', 1, type=int)

    pending_count = Loan.query.filter_by(status=LoanStatus.PENDING).count()
    activo_count = Loan.query.filter_by(status=LoanStatus.ACTIVE).count()
    returned_count = Loan.query.filter_by(status=LoanStatus.RETURNED).count()
    atrasado_count = Loan.query.filter_by(status=LoanStatus.OVERDUE).count()

    top_items = db.session.query(
        Catalog.title_or_name,
        func.count(Loan.id).label('total')
    ).select_from(Catalog).join(ItemInstance).join(Loan).group_by(Catalog.title_or_name).order_by(func.count(Loan.id).desc()).limit(5).all()
    
    try:
        query = Loan.query.filter(Loan.status == LoanStatus(status_filter))
    except ValueError:
        query = Loan.query.filter(Loan.status == LoanStatus.PENDING)
        
    loans_pagination = query.order_by(Loan.request_date.desc()).paginate(page=page, per_page=20, error_out=False)

    stats = {
        'pending': pending_count,
        'activo': activo_count,
        'returned': returned_count,
        'atrasado': atrasado_count
    }

    return render_template('admin/dashboard.html', loans_pagination=loans_pagination, current_status=status_filter, stats=stats, top_items=top_items)

@bp.route('/approve/<int:id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def approve(id):
    success, msg = LoanService.approve_loan(id)
    if success:
        flash(msg, 'success')
        return redirect(url_for('admin.admin_dashboard', status=LoanStatus.ACTIVE.value))
    flash(msg, 'danger')
    return redirect(url_for('admin.admin_dashboard', status=LoanStatus.PENDING.value))

@bp.route('/reports/overdue/export')
@role_required('admin')
def export_overdue_report():
    output = ReportService.generate_overdue_users_report()
    filename = f"usuarios_morosos_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=EXCEL_MIME_TYPE,
        max_age=0,
    )

@bp.route('/reports/inventory/export')
@role_required('admin')
def export_inventory_report():
    output = ReportService.generate_inventory_status_report()
    filename = f"inventario_actual_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype=EXCEL_MIME_TYPE,
        max_age=0,
    )

@bp.route('/loan/<int:loan_id>/return', methods=['POST'])
@role_required('admin', 'bibliotecario')
def return_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.status != LoanStatus.RETURNED:
        loan.final_penalty = loan.penalty_fee
        loan.status = LoanStatus.RETURNED
        loan.return_date = datetime.now(timezone.utc)
        success, msg = InventoryService.release_instance(loan.instance_id)
        if success:
            db.session.commit()
            flash('Ítem devuelto y reingresado al inventario con éxito.', 'success')
        else:
            db.session.rollback()
            flash(f'Error al liberar inventario: {msg}', 'danger')
    return redirect(request.referrer or url_for('admin.admin_dashboard'))

@bp.route('/reject/<int:id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def reject_loan(id):
    loan = Loan.query.get_or_404(id)
    if loan.status is LoanStatus.PENDING:
        loan.status = LoanStatus.REJECTED
        loan.observation = 'Rechazado por el bibliotecario.' 
        if loan.item_instance:
            loan.item_instance.status = InventoryStatus.AVAILABLE
        db.session.commit()
        flash('Solicitud rechazada con éxito.', 'success')
    else:
        flash('Solo puedes rechazar solicitudes que estén pendientes.', 'warning')
    return redirect(url_for('admin.admin_dashboard', status=LoanStatus.PENDING.value))

@bp.route('/catalog', methods=['GET', 'POST'])
@role_required('bibliotecario', 'admin')
def catalog_manage():
    form = CatalogForm()
    if form.validate_on_submit():
        new_catalog_item = Catalog(
            title_or_name=form.title_or_name.data,
            category=form.category.data,
            author_or_brand=form.author_or_brand.data
        )
        db.session.add(new_catalog_item)
        db.session.commit()
        flash(f'Elemento de catálogo "{form.title_or_name.data}" creado con éxito.', 'success')
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
    return render_template('admin/catalog.html', items=items, search_query=search_query, form=form)

@bp.route('/catalog/delete/<int:id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def catalog_delete(id):
    item = Catalog.query.get_or_404(id)
    if item.instances.count() > 0:
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
    form = InstanceForm()
    status_forms = {inst.id: UpdateInstanceStatusForm(status=inst.status) for inst in catalog_item.instances.all()}

    if form.validate_on_submit():
        unique_code = form.unique_code.data.strip()
        condition = form.condition.data
        status = form.status.data

        if ItemInstance.query.filter_by(unique_code=unique_code).first():
            flash(f'El código "{unique_code}" ya está registrado.', 'danger')
        else:
            new_instance = ItemInstance(
                catalog_id=catalog_id,
                unique_code=unique_code,
                condition=condition,
                status=InventoryStatus(status),
            )
            try:
                db.session.add(new_instance)
                db.session.commit()
                flash(f'Instancia agregada correctamente.', 'success')
            except Exception:
                db.session.rollback()
                flash('Error en la base de datos al guardar.', 'danger')
        return redirect(url_for('admin.manage_instances', catalog_id=catalog_id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error ({getattr(form, field).label.text}): {error}", 'danger')

    instances = catalog_item.instances.all()
    return render_template(
        'admin/instances.html',
        catalog_item=catalog_item,
        instances=instances,
        form=form,
        status_forms=status_forms,
    )

@bp.route('/instance/update_status/<int:instance_id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def update_instance_status(instance_id):
    instance = ItemInstance.query.get_or_404(instance_id)
    form = UpdateInstanceStatusForm()

    if form.validate_on_submit():
        new_status_value = form.status.data
        valid_status_values = {status.value for status in InventoryStatus}

        if new_status_value in valid_status_values:
            instance.status = InventoryStatus(new_status_value)
            try:
                db.session.commit()
                flash(f'Estado actualizado a {new_status_value}.', 'success')
            except Exception:
                db.session.rollback()
                flash('Error al actualizar.', 'danger')
        else:
            flash('Estado no válido.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error ({getattr(form, field).label.text}): {error}", 'danger')
        
    return redirect(url_for('admin.manage_instances', catalog_id=instance.catalog_id))

@bp.route('/instance/delete/<int:instance_id>', methods=['POST'])
@role_required('bibliotecario', 'admin')
def instance_delete(instance_id):
    instance = ItemInstance.query.get_or_404(instance_id)
    catalog_id = instance.catalog_id
    
    if instance.loans.filter(Loan.status.in_([LoanStatus.PENDING, LoanStatus.ACTIVE, LoanStatus.OVERDUE])).first():
        flash('No puedes eliminar una instancia en préstamo activo.', 'danger')
    else:
        db.session.delete(instance)
        db.session.commit()
        flash('Instancia eliminada.', 'success')
        
    return redirect(url_for('admin.manage_instances', catalog_id=catalog_id))