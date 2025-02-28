from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Настраиваем обработку CSRF для AJAX-запросов
    @app.after_request
    def add_csrf_header(response):
        response.headers.set('X-CSRFToken', csrf.generate_csrf())
        return response
    
    # Обработка ошибок CSRF через обработчик ошибок Flask
    @app.errorhandler(400)
    def handle_csrf_error(e):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, error='CSRF ошибка: неверный или отсутствующий токен'), 400
        return e

    from app.routes import main, auth, admin
    from app.api import api

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(api)

    return app 