from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Category, Application, ApkVersion, VersionFlag, Role, UserActionLog, OneTimeDownloadLink
from app.forms import (LoginForm, CategoryForm, ApplicationForm, UploadApkForm, 
                      AddFlagForm, BatchUploadForm, UserForm, RoleForm)
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
    flag_form = AddFlagForm()
    return render_template('application_details.html', 
                         application=application,
                         flag_form=flag_form)

@main.route('/application/<int:id>/upload', methods=['GET', 'POST'])
@login_required
def upload_version(id):
    application = Application.query.get_or_404(id)
    form = UploadApkForm()
    
    if form.validate_on_submit():
        try:
            file = form.apk_file.data
            if not file:
                flash('Файл не выбран', 'error')
                return redirect(url_for('main.upload_version', id=application.id))

            # Создаем директорию для загрузок, если её нет
            upload_folder = Config.UPLOAD_FOLDER
            os.makedirs(upload_folder, exist_ok=True)
            
            # Генерируем уникальное имя файла
            original_filename = secure_filename(file.filename)
            filename = f"{application.package_name}-v{form.version_number.data}-{form.branch.data}.apk"
            file_path = os.path.join(upload_folder, filename)
            
            current_app.logger.info(f'Сохраняем файл: {file_path}')
            
            # Сохраняем файл
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            
            current_app.logger.info(f'Файл сохранен, размер: {file_size}')
            
            # Создаем новую версию
            version = ApkVersion(
                application_id=application.id,
                version_number=form.version_number.data,
                branch=form.branch.data,
                changelog=form.changelog.data,
                is_stable=form.is_stable.data,
                filename=filename,
                file_size=file_size,
                uploader=current_user
            )
            
            current_app.logger.info('Создаем запись в базе данных')
            
            # Если это стабильная версия, сбрасываем флаг у других версий
            if version.is_stable:
                ApkVersion.query.filter_by(
                    application_id=application.id,
                    is_stable=True
                ).update({'is_stable': False})
            
            db.session.add(version)
            db.session.commit()
            
            current_app.logger.info('Запись создана успешно')
            
            flash('Новая версия успешно загружена', 'success')
            return redirect(url_for('main.application_details', id=application.id))
            
        except Exception as e:
            current_app.logger.error(f'Ошибка при загрузке: {str(e)}')
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            db.session.rollback()
            flash(f'Ошибка при загрузке файла: {str(e)}', 'error')
            return redirect(url_for('main.upload_version', id=application.id))
    
    return render_template('upload_version.html', 
                         title='Загрузка версии',
                         form=form,
                         application=application)

