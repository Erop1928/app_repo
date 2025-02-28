from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, jsonify, current_app, abort
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Category, Application, ApkVersion, VersionFlag, Role, UserActionLog, OneTimeDownloadLink
from app.forms import (LoginForm, CategoryForm, ApplicationForm, UploadApkForm, 
                      AddFlagForm, UserForm, RoleForm, MultiUploadApkForm)
from config import Config
from app import db
import os
from werkzeug.utils import secure_filename
from functools import wraps
from sqlalchemy import or_
from datetime import datetime
import json
import shutil

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('У вас нет прав для доступа к этой странице')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@login_required
@admin_required
def admin_panel():
    return render_template('admin/index.html')

@admin.route('/users')
@login_required
@admin_required
def users_list():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    form = UserForm()
    form.roles.choices = [(role.id, role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('admin.new_user'))
        
        user = User(
            username=form.username.data,
            is_active=form.is_active.data
        )
        if form.password.data:
            user.set_password(form.password.data)
            
        # Добавляем роли
        selected_roles = Role.query.filter(Role.id.in_(form.roles.data)).all()
        user.roles = selected_roles
        
        db.session.add(user)
        db.session.commit()
        
        # Логируем создание пользователя
        UserActionLog.log_action(
            current_user,
            'create_user',
            'user',
            user.id,
            None,
            {
                'username': user.username,
                'is_active': user.is_active,
                'roles': [role.name for role in user.roles]
            }
        )
        
        flash('Пользователь создан')
        return redirect(url_for('admin.users_list'))
        
    return render_template('admin/user_form.html', form=form, title='Новый пользователь')

@admin.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    form.roles.choices = [(role.id, role.name) for role in Role.query.all()]
    
    if form.validate_on_submit():
        # Сохраняем старые значения для лога
        old_value = {
            'username': user.username,
            'is_active': user.is_active,
            'roles': [role.name for role in user.roles]
        }
        
        username_exists = User.query.filter(
            User.username == form.username.data,
            User.id != id
        ).first()
        if username_exists:
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('admin.edit_user', id=id))
        
        user.username = form.username.data
        user.is_active = form.is_active.data
        
        if form.password.data:
            user.set_password(form.password.data)
            
        # Обновляем роли
        selected_roles = Role.query.filter(Role.id.in_(form.roles.data)).all()
        user.roles = selected_roles
        
        db.session.commit()
        
        # Логируем изменение пользователя
        new_value = {
            'username': user.username,
            'is_active': user.is_active,
            'roles': [role.name for role in user.roles]
        }
        
        UserActionLog.log_action(
            current_user,
            'edit_user',
            'user',
            user.id,
            old_value,
            new_value
        )
        
        flash('Пользователь обновлен')
        return redirect(url_for('admin.users_list'))
        
    # Предзаполняем выбранные роли
    form.roles.data = [role.id for role in user.roles]
    
    return render_template('admin/user_form.html', form=form, user=user, title='Редактирование пользователя')

@admin.route('/users/<int:id>/delete')
@login_required
@admin_required
def delete_user(id):
    if current_user.id == id:
        flash('Нельзя удалить самого себя')
        return redirect(url_for('admin.users_list'))
        
    user = User.query.get_or_404(id)
    
    # Сохраняем данные пользователя для лога
    old_value = {
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
        'roles': [role.name for role in user.roles]
    }
    
    db.session.delete(user)
    db.session.commit()
    
    # Логируем удаление пользователя
    UserActionLog.log_action(
        current_user,
        'delete_user',
        'user',
        id,
        old_value,
        None
    )
    
    flash('Пользователь удален')
    return redirect(url_for('admin.users_list'))

@admin.route('/roles')
@login_required
@admin_required
def roles_list():
    roles = Role.query.all()
    return render_template('admin/roles.html', roles=roles)

