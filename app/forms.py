from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    document_id = StringField('Número de Identificación', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    full_name = StringField(
        'Nombre Completo', validators=[DataRequired(), Length(min=4, max=100)])
    document_id = StringField(
        'Documento de Identidad', validators=[DataRequired(), Length(min=7, max=15)])
    email = StringField('Correo Electrónico', validators=[
                        DataRequired(), Email()])
    phone = StringField('Celular', validators=[
                        DataRequired(), Length(min=10, max=15)])
    role = SelectField('Rol en el Sistema', choices=[
        ('cliente', 'Usuario/Cliente'),
        ('premium', 'Usuario Premium/Staff'),
        ('bibliotecario', 'Bibliotecario')
    ], validators=[DataRequired()])
    program_name = StringField(
        'Programa de Formación', validators=[Length(max=100)])
    password = PasswordField('Contraseña', validators=[
                             DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[
                                     DataRequired(), EqualTo('password', message='Las contraseñas deben coincidir.')])
    submit = SubmitField('Registrarse')

class AdminUserForm(FlaskForm):
    full_name = StringField('Nombre Completo', validators=[DataRequired(), Length(min=4, max=100)])
    document_id = StringField('Documento de Identidad', validators=[DataRequired(), Length(min=7, max=15)])
    email = StringField('Correo Electrónico', validators=[DataRequired(), Email()])
    phone = StringField('Celular', validators=[DataRequired(), Length(min=10, max=15)])
    role = SelectField('Rol en el Sistema', choices=[
        ('cliente', 'Usuario/Cliente'),
        ('premium', 'Usuario Premium/Staff'),
        ('bibliotecario', 'Bibliotecario'),
        ('admin', 'Administrador')
    ], validators=[DataRequired()])
    program_name = StringField('Programa de Formación', validators=[Length(max=100)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Crear Usuario')

class ImportForm(FlaskForm):
    file = FileField('Archivo Excel o CSV', validators=[
        FileRequired(),
        FileAllowed(['csv', 'xlsx'], 'Solo archivos CSV o Excel (xlsx)')
    ])
    submit = SubmitField('Importar Datos')
