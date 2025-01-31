from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from config import Config
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSON
import os

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Таблица связи пользователей и ролей
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                          back_populates='users')
    uploaded_versions = db.relationship('ApkVersion', back_populates='uploader', lazy='dynamic')
    flags_created = db.relationship('VersionFlag', back_populates='created_by', lazy='dynamic')
    created_links = db.relationship('OneTimeDownloadLink', back_populates='created_by', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission):
        return any(permission in role.permissions for role in self.roles)

    @property
    def is_admin(self):
        return self.has_role('admin')

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(JSON, default=list)
    users = db.relationship('User', secondary=user_roles, lazy='subquery',
                          back_populates='roles')

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    applications = db.relationship('Application', back_populates='category', lazy=True)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_name = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', back_populates='applications')
    versions = db.relationship('ApkVersion', back_populates='application', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_versions(self):
        """Получает список всех версий приложения"""
        return self.versions.order_by(ApkVersion.upload_date.desc()).all()
    
    def get_latest_release(self):
        """Получает последнюю стабильную версию приложения"""
        return self.versions.filter_by(is_stable=True).order_by(ApkVersion.upload_date.desc()).first() or \
               self.versions.order_by(ApkVersion.upload_date.desc()).first()
    
    def get_latest_version(self, branch=None):
        """Получает последнюю версию приложения для указанной ветки"""
        query = self.versions
        if branch:
            query = query.filter_by(branch=branch)
        return query.order_by(ApkVersion.upload_date.desc()).first()
    
    def get_version_count(self):
        """Получает общее количество версий"""
        return self.versions.count()
    
    def get_total_downloads(self):
        """Получает общее количество загрузок всех версий"""
        return db.session.query(db.func.sum(ApkVersion.downloads)).filter_by(application_id=self.id).scalar() or 0

class ApkVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    version_number = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    changelog = db.Column(db.Text)
    is_stable = db.Column(db.Boolean, default=False)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    downloads = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    application = db.relationship('Application', back_populates='versions')
    uploader = db.relationship('User', back_populates='uploaded_versions')
    flags = db.relationship('VersionFlag', back_populates='version', cascade='all, delete-orphan')
    download_links = db.relationship('OneTimeDownloadLink', back_populates='version', cascade='all, delete-orphan')
    
    @staticmethod
    def parse_filename(filename):
        """
        Парсит имя файла APK для извлечения package_name, version_number и branch.
        Ожидаемый формат: package_name-vX.X.X-branch.apk
        
        Возвращает кортеж (package_name, version_number, branch) или (None, None, None) если формат неверный.
        """
        try:
            # Убираем расширение .apk
            if not filename.lower().endswith('.apk'):
                return None, None, None
            
            base_name = filename[:-4]  # удаляем '.apk'
            
            # Разбиваем на части по дефису
            parts = base_name.split('-')
            
            # Должно быть 2 или 3 части: package_name, version, [branch]
            if len(parts) < 2 or len(parts) > 3:
                return None, None, None
            
            package_name = parts[0]
            
            # Проверяем версию (должна начинаться с 'v')
            if not parts[1].startswith('v'):
                return None, None, None
            
            version_number = parts[1][1:]  # убираем 'v'
            
            # Если есть branch, берем его, иначе используем 'release'
            branch = parts[2] if len(parts) > 2 else 'release'
            
            return package_name, version_number, branch
            
        except Exception as e:
            print(f"Error parsing filename {filename}: {str(e)}")
            return None, None, None

class VersionFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('apk_version.id'), nullable=False)
    flag_type = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    version = db.relationship('ApkVersion', back_populates='flags')
    created_by = db.relationship('User', back_populates='flags_created')

class UserActionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(128), nullable=False)
    entity_type = db.Column(db.String(64), nullable=False)
    entity_id = db.Column(db.Integer)
    old_value = db.Column(JSON)
    new_value = db.Column(JSON)
    description = db.Column(db.Text)

    @staticmethod
    def log_action(user, action, entity_type, entity_id=None, old_value=None, new_value=None, description=None):
        log = UserActionLog(
            user_id=user.id,
            username=user.username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            description=description
        )
        db.session.add(log)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error logging action: {str(e)}")

class OneTimeDownloadLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey('apk_version.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    used_by_ip = db.Column(db.String(45))
    
    version = db.relationship('ApkVersion', back_populates='download_links')
    created_by = db.relationship('User', back_populates='created_links')
    
    def is_valid(self):
        return not self.is_used and datetime.utcnow() <= self.expires_at
    
    def mark_as_used(self, ip_address):
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.used_by_ip = ip_address
        db.session.commit()
    
    @staticmethod
    def generate_token():
        return os.urandom(32).hex()
    
    @staticmethod
    def create_for_version(version, user, expires_in=None):
        if expires_in is None:
            expires_in = Config.DOWNLOAD_LINK_EXPIRY
            
        link = OneTimeDownloadLink(
            token=OneTimeDownloadLink.generate_token(),
            version_id=version.id,
            created_by_id=user.id,
            expires_at=datetime.utcnow() + expires_in
        )
        db.session.add(link)
        db.session.commit()
        return link 