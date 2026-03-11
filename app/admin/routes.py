"""
Rutas de administración para gestión de catálogo, instancias y usuarios.
"""

from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import Catalog, ItemInstance, InventoryStatus


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(fn):
    """Decorador que restringe el acceso a usuarios con rol 'admin'."""
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Acceso denegado. Se requiere rol de administrador.", "danger")
            return redirect(url_for("main.index"))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# =============================================================================
# CATALOG - CRUD
# =============================================================================

@admin_bp.route("/catalog")
@admin_required
def list_catalogs():
    """Lista todos los catálogos."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    pagination = Catalog.query.order_by(Catalog.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("admin/catalog/list.html", pagination=pagination)


@admin_bp.route("/catalog/new", methods=["GET", "POST"])
@admin_required
def create_catalog():
    """Crea un nuevo catálogo."""
    if request.method == "POST":
        catalog = Catalog(
            title_or_name=request.form["title_or_name"],
            category=request.form["category"],
            author_or_brand=request.form.get("author_or_brand") or None,
        )
        db.session.add(catalog)
        db.session.commit()
        flash("Catálogo creado exitosamente.", "success")
        return redirect(url_for("admin.list_catalogs"))
    return render_template("admin/catalog/form.html", catalog=None)


@admin_bp.route("/catalog/<int:catalog_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_catalog(catalog_id):
    """Edita un catálogo existente."""
    catalog = db.session.get(Catalog, catalog_id)
    if not catalog:
        flash("Catálogo no encontrado.", "danger")
        return redirect(url_for("admin.list_catalogs"))

    if request.method == "POST":
        catalog.title_or_name = request.form["title_or_name"]
        catalog.category = request.form["category"]
        catalog.author_or_brand = request.form.get("author_or_brand") or None
        db.session.commit()
        flash("Catálogo actualizado exitosamente.", "success")
        return redirect(url_for("admin.list_catalogs"))

    return render_template("admin/catalog/form.html", catalog=catalog)


@admin_bp.route("/catalog/<int:catalog_id>/delete", methods=["POST"])
@admin_required
def delete_catalog(catalog_id):
    """Elimina un catálogo solo si no tiene instancias físicas asociadas.

    Usa .count() sobre la relación dinámica para evitar cargar todos los objetos
    en memoria y lanzar un error claro antes de intentar el DELETE.
    """
    catalog = db.session.get(Catalog, catalog_id)
    if not catalog:
        flash("Catálogo no encontrado.", "danger")
    elif catalog.instances.count() > 0:
        flash(
            f"No se puede eliminar: el catálogo tiene "
            f"{catalog.instances.count()} instancia(s) registrada(s). "
            "Elimina primero las instancias asociadas.",
            "danger",
        )
    else:
        db.session.delete(catalog)
        db.session.commit()
        flash("Catálogo eliminado exitosamente.", "success")
    return redirect(url_for("admin.list_catalogs"))


# =============================================================================
# ITEMINSTANCE - CRUD
# =============================================================================

@admin_bp.route("/instances")
@admin_required
def list_instances():
    """Lista todas las instancias con filtros opcionales por catálogo y estado."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    catalog_id = request.args.get("catalog_id", type=int)
    status = request.args.get("status")

    query = ItemInstance.query
    if catalog_id:
        query = query.filter(ItemInstance.catalog_id == catalog_id)
    if status:
        try:
            query = query.filter(ItemInstance.status == InventoryStatus(status))
        except ValueError:
            pass  # Valor de estado inválido: ignorar filtro silenciosamente

    pagination = query.order_by(ItemInstance.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    catalogs = Catalog.query.all()
    return render_template(
        "admin/instances/list.html",
        pagination=pagination,
        catalogs=catalogs,
    )


@admin_bp.route("/instances/new", methods=["GET", "POST"])
@admin_required
def create_instance():
    """Registra una nueva instancia física usando InstanceForm con validación."""
    from app.forms import InstanceForm

    form = InstanceForm()
    form_catalogs = Catalog.query.order_by(Catalog.title_or_name).all()

    if form.validate_on_submit():
        try:
            instance = ItemInstance(
                catalog_id=request.form.get("catalog_id"),
                unique_code=form.unique_code.data,
                status=InventoryStatus(form.status.data),
                condition=form.condition.data or None,
            )
            db.session.add(instance)
            db.session.commit()
            flash("Instancia registrada exitosamente.", "success")
            return redirect(url_for("admin.list_instances"))
        except IntegrityError:
            db.session.rollback()
            flash("El código único ya existe.", "danger")
        except ValueError as e:
            flash(f"Estado inválido: {e}", "danger")
    elif request.method == "POST":
        # Tarea 3: feedback detallado por campo cuando validate_on_submit es False
        for field_name, errors in form.errors.items():
            label = getattr(form, field_name).label.text
            for err in errors:
                flash(f"Error en «{label}»: {err}", "danger")

    statuses = [s.value for s in InventoryStatus]
    return render_template(
        "admin/instances/form.html",
        form=form,
        instance=None,
        catalogs=form_catalogs,
        statuses=statuses,
    )


@admin_bp.route("/instances/<int:instance_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_instance(instance_id):
    """Edita una instancia existente con InstanceForm y flash de errores por campo."""
    from app.forms import InstanceForm

    instance = db.session.get(ItemInstance, instance_id)
    if not instance:
        flash("Instancia no encontrada.", "danger")
        return redirect(url_for("admin.list_instances"))

    form = InstanceForm(obj=instance)
    form_catalogs = Catalog.query.order_by(Catalog.title_or_name).all()

    if form.validate_on_submit():
        try:
            instance.catalog_id = request.form.get("catalog_id", instance.catalog_id)
            instance.unique_code = form.unique_code.data
            instance.status = InventoryStatus(form.status.data)
            instance.condition = form.condition.data or None
            db.session.commit()
            flash("Instancia actualizada exitosamente.", "success")
            return redirect(url_for("admin.list_instances"))
        except IntegrityError:
            db.session.rollback()
            flash("El código único ya existe.", "danger")
        except ValueError as e:
            flash(f"Estado inválido: {e}", "danger")
    elif request.method == "POST":
        # Tarea 3: feedback detallado por campo cuando validate_on_submit es False
        for field_name, errors in form.errors.items():
            label = getattr(form, field_name).label.text
            for err in errors:
                flash(f"Error en «{label}»: {err}", "danger")

    statuses = [s.value for s in InventoryStatus]
    return render_template(
        "admin/instances/form.html",
        form=form,
        instance=instance,
        catalogs=form_catalogs,
        statuses=statuses,
    )


@admin_bp.route("/instances/<int:instance_id>/delete", methods=["POST"])
@admin_required
def delete_instance(instance_id):
    """Elimina una instancia física."""
    instance = db.session.get(ItemInstance, instance_id)
    if not instance:
        flash("Instancia no encontrada.", "danger")
    else:
        db.session.delete(instance)
        db.session.commit()
        flash("Instancia eliminada exitosamente.", "success")
    return redirect(url_for("admin.list_instances"))


# =============================================================================
# DASHBOARD DEL BIBLIOTECARIO
# =============================================================================

@admin_bp.route("/dashboard")
@login_required
def admin_dashboard():
    """Panel principal del bibliotecario: préstamos paginados + estadísticas."""
    from app.models import Loan, LoanStatus
    from sqlalchemy import func

    current_status = request.args.get("status", "pendiente")
    page = request.args.get("page", 1, type=int)

    try:
        status_enum = LoanStatus(current_status)
    except ValueError:
        status_enum = LoanStatus.PENDING
        current_status = "pendiente"

    loans_pagination = (
        Loan.query.filter_by(status=status_enum)
        .order_by(Loan.request_date.desc())
        .paginate(page=page, per_page=15, error_out=False)
    )

    stats = {
        "pending":  Loan.query.filter_by(status=LoanStatus.PENDING).count(),
        "activo":   Loan.query.filter_by(status=LoanStatus.ACTIVE).count(),
        "atrasado": Loan.query.filter_by(status=LoanStatus.OVERDUE).count(),
        "returned": Loan.query.filter_by(status=LoanStatus.RETURNED).count(),
    }

    # Top 5 ítems más solicitados
    top_items = (
        db.session.query(
            Catalog.title_or_name.label("title_or_name"),
            func.count(Loan.id).label("total"),
        )
        .join(ItemInstance, ItemInstance.catalog_id == Catalog.id)
        .join(Loan, Loan.instance_id == ItemInstance.id)
        .group_by(Catalog.id, Catalog.title_or_name)
        .order_by(func.count(Loan.id).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        loans_pagination=loans_pagination,
        current_status=current_status,
        stats=stats,
        top_items=top_items,
    )


# =============================================================================
# GESTIÓN DE USUARIOS
# =============================================================================

@admin_bp.route("/users")
@admin_required
def manage_users():
    """Lista todos los usuarios del sistema."""
    from app.models import User

    page = request.args.get("page", 1, type=int)
    users = User.query.order_by(User.full_name).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def create_user():
    """Crea un nuevo usuario. Flash de errores por campo si falla validate_on_submit."""
    from app.forms import AdminUserForm
    from app.models import User

    form = AdminUserForm()

    if form.validate_on_submit():
        if User.query.filter_by(document_id=form.document_id.data).first():
            flash("Ya existe un usuario con ese número de documento.", "danger")
            return render_template("admin/user_form.html", form=form, user=None)
        if form.email.data and User.query.filter_by(email=form.email.data).first():
            flash("Ya existe un usuario con ese correo electrónico.", "danger")
            return render_template("admin/user_form.html", form=form, user=None)

        user = User(
            full_name=form.full_name.data,
            document_id=form.document_id.data,
            email=form.email.data or None,
            phone=form.phone.data or None,
            role=form.role.data,
            program_name=form.program_name.data or None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"Usuario «{user.full_name}» creado exitosamente.", "success")
        return redirect(url_for("admin.manage_users"))
    elif request.method == "POST":
        # Tarea 3: feedback detallado por campo cuando validate_on_submit es False
        for field_name, errors in form.errors.items():
            label = getattr(form, field_name).label.text
            for err in errors:
                flash(f"Error en «{label}»: {err}", "danger")

    return render_template("admin/user_form.html", form=form, user=None)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    """Edita un usuario existente. Flash de errores por campo si falla validate_on_submit."""
    from app.forms import EditUserForm
    from app.models import User

    user = db.session.get(User, user_id)
    if not user:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin.manage_users"))

    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        user.full_name = form.full_name.data
        user.phone = form.phone.data or None
        user.role = form.role.data
        user.program_name = form.program_name.data or None
        if form.email.data:
            user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        try:
            db.session.commit()
            flash(f"Usuario «{user.full_name}» actualizado correctamente.", "success")
            return redirect(url_for("admin.manage_users"))
        except IntegrityError:
            db.session.rollback()
            flash("El correo electrónico ya está en uso por otro usuario.", "danger")
    elif request.method == "POST":
        # Tarea 3: feedback detallado por campo cuando validate_on_submit es False
        for field_name, errors in form.errors.items():
            label = getattr(form, field_name).label.text
            for err in errors:
                flash(f"Error en «{label}»: {err}", "danger")

    return render_template("admin/user_form.html", form=form, user=user)