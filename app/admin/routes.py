from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.admin import bp
from app import db
from app.models import Loan, User
from datetime import datetime

@bp.route('/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'bibliotecario':
        return redirect(url_for('main.instructor_dashboard'))

    # Filtros
    status_filter = request.args.get('status', 'pendiente')
    role_filter = request.args.get('role')

    query = Loan.query.filter(Loan.status == status_filter)
    
    if role_filter:
        query = query.join(User).filter(User.role == role_filter)

    loans = query.order_by(Loan.request_date.desc()).all()
    
    return render_template('admin/dashboard.html', loans=loans, current_status=status_filter)

@bp.route('/approve/<int:id>', methods=['POST'])
@login_required
def approve(id):
    loan = Loan.query.get_or_404(id)
    serial = request.form.get('serial')
    
    if not serial:
        flash('Falta el serial', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
        
    loan.assigned_serial = serial
    loan.status = 'aprobado'
    loan.approval_date = datetime.utcnow()
    db.session.commit()
    flash('Préstamo aprobado', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@bp.route('/return/<int:id>')
@login_required
def return_item(id):
    loan = Loan.query.get_or_404(id)
    loan.status = 'devuelto'
    loan.return_date = datetime.utcnow()
    db.session.commit()
    flash('Elemento devuelto', 'info')
    return redirect(url_for('admin.admin_dashboard', status='aprobado'))