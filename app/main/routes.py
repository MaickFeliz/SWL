from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.main import bp
from app import db
from app.models import Loan

@bp.route('/')
@login_required
def instructor_dashboard():
    if current_user.role == 'bibliotecario':
        return redirect(url_for('admin.admin_dashboard'))
        
    my_loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.request_date.desc()).all()
    return render_template('instructor/dashboard.html', loans=my_loans)

@bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_loan():
    if request.method == 'POST':
        item = request.form.get('item_type')
        new_loan = Loan(user_id=current_user.id, item_type=item)
        db.session.add(new_loan)
        db.session.commit()
        flash('Solicitud enviada.', 'success')
        return redirect(url_for('main.instructor_dashboard'))
    return render_template('instructor/request.html')