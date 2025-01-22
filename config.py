import os
from dotenv import load_dotenv
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    
    # Пути к базам данных
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_BINDS = {}
    
    # Папка для загрузок
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or \
        os.path.join(basedir, 'uploads')
    
    # Настройки загрузки файлов
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024 * 1024  # 5 GB
    MAX_FILES_COUNT = 50  # Максимальное количество файлов за раз
    MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB на файл
    
    # Настройки одноразовых ссылок
    HOST_URL = os.environ.get('HOST_URL', 'http://192.168.77.171:5000')
    DOWNLOAD_LINK_EXPIRY = timedelta(hours=24)  # Срок действия ссылки
    
    # Разрешаем отслеживание изменений
    SQLALCHEMY_TRACK_MODIFICATIONS = True