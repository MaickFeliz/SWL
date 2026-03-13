from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.services.inventory_service import CatalogService
from app.main import bp
from app import db
from app.models import Loan, User, LibraryLog
from app.services.loan_service import LoanService
from app.utils.decorators import role_required
from app.forms import RequestItemForm, VisitForm, FastLoanSearchForm, FastLoanForm


@bp.route('/fast_loan', methods=['GET', 'POST'])
@login_required
def fast_loan():
    search_form = FastLoanSearchForm()
    loan_form = FastLoanForm()

    user_id = request.form.get('user_id')
    user = None
    if user_id:
        user = db.session.get(User, user_id)
    elif search_form.validate_on_submit() and search_form.submit_search.data:
        user = User.query.filter_by(document_id=search_form.document_id.data).first()

    exclude_cat = 'general' if user and user.role == 'premium' else None
    all_items = CatalogService.get_catalog_with_counts(exclude_category=exclude_cat)
    loan_form.catalog_id.choices = [
        (i.id, f"{i.title_or_name} (Disponibles: {i.available_count})")
        for i in all_items
        if i.available_count > 0
    ]

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

        item_type = loan_form.item_type.data
        environment = loan_form.environment.data
        try:
            catalog_id = int(loan_form.catalog_id.data)
            quantity = 1 if item_type == 'computo' else int(loan_form.quantity.data)
        except (TypeError, ValueError):
            flash('ID de catálogo o cantidad inválidos.', 'danger')
            return redirect(url_for('main.fast_loan'))

        try:
            LoanService.create_loan(
                user_id=target_user_id,
                catalog_id=catalog_id,
                quantity=quantity,
                environment=environment,
            )
            flash('Préstamo rápido registrado con éxito.', 'success')
        except ValueError as exc:
            flash(str(exc), 'warning')
        except Exception:
            flash('Error interno al procesar la solicitud.', 'danger')

        return redirect(url_for('main.index'))

    elif request.method == 'POST' and loan_form.submit_loan.data:
        for field, errors in loan_form.errors.items():
            for err in errors:
                flash(f"Error de validación en {field}: {err}", 'danger')

    return render_template('main/fast_loan.html', search_form=search_form, loan_form=loan_form)


@bp.route('/visit', methods=['GET', 'POST'])
def register_visit():
    form = VisitForm()

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
    available_computers = CatalogService.get_catalog_with_counts(category_filter='computo')

    if form.validate_on_submit():
        try:
            quantity = int(form.quantity.data) if current_user.role == 'premium' else 1
            catalog_id = int(form.catalog_id.data)
        except (TypeError, ValueError):
            flash('Parámetros inválidos.', 'danger')
            return redirect(url_for('main.request_laptop'))
            
        environment = form.environment.data

        try:
            LoanService.create_loan(
                user_id=current_user.id,
                catalog_id=catalog_id,
                quantity=quantity,
                environment=environment,
            )
            flash('Solicitud de portátil enviada correctamente.', 'success')
        except ValueError as exc:
            flash(str(exc), 'warning')
        except Exception:
            flash('Error interno al registrar la solicitud.', 'danger')

        return redirect(url_for('main.premium_dashboard'))

    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Error de validación en {field}: {err}", 'danger')

    return render_template('premium/request_laptop.html', items=available_computers, form=form)


@bp.route('/request/accessory', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_accessory():
    form = RequestItemForm()
    can_request, msg = LoanService.can_request_accessory(current_user.id)
    if not can_request:
        flash(msg, 'warning')
        return redirect(url_for('main.index'))

    exclude_cat = 'computo' if current_user.role == 'cliente' else None
    available_items = CatalogService.get_catalog_with_counts(exclude_category=exclude_cat)

    if form.validate_on_submit():
        try:
            catalog_id = int(form.catalog_id.data)
            quantity = int(form.quantity.data)
        except (TypeError, ValueError):
            flash('Parámetros inválidos.', 'danger')
            return redirect(url_for('main.request_accessory'))

        try:
            LoanService.create_loan(
                user_id=current_user.id,
                catalog_id=catalog_id,
                quantity=quantity,
            )
            flash('Solicitud realizada con éxito.', 'success')
        except ValueError as exc:
            flash(str(exc), 'warning')
        except Exception:
            flash('Error interno al procesar la solicitud.', 'danger')

        return redirect(url_for('main.premium_dashboard'))

    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Error de validación en {field}: {err}", 'danger')

    return render_template('premium/request_accessory.html', items=available_items, form=form)


@bp.route('/request/book', methods=['GET', 'POST'])
@role_required('premium', 'cliente')
def request_book():
    form = RequestItemForm()
    available_books = CatalogService.get_catalog_with_counts(category_filter='libro')

    if form.validate_on_submit():
        try:
            catalog_id = int(form.catalog_id.data)
        except (TypeError, ValueError):
            flash('ID de catálogo inválido.', 'danger')
            return redirect(url_for('main.request_book'))

        try:
            LoanService.create_loan(user_id=current_user.id, catalog_id=catalog_id)
            flash('Solicitud de libro registrada. Acércate al mostrador.', 'success')
        except ValueError as exc:
            flash(str(exc), 'warning')
        except Exception:
            flash('Ocurrió un error al registrar la solicitud.', 'danger')

        return redirect(url_for('main.premium_dashboard'))

    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Error de validación en {field}: {err}", 'danger')

    return render_template('premium/request_book.html', items=available_books, form=form)