@main.route('/version/<int:id>/flag', methods=['POST'])
@login_required
def add_flag(id):
    version = ApkVersion.query.get_or_404(id)
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
    
    if version.uploader != current_user:
        flash('У вас нет прав на удаление этой версии')
        return redirect(url_for('main.application_details', id=application_id))
    
    file_path = os.path.join(Config.UPLOAD_FOLDER, version.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.session.delete(version)
    db.session.commit()
    
    flash('Версия удалена')
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
    
    try:
        version.is_stable = not version.is_stable
        db.session.commit()
        
        status = 'стабильной' if version.is_stable else 'нестабильной'
        flash(f'Версия {version.version_number} отмечена как {status}')
        
        return jsonify({
            'success': True,
            'is_stable': version.is_stable,
            'message': f'Версия {version.version_number} отмечена как {status}'
        })
    except Exception as e:
        db.session.rollback()
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

@main.route('/application/<int:id>/batch_upload', methods=['GET', 'POST'])
@login_required
def batch_upload_versions(id):
    try:
        print("Batch upload started")
        application = Application.query.get_or_404(id)
        form = BatchUploadForm()
        
        print(f"Request method: {request.method}")
        print(f"Form validation: {form.validate_on_submit()}")
        print(f"Form errors: {form.errors}")
        print(f"Request form data: {request.form}")
        print(f"Request files: {request.files}")
        
        if form.validate_on_submit():
            print("Form validated successfully")
            uploaded_versions = []
            temp_folder = os.path.join(Config.UPLOAD_FOLDER, 'temp', str(id))
            
            try:
                # Получаем информацию о версиях из формы
                versions_info = request.form.get('versions_info', '[]')
                print(f"Raw versions info: {versions_info}")
                versions_info = json.loads(versions_info)
                print(f"Parsed versions info: {versions_info}")
                
                for info in versions_info:
                    print(f"Processing version info: {info}")
                    filename = info['filename']
                    version_number = info['version_number']
                    branch = info['branch']
                    changelog = info.get('changelog', '')
                    is_stable = info.get('is_stable', False)
                    
                    # Проверяем существование версии
                    existing_version = ApkVersion.query.filter_by(
                        application_id=application.id,
                        version_number=version_number,
                        branch=branch
                    ).first()
                    
                    if existing_version:
                        error_msg = f'Версия {version_number} ({branch}) уже существует'
                        print(f"Error: {error_msg}")
                        return jsonify({
                            'success': False,
                            'error': error_msg
                        })
                    
                    # Перемещаем файл из временной директории
                    temp_path = os.path.join(temp_folder, filename)
                    final_path = os.path.join(Config.UPLOAD_FOLDER, filename)
                    print(f"Moving file from {temp_path} to {final_path}")
                    
                    if os.path.exists(temp_path):
                        shutil.move(temp_path, final_path)
                        print(f"File moved successfully")
                        
                        version = ApkVersion(
                            application_id=application.id,
                            version_number=version_number,
                            branch=branch,
                            changelog=changelog,
                            is_stable=is_stable,
                            filename=filename,
                            file_size=os.path.getsize(final_path),
                            uploader=current_user
                        )
                        db.session.add(version)
                        uploaded_versions.append(version)
                        print(f"Version added to session: {version_number}")
                    else:
                        print(f"Error: Temp file not found at {temp_path}")
                
                if uploaded_versions:
                    try:
                        print("Committing changes to database")
                        db.session.commit()
                        
                        # Очищаем временную директорию
                        if os.path.exists(temp_folder):
                            print(f"Cleaning up temp folder: {temp_folder}")
                            shutil.rmtree(temp_folder)
                        
                        # Логируем пакетную загрузку
                        UserActionLog.log_action(
                            current_user,
                            'batch_upload_versions',
                            'application',
                            application.id,
                            None,
                            {
                                'uploaded_versions': [
                                    {
                                        'version': v.version_number,
                                        'branch': v.branch,
                                        'filename': v.filename
                                    } for v in uploaded_versions
                                ]
                            },
                            f'Загружено {len(uploaded_versions)} версий'
                        )
                        
                        success_msg = f'Загружено {len(uploaded_versions)} версий'
                        print(f"Success: {success_msg}")
                        return jsonify({
                            'success': True,
                            'message': success_msg,
                            'redirect_url': url_for('main.application_details', id=application.id)
                        })
                        
                    except Exception as e:
                        db.session.rollback()
                        error_msg = f'Ошибка при сохранении версий: {str(e)}'
                        print(f"Error during commit: {error_msg}")
                        return jsonify({'success': False, 'error': error_msg})
                else:
                    error_msg = 'Ни один файл не был загружен'
                    print(f"Error: {error_msg}")
                    return jsonify({'success': False, 'error': error_msg})
                    
            except json.JSONDecodeError as e:
                error_msg = f'Ошибка при разборе данных версий: {str(e)}'
                print(f"JSON decode error: {error_msg}")
                return jsonify({'success': False, 'error': error_msg})
                
            except Exception as e:
                error_msg = f'Ошибка при обработке загрузки: {str(e)}'
                print(f"General error: {error_msg}")
                return jsonify({'success': False, 'error': error_msg})
        else:
            print(f"Form validation failed: {form.errors}")
        
        return render_template('batch_upload.html', form=form, application=application)
        
    except Exception as e:
        error_msg = f'Ошибка: {str(e)}'
        print(f"Unexpected error: {error_msg}")
        return jsonify({'success': False, 'error': error_msg})

@main.route('/application/<int:id>/batch_edit', methods=['GET', 'POST'])
@login_required
def batch_edit_versions(id):
    application = Application.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            for version in application.versions:
                changelog = request.form.get(f'changelog_{version.id}', '')
                is_stable = request.form.get(f'is_stable_{version.id}', False) == 'on'
                
                version.changelog = changelog
                version.is_stable = is_stable
            
            db.session.commit()
            flash('Изменения сохранены')
            return redirect(url_for('main.application_details', id=application.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении изменений: {str(e)}')
    
    # Получаем только последние загруженные версии (например, за последние 24 часа)
    recent_versions = ApkVersion.query.filter_by(application_id=application.id)\
        .order_by(ApkVersion.upload_date.desc())\
        .limit(10)\
        .all()
    
    return render_template('batch_edit.html', 
                         application=application,
                         versions=recent_versions)

@admin.route('/logs')
@login_required
@admin_required
def logs_list():
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Фильтры
    username = request.args.get('username', '')
    action = request.args.get('action', '')
    
    # Базовый запрос
    query = UserActionLog.query.order_by(UserActionLog.timestamp.desc())
    
    # Применяем фильтры
    if username:
        query = query.filter(UserActionLog.username.ilike(f'%{username}%'))
    if action:
        query = query.filter(UserActionLog.action.ilike(f'%{action}%'))
    
    # Пагинация
    logs = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/logs.html', logs=logs)

@main.route('/version/<int:id>/generate_link', methods=['POST'])
@login_required
def generate_download_link(id):
    try:
        version = ApkVersion.query.get_or_404(id)
        
        # Создаем одноразовую ссылку
        link = OneTimeDownloadLink.create_for_version(version, current_user)
        
        # Логируем создание ссылки
        UserActionLog.log_action(
            current_user,
            'generate_download_link',
            'version',
            version.id,
            None,
            {
                'link_token': link.token,
                'expires_at': link.expires_at.isoformat()
            },
            f'Создана одноразовая ссылка для версии {version.version_number}'
        )
        
        # Формируем полный URL для скачивания
        download_url = f"{Config.HOST_URL}/download/{link.token}"
        
        return jsonify({
            'success': True,
            'download_url': download_url,
            'expires_at': link.expires_at.strftime('%d.%m.%Y %H:%M:%S')
        })
        
    except Exception as e:
        print(f'Error generating download link: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'Ошибка при создании ссылки'
        }), 500

@main.route('/download/<token>')
def download_by_link(token):
    try:
        # Находим ссылку
        link = OneTimeDownloadLink.query.filter_by(token=token).first_or_404()
        
        # Проверяем валидность ссылки
        if not link.is_valid():
            if link.is_used:
                flash('Эта ссылка уже была использована')
            else:
                flash('Срок действия ссылки истек')
            return redirect(url_for('main.index'))
        
        # Получаем IP-адрес ользователя
        ip_address = request.remote_addr
        
        # Отмечаем ссылку как использованную
        link.mark_as_used(ip_address)
        
        # Логируем скачивание
        UserActionLog.log_action(
            link.created_by,  # используем создателя ссылки как пользователя
            'download_by_link',
            'version',
            link.version_id,
            None,
            {
                'link_token': token,
                'ip_address': ip_address
            },
            f'Скачивание по одноразовой ссылке версии {link.version.version_number}'
        )
        
        # Увеличиваем счетчик загрузок
        link.version.downloads += 1
        db.session.commit()
        
        return send_from_directory(
            Config.UPLOAD_FOLDER,
            link.version.filename,
            as_attachment=True
        )
        
    except Exception as e:
        flash('Ошибка при скачивании файла')
        print(f'Error downloading by link: {str(e)}')
        return redirect(url_for('main.index')) 