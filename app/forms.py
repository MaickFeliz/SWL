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
    catalog_id = SelectField('Seleccione el Elemento', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Cantidad', default=1, validators=[DataRequired(), NumberRange(min=1)])
    environment = SelectField('Ambiente', choices=[('interno', 'Interno'), ('externo', 'Externo')], validators=[Optional()])
    submit_loan = SubmitField('Confirmar Préstamo')

class CatalogForm(FlaskForm):
    title_or_name = StringField('Nombre / Título', validators=[DataRequired()])
    category = SelectField('Categoría', choices=[('computo', 'Equipo de Cómputo'), ('accesorio', 'Accesorio / General'), ('libro', 'Libro')], validators=[DataRequired()])
    author_or_brand = StringField('Marca/Autor', validators=[Optional()])
    submit = SubmitField('Guardar')

class InstanceForm(FlaskForm):
    unique_code = StringField('Placa SENA / Serial / Código de Barras', validators=[DataRequired()])
    condition = StringField('Condición', validators=[Optional()])
    submit = SubmitField('Registrar Código')