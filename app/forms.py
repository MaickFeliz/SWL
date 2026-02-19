from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    username = StringField('Nombre de Usuario', validators=[DataRequired()])
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
    role = SelectField('Rol en el SENA', choices=[
        ('aprendiz', 'Aprendiz'),
        ('instructor', 'Instructor'),
        ('bibliotecario', 'Bibliotecario')
    ], validators=[DataRequired()])
    ficha = StringField('Número de Ficha', validators=[Length(max=15)])
    program_name = StringField(
        'Programa de Formación', validators=[Length(max=100)])
    password = PasswordField('Contraseña', validators=[
                             DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[
                                     DataRequired(), EqualTo('password', message='Las contraseñas deben coincidir.')])
    submit = SubmitField('Registrarse')
