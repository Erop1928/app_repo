from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from config import Config
from sqlalchemy.ext.hybrid import hybrid_property
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
    email = db.Column(db.String(120), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                          backref=db.backref('users', lazy=True))

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
    permissions = db.Column(db.JSON, default=list)  # Список разрешений

    def __repr__(self):
        return f'<Role {self.name}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    applications = db.relationship('Application', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_name = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    versions = db.relationship('ApkVersion', backref='application', lazy=True,
                             order_by='ApkVersion.version_number.desc()')

    def __repr__(self):
        return f'<Application {self.name}>'

    def get_latest_release(self):
        """Возвращает последнюю стабильную версию приложения"""
        # Сначала ищем версию с отметкой is_stable
        stable_version = ApkVersion.query.filter_by(
            application_id=self.id,
            is_stable=True
        ).order_by(ApkVersion.upload_date.desc()).first()
        
        if stable_version:
            return stable_version
            
        # Если стабильной версии нет, ищем последний релиз
        release_version = ApkVersion.query.filter_by(
            application_id=self.id,
            branch='release'
        ).order_by(ApkVersion.upload_date.desc()).first()
        
        if release_version:
            return release_version
            
        # Если и релиза нет, возвращаем последнюю версию
        return ApkVersion.query.filter_by(
            application_id=self.id
        ).order_by(ApkVersion.upload_date.desc()).first()

class ApkVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    version_number = db.Column(db.String(64), nullable=False)
    branch = db.Column(db.String(64))
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    changelog = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    downloads = db.Column(db.Integer, default=0)
    is_stable = db.Column(db.Boolean, default=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploader = db.relationship('User', backref=db.backref('uploads', lazy=True))
    flags = db.relationship('VersionFlag', backref='version', lazy=True)

    def __repr__(self):
        return f'<ApkVersion {self.version_number} ({self.branch})>'

    def _version_tuple(self):
        """Преобразует номер версии в кортеж для сравнения"""
        try:
            return tuple(map(int, self.version_number.split('.')))
        except (ValueError, AttributeError):
            return (0,)

    def __lt__(self, other):
        """Определяем оператор < для правильной сортировки версий"""
        if not isinstance(other, ApkVersion):
            return NotImplemented
        return self._version_tuple() < other._version_tuple()

    def __gt__(self, other):
        """Определяем оператор > для правильной сортировки версий"""
        if not isinstance(other, ApkVersion):
            return NotImplemented
        return self._version_tuple() > other._version_tuple()

    @staticmethod
    def parse_filename(filename):
        """Парсит имя файла для извлечения информации о версии"""
        try:
            # Пример: com.tpsterminal-v4.2.57.4-release.apk
            name_parts = filename.replace('.apk', '').split('-')
            package_name = name_parts[0]
            version = name_parts[1].replace('v', '')
            branch = name_parts[2] if len(name_parts) > 2 else 'release'
            return package_name, version, branch
        except:
            return None, None, None

class VersionFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('apk_version.id'), nullable=False)
    flag_type = db.Column(db.String(64), nullable=False)  # например, bug, feature, warning
    description = db.Column(db.String(255), nullable=False)  # например, "не работает Wiegand"
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.relationship('User', backref=db.backref('flags_created', lazy=True))

    def __repr__(self):
        return f'<VersionFlag {self.flag_type}: {self.description}>'

class UserActionLog(db.Model):
    __bind_key__ = 'logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(128), nullable=False)
    entity_type = db.Column(db.String(64), nullable=False)  # тип объекта: user, role, application, version и т.д.
    entity_id = db.Column(db.Integer)  # ID измененного объекта
    old_value = db.Column(db.JSON)  # значение до изменения
    new_value = db.Column(db.JSON)  # значение после изменения
    description = db.Column(db.Text)  # дополнительное описание действия

    def __repr__(self):
        return f'<UserActionLog {self.action} by {self.username}>'

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
    
    version = db.relationship('ApkVersion', backref=db.backref('download_links', lazy=True))
    created_by = db.relationship('User', backref=db.backref('created_links', lazy=True))
    
    def __repr__(self):
        return f'<OneTimeDownloadLink {self.token}>'
    
    def is_valid(self):
        """Проверяет, действительна ли ссылка"""
        return not self.is_used and datetime.utcnow() <= self.expires_at
    
    def mark_as_used(self, ip_address):
        """Отмечает ссылку как использованную"""
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.used_by_ip = ip_address
        db.session.commit()
    
    @staticmethod
    def generate_token():
        """Генерирует уникальный токен"""
        return os.urandom(32).hex()
    
    @staticmethod
    def create_for_version(version, user, expires_in=None):
        """Создает новую одноразовую ссылку для версии"""
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
  