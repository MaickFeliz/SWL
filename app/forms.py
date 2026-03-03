# app/forms.py
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, IntegerField, SelectField, SubmitField, HiddenField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Optional, Email, Length

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
    catalog_id = SelectField('Seleccione el Equipo', coerce=int, validators=[DataRequired()])
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
    status = SelectField(
        'Estado',
        choices=[
            ('disponible', 'Disponible'),
            ('mantenimiento', 'Mantenimiento'),
            ('perdido', 'Perdido'),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField('Registrar Código')


class AdminUserForm(FlaskForm):
    full_name = StringField('Nombre completo', validators=[DataRequired()])
    document_id = StringField('Documento', validators=[DataRequired()])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    phone = StringField('Teléfono', validators=[Optional()])
    role = SelectField(
        'Rol',
        choices=[
            ('cliente', 'Cliente / Usuario'),
            ('premium', 'Staff / Premium'),
            ('bibliotecario', 'Bibliotecario'),
        ],
        validators=[DataRequired()],
    )
    program_name = StringField('Programa / Grupo', validators=[Optional()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Guardar')


class EditUserForm(FlaskForm):
    full_name = StringField('Nombre completo', validators=[DataRequired()])
    phone = StringField('Teléfono', validators=[Optional()])
    role = SelectField(
        'Rol',
        choices=[
            ('cliente', 'Cliente / Usuario'),
            ('premium', 'Staff / Premium'),
            ('bibliotecario', 'Bibliotecario'),
        ],
        validators=[DataRequired()],
    )
    program_name = StringField('Programa / Grupo', validators=[Optional()])
    # Campos opcionales / de solo lectura desde el punto de vista de validación
    document_id = StringField('Documento', validators=[Optional()])
    email = StringField('Correo electrónico', validators=[Optional(), Email()])
    password = PasswordField('Nueva contraseña', validators=[Optional(), Length(min=8)])
    submit = SubmitField('Guardar Cambios')


class ImportForm(FlaskForm):
    file = FileField('Archivo', validators=[DataRequired(), FileAllowed(['csv', 'xlsx'], 'Formatos permitidos: CSV, XLSX')])


class UpdateInstanceStatusForm(FlaskForm):
    status = SelectField(
        'Estado',
        choices=[
            ('disponible', 'Disponible'),
            ('mantenimiento', 'Mantenimiento'),
            ('perdido', 'Perdido'),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField('Actualizar')