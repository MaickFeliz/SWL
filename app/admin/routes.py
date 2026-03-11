"""
Rutas de administración para gestión de catálogo e instancias.
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
            flash("Acceso denegado. Se requiere rol de administrador.", "error")
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
            author_or_brand=request.form.get("author_or_brand") or None
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
        flash("Catálogo no encontrado.", "error")
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
    """Elimina un catálogo."""
    catalog = db.session.get(Catalog, catalog_id)
    if not catalog:
        flash("Catálogo no encontrado.", "error")
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
    """Lista todas las instancias."""
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
    return render_template("admin/instances/list.html", 
                         pagination=pagination, catalogs=catalogs)


@admin_bp.route("/instances/new", methods=["GET", "POST"])
@admin_required
def create_instance():
    """Registra una nueva instancia física."""
    if request.method == "POST":
        try:
            instance = ItemInstance(
                catalog_id=request.form["catalog_id"],
                unique_code=request.form["unique_code"],
                status=InventoryStatus(request.form.get("status", "disponible")),
                condition=request.form.get("condition") or None
            )
            db.session.add(instance)
            db.session.commit()
            flash("Instancia registrada exitosamente.", "success")
            return redirect(url_for("admin.list_instances"))
        except IntegrityError:
            db.session.rollback()
            flash("El código único ya existe.", "error")
        except ValueError as e:
            flash(f"Estado inválido: {e}", "error")
    
    catalogs = Catalog.query.all()
    statuses = [s.value for s in InventoryStatus]
    return render_template("admin/instances/form.html", 
                         instance=None, catalogs=catalogs, statuses=statuses)


@admin_bp.route("/instances/<int:instance_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_instance(instance_id):
    """Edita una instancia existente."""
    instance = db.session.get(ItemInstance, instance_id)
    if not instance:
        flash("Instancia no encontrada.", "error")
        return redirect(url_for("admin.list_instances"))
    
    if request.method == "POST":
        try:
            instance.catalog_id = request.form["catalog_id"]
            instance.unique_code = request.form["unique_code"]
            instance.status = InventoryStatus(request.form.get("status", "disponible"))
            instance.condition = request.form.get("condition") or None
            db.session.commit()
            flash("Instancia actualizada exitosamente.", "success")
            return redirect(url_for("admin.list_instances"))
        except IntegrityError:
            db.session.rollback()
            flash("El código único ya existe.", "error")
        except ValueError as e:
            flash(f"Estado inválido: {e}", "error")
    
    catalogs = Catalog.query.all()
    statuses = [s.value for s in InventoryStatus]
    return render_template("admin/instances/form.html", 
                         instance=instance, catalogs=catalogs, statuses=statuses)


@admin_bp.route("/instances/<int:instance_id>/delete", methods=["POST"])
@admin_required
def delete_instance(instance_id):
    """Elimina una instancia."""
    instance = db.session.get(ItemInstance, instance_id)
    if not instance:
        flash("Instancia no encontrada.", "error")
    else:
        db.session.delete(instance)
        db.session.commit()
        flash("Instancia eliminada exitosamente.", "success")
    return redirect(url_for("admin.list_instances"))