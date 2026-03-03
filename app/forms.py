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
    visitor_name = StringField('Nombre', validators=[Optional()])
    submit = SubmitField('Registrar Visita')