@admin.route('/roles/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_role():
    form = RoleForm()
    
    if form.validate_on_submit():
        if Role.query.filter_by(name=form.name.data).first():
            flash('Роль с таким названием уже существует')
            return redirect(url_for('admin.new_role'))
            
        role = Role(
            name=form.name.data,
            description=form.description.data,
            permissions=form.permissions.data
        )
        db.session.add(role)
        db.session.commit()
        flash('Роль создана')
        return redirect(url_for('admin.roles_list'))
        
    return render_template('admin/role_form.html', form=form, title='Новая роль')

@admin.route('/roles/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(id):
    role = Role.query.get_or_404(id)
    form = RoleForm(obj=role)
    
    if form.validate_on_submit():
        name_exists = Role.query.filter(
            Role.name == form.name.data,
            Role.id != id
        ).first()
        if name_exists:
            flash('Роль с таким названием уже существует')
            return redirect(url_for('admin.edit_role', id=id))
            
        role.name = form.name.data
        role.description = form.description.data
        role.permissions = form.permissions.data
        
        db.session.commit()
        flash('Роль обновлена')
        return redirect(url_for('admin.roles_list'))
        
    # Предзаполняем разрешения
    form.permissions.data = role.permissions
    
    return render_template('admin/role_form.html', form=form, role=role, title='Редактирование роли')

@admin.route('/roles/<int:id>/delete')
@login_required
@admin_required
def delete_role(id):
    role = Role.query.get_or_404(id)
    if role.users:
        flash('Нельзя удалить роль, которая назначена пользователям')
        return redirect(url_for('admin.roles_list'))
        
    db.session.delete(role)
    db.session.commit()
    flash('Роль удалена')
    return redirect(url_for('admin.roles_list'))

@main.route('/')
@login_required
def index():
    categories = Category.query.all()
    category_id = request.args.get('category', type=int)
    
    try:
        # Получаем ID категории инструментов
        tools_category = Category.query.filter_by(name='Инструменты').first()
        tools_category_id = tools_category.id if tools_category else None
        
        if category_id:
            # Если выбрана категория и это не инструменты
            if category_id != tools_category_id:
                applications = Application.query.filter_by(category_id=category_id).all()
                current_category = Category.query.get_or_404(category_id)
            else:
                applications = []
                current_category = tools_category
        else:
            # Показываем все приложения кроме инструментов
            applications = Application.query.filter(
                Application.category_id != tools_category_id if tools_category_id else False
            ).all()
            current_category = None
        
        return render_template('index.html', 
                            applications=applications, 
                            categories=categories,
                            current_category=current_category)
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        flash(f'Ошибка при загрузке списка приложений: {str(e)}')
        return render_template('index.html', 
                            applications=[], 
                            categories=categories,
                            current_category=None)

@main.route('/application/new', methods=['GET', 'POST'])
@login_required
def new_application():
    form = ApplicationForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        application = Application(
            package_name=form.package_name.data,
            name=form.name.data,
            description=form.description.data,
            category_id=form.category_id.data
        )
        db.session.add(application)
        db.session.commit()
        flash('Приложение добавлено')
        return redirect(url_for('main.application_details', id=application.id))
    
    return render_template('application_form.html', form=form, title='Новое приложение')

@main.route('/application/<int:id>')
@login_required
def application_details(id):
    application = Application.query.get_or_404(id)
    versions = ApkVersion.query.filter_by(application_id=id).order_by(ApkVersion.upload_date.desc()).all()
    flag_form = AddFlagForm()
    return render_template('application_details.html', 
                         application=application,
                         versions=versions,
                         flag_form=flag_form)

@main.route('/application/<int:id>/upload', methods=['GET', 'POST'])
@login_required
def upload_version(id):
    application = Application.query.get_or_404(id)
    form = UploadApkForm()
    multi_form = MultiUploadApkForm()
    
    if form.validate_on_submit():
        file = form.apk_file.data
        filename = secure_filename(file.filename)
        
        # Создаем директорию для загрузок если её нет
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Полный путь к файлу
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Сохраняем файл
        file.save(filepath)
        
        # Получаем размер файла
        file_size = os.path.getsize(filepath)
        
        # Создаем новую версию
        version = ApkVersion(
            application=application,
            version_number=form.version_number.data,
            branch=form.branch.data,
            changelog=form.changelog.data,
            is_stable=form.is_stable.data,
            filename=filename,
            file_size=file_size,
            uploader=current_user
        )
        
        try:
            db.session.add(version)
            db.session.commit()
            
            # Логируем действие
            UserActionLog.log_action(
                current_user,
                'upload_version',
                'apk_version',
                version.id,
                None,
                {
                    'version': version.version_number,
                    'branch': version.branch,
                    'is_stable': version.is_stable,
                    'filename': version.filename
                },
                f'Загружена новая версия {version.version_number} для {application.package_name}'
            )
            
            flash('Версия успешно загружена.', 'success')
            return redirect(url_for('main.application_details', id=application.id))
            
        except Exception as e:
            db.session.rollback()
            # Удаляем загруженный файл
            if os.path.exists(filepath):
                os.remove(filepath)
            flash(f'Ошибка при сохранении версии: {str(e)}', 'error')
    
    return render_template('upload_version.html', form=form, multi_form=multi_form, application=application)

@main.route('/version/<int:id>/flag', methods=['POST'])
@login_required
def add_flag(id):
    version = ApkVersion.query.get_or_404(id)
    
    # Проверяем, является ли запрос AJAX-запросом
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Отладочная информация
    current_app.logger.info(f"Добавление флага для версии {id}")
    current_app.logger.info(f"AJAX запрос: {is_ajax}")
    current_app.logger.info(f"Метод запроса: {request.method}")
    current_app.logger.info(f"Заголовки запроса: {dict(request.headers)}")
    current_app.logger.info(f"Данные формы: {dict(request.form)}")
    
    try:
        # Для AJAX-запросов используем данные из request.form
        if is_ajax:
            flag_type = request.form.get('flag_type')
            description = request.form.get('description')
            
            current_app.logger.info(f"Тип флага: {flag_type}")
            current_app.logger.info(f"Описание: {description}")
            
            if not flag_type or not description:
                return jsonify({'success': False, 'error': 'Не указан тип флага или описание'})
            
            # Проверяем, что тип флага допустимый
            valid_flag_types = ['bug', 'feature', 'warning']
            if flag_type not in valid_flag_types:
                return jsonify({'success': False, 'error': 'Недопустимый тип флага'})
            
            # Проверяем длину описания
            if len(description) > 255:
                return jsonify({'success': False, 'error': 'Описание слишком длинное (максимум 255 символов)'})
            
            flag = VersionFlag(
                version_id=version.id,
                flag_type=flag_type,
                description=description,
                created_by=current_user
            )
            
            try:
                db.session.add(flag)
                db.session.commit()
                
                # Логируем добавление флага
                UserActionLog.log_action(
                    current_user,
                    'add_flag',
                    'version_flag',
                    flag.id,
                    None,
                    {
                        'version_id': version.id,
                        'flag_type': flag.flag_type,
                        'description': flag.description
                    },
                    f'Добавлен флаг "{flag.description}" к версии {version.version_number}'
                )
                
                return jsonify({'success': True, 'message': 'Флаг добавлен'})
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Ошибка при сохранении флага: {str(e)}")
                return jsonify({'success': False, 'error': f'Ошибка при сохранении флага: {str(e)}'})
        else:
            # Для обычных запросов используем форму
            form = AddFlagForm()
            if form.validate_on_submit():
                flag = VersionFlag(
                    version_id=version.id,
                    flag_type=form.flag_type.data,
                    description=form.description.data,
                    created_by=current_user
                )
                db.session.add(flag)
                db.session.commit()
                
                flash('Флаг добавлен')
                return redirect(url_for('main.application_details', id=version.application_id))
            else:
                flash('Ошибка при добавлении флага')
                return redirect(url_for('main.application_details', id=version.application_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка при добавлении флага: {str(e)}")
        
        if is_ajax:
            return jsonify({'success': False, 'error': str(e)})
        else:
            flash(f'Ошибка: {str(e)}')
            return redirect(url_for('main.application_details', id=version.application_id))

@main.route('/version/<int:id>/download')
@login_required
def download_version(id):
    try:
        version = ApkVersion.query.get_or_404(id)
        file_path = os.path.join(Config.UPLOAD_FOLDER, version.filename)
        
        if not os.path.exists(file_path):
            flash('Файл не найден')
            return redirect(url_for('main.application_details', id=version.application_id))
        
        # Увеличиваем счетчик загрузок
        version.downloads += 1
        
        # Логируем скачивание
        UserActionLog.log_action(
            current_user,
            'download_version',
            'version',
            version.id,
            None,
            {'downloads': version.downloads},
            f'Скачана версия {version.version_number} ({version.branch})'
        )
        
        db.session.commit()
        
        try:
            return send_from_directory(
                Config.UPLOAD_FOLDER,
                version.filename,
                as_attachment=True
            )
        except Exception as e:
            flash(f'Ошибка при скачивании файла: {str(e)}')
            print(f'Error downloading file: {str(e)}')
            return redirect(url_for('main.application_details', id=version.application_id))
            
    except Exception as e:
        flash(f'Ошибка: {str(e)}')
        print(f'Error in download_version route: {str(e)}')
        return redirect(url_for('main.index'))

@main.route('/version/<int:id>/delete')
@login_required
def delete_version(id):
    version = ApkVersion.query.get_or_404(id)
    application_id = version.application_id
    
    # Сохраняем информацию о версии для лога
    version_info = {
        'version_number': version.version_number,
        'branch': version.branch,
        'filename': version.filename,
        'is_stable': version.is_stable
    }
    
    try:
        # Удаляем файл
        file_path = os.path.join(Config.UPLOAD_FOLDER, version.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Удаляем запись из базы
        db.session.delete(version)
        db.session.commit()
        
        # Логируем удаление
        UserActionLog.log_action(
            current_user,
            'delete_version',
            'version',
            version.id,
            version_info,
            None,
            f'Удалена версия {version.version_number} ({version.branch})'
        )
        
        flash('Версия удалена')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении версии: {str(e)}')
    
    return redirect(url_for('main.application_details', id=application_id))

@main.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(name=form.name.data, description=form.description.data)
        db.session.add(category)
        db.session.commit()
        flash('Категория добавлена')
        return redirect(url_for('main.categories'))
    
    categories = Category.query.all()
    return render_template('categories.html', categories=categories, form=form)

@main.route('/category/delete/<int:id>')
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    if Application.query.filter_by(category_id=id).first():
        flash('Невозможно удалить категорию, содержащую приложения')
        return redirect(url_for('main.categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash('Категория удалена')
    return redirect(url_for('main.categories'))

@main.route('/version/<int:id>/edit_changelog', methods=['POST'])
@login_required
def edit_changelog(id):
    version = ApkVersion.query.get_or_404(id)
    
    try:
        changelog = request.json.get('changelog', '')
        version.changelog = changelog
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Changelog обновлен',
            'changelog': changelog
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@main.route('/version/<int:id>/toggle_stable', methods=['POST'])
@login_required
def toggle_stable(id):
    version = ApkVersion.query.get_or_404(id)
    
    # Отладочная информация
    current_app.logger.info(f"Переключение стабильной версии для версии {id}")
    current_app.logger.info(f"Текущее значение is_stable: {version.is_stable}")
    current_app.logger.info(f"Метод запроса: {request.method}")
    current_app.logger.info(f"Заголовки запроса: {dict(request.headers)}")
    
    try:
        version.is_stable = not version.is_stable
        db.session.commit()
        
        status = 'стабильной' if version.is_stable else 'нестабильной'
        flash(f'Версия {version.version_number} отмечена как {status}')
        
        current_app.logger.info(f"Новое значение is_stable: {version.is_stable}")
        
        # Логируем изменение статуса стабильности
        UserActionLog.log_action(
            current_user,
            'toggle_stable',
            'version',
            version.id,
            {'is_stable': not version.is_stable},
            {'is_stable': version.is_stable},
            f'Версия {version.version_number} отмечена как {status}'
        )
        
        return jsonify({
            'success': True,
            'is_stable': version.is_stable,
            'message': f'Версия {version.version_number} отмечена как {status}'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка при переключении стабильной версии: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@main.route('/version/<int:id>/change_branch', methods=['POST'])
@login_required
def change_branch(id):
    version = ApkVersion.query.get_or_404(id)
    
    try:
        new_branch = request.json.get('branch')
        if new_branch not in ['release', 'debug', 'beta', 'alpha']:
            return jsonify({'success': False, 'error': 'Недопустимое значение branch'})
            
        # Сохраняем старое значение для лога
        old_branch = version.branch
        version.branch = new_branch
        
        # Логируем изменение
        UserActionLog.log_action(
            current_user,
            'change_branch',
            'version',
            version.id,
            {'branch': old_branch},
            {'branch': new_branch},
            f'Изменен branch версии {version.version_number} с {old_branch} на {new_branch}'
        )
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Branch изменен на {new_branch}',
            'branch': new_branch
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверное имя пользователя или пароль')
            return redirect(url_for('auth.login'))
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('login.html', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@main.route('/application/<int:id>/temp_upload', methods=['POST'])
@login_required
def temp_upload_version(id):
    try:
        application = Application.query.get_or_404(id)
        file = request.files['file']
        
        if not file:
            return jsonify({'error': 'Файл не найден'}), 400
            
        # Проверяем размер файла
        if file.content_length > Config.MAX_FILE_SIZE:
            return jsonify({'error': f'Файл превышает максимальный размер ({Config.MAX_FILE_SIZE / (1024*1024):.0f} MB)'}), 400
        
        filename = secure_filename(file.filename)
        package_name, version_number, branch = ApkVersion.parse_filename(filename)
        
        if not package_name or package_name != application.package_name:
            return jsonify({'error': f'Файл не соответствует формату: {application.package_name}-vX.X.X-branch.apk'}), 400
        
        # Создаем временную директорию, если её нет
        temp_folder = os.path.join(Config.UPLOAD_FOLDER, 'temp', str(id))
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
        
        # Сохраняем файл во временную директорию
        temp_path = os.path.join(temp_folder, filename)
        file.save(temp_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'version_number': version_number,
            'branch': branch,
            'file_size': os.path.getsize(temp_path)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/version/<int:id>/generate_link', methods=['POST'])
@login_required
def generate_download_link(id):
    version = ApkVersion.query.get_or_404(id)
    
    # Создаем одноразовую ссылку
    link = OneTimeDownloadLink(
        version_id=version.id,
        created_by=current_user
    )
    db.session.add(link)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'token': link.token,
        'expires_at': link.expires_at.strftime('%d.%m.%Y %H:%M')
    })

@main.route('/download/<token>')
def download_by_link(token):
    link = OneTimeDownloadLink.query.filter_by(token=token).first_or_404()
    
    # Проверяем, не истек ли срок действия ссылки
    if link.is_expired:
        flash('Срок действия ссылки истек')
        return redirect(url_for('main.index'))
    
    # Проверяем, не была ли ссылка уже использована
    if link.is_used:
        flash('Ссылка уже была использована')
        return redirect(url_for('main.index'))
    
    version = link.version
    file_path = os.path.join(Config.UPLOAD_FOLDER, version.filename)
    
    if not os.path.exists(file_path):
        flash('Файл не найден')
        return redirect(url_for('main.index'))
    
    # Отмечаем ссылку как использованную
    link.is_used = True
    link.used_at = datetime.utcnow()
    
    # Увеличиваем счетчик загрузок
    version.downloads += 1
    
    db.session.commit()
    
    try:
        return send_from_directory(
            Config.UPLOAD_FOLDER,
            version.filename,
            as_attachment=True
        )
    except Exception as e:
        flash(f'Ошибка при скачивании файла: {str(e)}')
        return redirect(url_for('main.index'))

@main.route('/application/<int:id>/multi_temp_upload', methods=['POST'])
@login_required
def multi_temp_upload(id):
    try:
        application = Application.query.get_or_404(id)
        
        if 'files[]' not in request.files:
            return jsonify({'error': 'Файлы не найдены'}), 400
            
        files = request.files.getlist('files[]')
        results = []
        
        # Создаем временную директорию, если её нет
        temp_folder = os.path.join(Config.UPLOAD_FOLDER, 'temp', str(id))
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
            
        for file in files:
            if not file:
                continue
                
            # Проверяем размер файла
            if file.content_length and file.content_length > Config.MAX_FILE_SIZE:
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': f'Файл превышает максимальный размер ({Config.MAX_FILE_SIZE / (1024*1024):.0f} MB)'
                })
                continue
            
            filename = secure_filename(file.filename)
            
            try:
                package_name, version_number, branch = ApkVersion.parse_filename(filename)
                
                if not package_name or package_name != application.package_name:
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': f'Файл не соответствует формату: {application.package_name}-vX.X.X-branch.apk'
                    })
                    continue
                
                # Сохраняем файл во временную директорию
                temp_path = os.path.join(temp_folder, filename)
                file.save(temp_path)
                
                results.append({
                    'success': True,
                    'filename': filename,
                    'version_number': version_number,
                    'branch': branch,
                    'file_size': os.path.getsize(temp_path),
                    'temp_path': temp_path
                })
            except Exception as e:
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/application/<int:id>/save_multi_upload', methods=['POST'])
@login_required
def save_multi_upload(id):
    try:
        application = Application.query.get_or_404(id)
        data = request.json
        
        if not data or 'versions' not in data:
            return jsonify({'error': 'Данные не предоставлены'}), 400
            
        versions_data = data['versions']
        saved_versions = []
        
        for version_data in versions_data:
            try:
                # Получаем путь к временному файлу
                temp_path = os.path.join(
                    Config.UPLOAD_FOLDER, 
                    'temp', 
                    str(id), 
                    version_data['filename']
                )
                
                if not os.path.exists(temp_path):
                    continue
                    
                # Перемещаем файл из временной директории в постоянную
                target_path = os.path.join(
                    Config.UPLOAD_FOLDER, 
                    version_data['filename']
                )
                
                # Если файл уже существует, удаляем его
                if os.path.exists(target_path):
                    os.remove(target_path)
                    
                # Перемещаем файл
                shutil.move(temp_path, target_path)
                
                # Создаем новую версию
                version = ApkVersion(
                    application=application,
                    version_number=version_data['version_number'],
                    branch=version_data['branch'],
                    changelog=version_data.get('changelog', ''),
                    is_stable=version_data.get('is_stable', False),
                    filename=version_data['filename'],
                    file_size=os.path.getsize(target_path),
                    uploader=current_user
                )
                
                db.session.add(version)
                
                # Добавляем флаги, если они есть
                if 'flags' in version_data and version_data['flags']:
                    for flag_data in version_data['flags']:
                        flag = VersionFlag(
                            version=version,
                            flag_type=flag_data['type'],
                            description=flag_data['description'],
                            created_by=current_user
                        )
                        db.session.add(flag)
                
                saved_versions.append({
                    'version_number': version.version_number,
                    'branch': version.branch,
                    'filename': version.filename
                })
                
                # Логируем действие
                UserActionLog.log_action(
                    current_user,
                    'upload_version',
                    'apk_version',
                    version.id,
                    None,
                    {
                        'version': version.version_number,
                        'branch': version.branch,
                        'is_stable': version.is_stable,
                        'filename': version.filename
                    },
                    f'Загружена новая версия {version.version_number} для {application.package_name}'
                )
                
            except Exception as e:
                db.session.rollback()
                return jsonify({
                    'success': False, 
                    'error': f'Ошибка при сохранении версии {version_data["filename"]}: {str(e)}'
                }), 500
        
        # Сохраняем все изменения в базе данных
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Успешно сохранено {len(saved_versions)} версий',
            'saved_versions': saved_versions
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500 