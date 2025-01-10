from app import create_app, db
import os
from config import Config

app = create_app()

def init_directories():
    """Создаем необходимые директории при запуске"""
    if not os.path.exists(Config.UPLOAD_FOLDER):
        try:
            os.makedirs(Config.UPLOAD_FOLDER)
            print(f"Создана директория: {Config.UPLOAD_FOLDER}")
        except Exception as e:
            print(f"Ошибка при создании директории {Config.UPLOAD_FOLDER}: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        init_directories()
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
