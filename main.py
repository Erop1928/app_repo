from app import create_app, db
import os
from config import Config

app = create_app()

def init_directories():
    """Создаем необходимые директории при запуске"""
    directories = [
        Config.UPLOAD_FOLDER,
        os.path.dirname(Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')),
        os.path.dirname(Config.LOGS_DATABASE_URI.replace('sqlite:///', ''))
    ]
    
    for directory in directories:
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"Создана директория: {directory}")
            except Exception as e:
                print(f"Ошибка при создании директории {directory}: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        init_directories()
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
