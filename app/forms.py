from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, FileField, BooleanField, MultipleFileField, SelectMultipleField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, Regexp
from flask_wtf.file import FileRequired, FileAllowed

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class CategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(max=64)])
    description = TextAreaField('Описание')
    submit = SubmitField('Сохранить')

class ApplicationForm(FlaskForm):
    package_name = StringField('Package Name', validators=[DataRequired(), Length(max=128)])
    name = StringField('Название', validators=[DataRequired(), Length(max=128)])
    description = TextAreaField('Описание')
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Сохранить')

class UploadApkForm(FlaskForm):
    apk_file = FileField('APK файл', validators=[
        FileRequired(),
        FileAllowed(['apk'], 'Разрешены только APK файлы')
    ])
    version_number = StringField('Номер версии', validators=[
        DataRequired(),
        Regexp(r'^\d+(\.\d+)*$', message='Номер версии должен состоять из цифр, разделенных точками')
    ])
    branch = SelectField('Тип сборки', choices=[
        ('release', 'Release'),
        ('debug', 'Debug'),
        ('beta', 'Beta'),
        ('alpha', 'Alpha')
    ], validators=[DataRequired()])
    changelog = TextAreaField('Список изменений')
    is_stable = BooleanField('Стабильная версия')
    submit = SubmitField('Загрузить')

class AddFlagForm(FlaskForm):
    flag_type = SelectField('Тип', choices=[
        ('bug', 'Ошибка'),
        ('feature', 'Новая функция'),
        ('warning', 'Предупреждение')
    ])
    description = StringField('Описание', validators=[DataRequired(), Length(max=255)])
    submit = SubmitField('Добавить')

class UserForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('Пароль', validators=[
        Optional(),
        Length(min=6, message='Пароль должен содержать минимум 6 символов')
    ])
    confirm_password = PasswordField('Подтвердите пароль', validators=[
        Optional(),
        EqualTo('password', message='Пароли должны совпадать')
    ])
    roles = SelectMultipleField('Роли', coerce=int)
    is_active = BooleanField('Активен')
    submit = SubmitField('Сохранить')

class RoleForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(max=64)])
    description = TextAreaField('Описание', validators=[Optional(), Length(max=255)])
    permissions = SelectMultipleField('Разрешения', choices=[
        ('add_application', 'Добавление приложений'),
        ('edit_application', 'Редактирование приложений'),
        ('delete_application', 'Удаление приложений'),
        ('add_version', 'Добавление версий'),
        ('edit_version', 'Редактирование версий'),
        ('delete_version', 'Удаление версий'),
        ('manage_users', 'Управление пользователями'),
        ('manage_roles', 'Управление ролями')
    ])
    submit = SubmitField('Сохранить') 