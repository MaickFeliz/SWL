# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Optional

class RequestItemForm(FlaskForm):
    catalog_id = HiddenField('catalog_id', validators=[DataRequired()])
    quantity = IntegerField('Cantidad', default=1, validators=[DataRequired(), NumberRange(min=1)])
    environment = SelectField('Ambiente', choices=[('interno', 'Interno'), ('externo', 'Externo')], validators=[Optional()])
    submit = SubmitField('Solicitar')

class VisitForm(FlaskForm):
    document_id = StringField('Documento', validators=[DataRequired()])
    activity = StringField('Actividad', validators=[DataRequired()])
    submit = SubmitField('Registrar Visita')

# NUEVOS FORMULARIOS PARA PRÉSTAMO RÁPIDO
class FastLoanSearchForm(FlaskForm):
    document_id = StringField('Documento', validators=[DataRequired()])
    submit_search = SubmitField('Buscar Usuario')

class FastLoanForm(FlaskForm):
    user_id = HiddenField('user_id', validators=[DataRequired()])
    item_type = HiddenField('item_type', validators=[DataRequired()])
    catalog_id = HiddenField('catalog_id', validators=[DataRequired()])
    quantity = IntegerField('Cantidad', default=1, validators=[DataRequired(), NumberRange(min=1)])
    environment = SelectField('Ambiente', choices=[('interno', 'Interno'), ('externo', 'Externo')], validators=[Optional()])
    submit_loan = SubmitField('Confirmar Préstamo')