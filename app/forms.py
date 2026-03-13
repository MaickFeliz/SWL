from __future__ import annotations
from typing import Optional
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    IntegerField,
    SelectField,
    SubmitField,
    HiddenField,
    PasswordField,
)
from wtforms.validators import DataRequired, NumberRange, Optional, Email, Length, EqualTo
from app.models import InventoryStatus

AMBIENTES = [(str(i), f'Ambiente {i}') for i in range(1, 15)] + [('15', 'Ambiente 15 (Peluquería)')]


def strip_filter(value: Optional[str]) -> Optional[str]:
    """Normaliza entradas eliminando espacios para evitar errores sutiles de validación."""
    return value.strip() if value else None


class RequestItemForm(FlaskForm):
    catalog_id = IntegerField('catalog_id', validators=[DataRequired()])
    quantity = IntegerField('Cantidad', default=1, validators=[DataRequired(), NumberRange(min=1)])
    environment = SelectField('Ambiente', choices=AMBIENTES, validators=[Optional()])
    submit = SubmitField('Solicitar')

class VisitForm(FlaskForm):
    document_id = StringField(
        'Documento',
        validators=[DataRequired()],
        filters=[strip_filter],
    )
    visitor_name = StringField(
        'Nombre del Visitante',
        validators=[Optional(), Length(max=100)],
        filters=[strip_filter],
    )
    activity = StringField(
        'Actividad',
        validators=[DataRequired(), Length(max=50)],
        filters=[strip_filter],
    )
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
    environment = SelectField('Ambiente', choices=AMBIENTES, validators=[Optional()])
    submit_loan = SubmitField('Confirmar Préstamo')

class CatalogForm(FlaskForm):
    title_or_name = StringField('Nombre / Título', validators=[DataRequired()])
    category = SelectField('Categoría', choices=[('computo', 'Equipo de Cómputo'), ('accesorio', 'Accesorio / General'), ('libro', 'Libro')], validators=[DataRequired()])
    author_or_brand = StringField('Marca/Autor', validators=[Optional()])
    submit = SubmitField('Guardar')

class InstanceForm(FlaskForm):
    unique_code = StringField('Placa / Serial / Código de Barras', validators=[DataRequired()])
    condition = SelectField('Estado Físico / Condición', choices=[('Nuevo', 'Nuevo'), ('Bueno', 'Bueno'), ('Regular', 'Regular'), ('Malo', 'Malo')], validators=[Optional()])
    status = SelectField(
        'Estado',
        choices=[
            (InventoryStatus.AVAILABLE.value, 'Disponible'),
            (InventoryStatus.MAINTENANCE.value, 'Mantenimiento'),
            (InventoryStatus.LOST.value, 'Perdido'),
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
            (InventoryStatus.AVAILABLE.value, 'Disponible'),
            (InventoryStatus.MAINTENANCE.value, 'Mantenimiento'),
            (InventoryStatus.LOST.value, 'Perdido'),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField('Actualizar')


class LoginForm(FlaskForm):
    document_id = StringField('Documento', validators=[DataRequired(), Length(max=20)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Ingresar')


class RegistrationForm(FlaskForm):
    full_name = StringField('Nombre completo', validators=[DataRequired(), Length(max=100)])
    email = StringField('Correo electrónico', validators=[DataRequired(), Email(), Length(max=120)])
    document_id = StringField('Documento', validators=[DataRequired(), Length(max=20)])
    phone = StringField('Teléfono', validators=[Optional(), Length(max=20)])
    role = SelectField(
        'Rol',
        choices=[
            ('cliente', 'Cliente / Usuario'),
            ('premium', 'Staff / Premium'),
            ('bibliotecario', 'Bibliotecario'),
        ],
        validators=[DataRequired()],
    )
    program_name = StringField('Programa / Grupo', validators=[Optional(), Length(max=100)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        'Confirmar contraseña',
        validators=[DataRequired(), EqualTo('password', message='Las contraseñas no coinciden.')],
    )
    submit = SubmitField('Registrarse')