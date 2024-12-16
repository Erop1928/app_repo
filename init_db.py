from app import db, create_app
from app.models import User, Category, Role, UserActionLog
from config import Config

def init_db():
    app = create_app()
    
    with app.app_context():
        # Пересоздаем все таблицы
        db.drop_all()
        db.create_all()
        
        # Создаем роль администратора
        admin_role = Role(
            name='admin',
            description='Администратор системы',
            permissions=[
                'add_application',
                'edit_application',
                'delete_application',
                'add_version',
                'edit_version',
                'delete_version',
                'manage_users',
                'manage_roles',
                'view_logs'
            ]
        )
        db.session.add(admin_role)
        
        # Создаем роль пользователя
        user_role = Role(
            name='user',
            description='Обычный пользователь',
            permissions=[
                'add_version',
                'edit_version'
            ]
        )
        db.session.add(user_role)
        
        # Создаем пользователя admin
        admin = User(username='admin', email='admin@example.com', is_active=True)
        admin.set_password('admin')
        admin.roles.append(admin_role)
        db.session.add(admin)
        
        # Создаем категории
        categories = [
            {
                'name': 'Основные приложения',
                'description': 'Основные приложения компании'
            },
            {
                'name': 'Инструменты',
                'description': 'Утилиты и инструменты для разработки и тестирования'
            },
            {
                'name': 'Приложения партнеров',
                'description': 'Приложения от партнеров и интег��аторов'
            },
            {
                'name': 'Debug/SDK',
                'description': 'Отладочные версии и SDK для разработчиков'
            }
        ]
        
        for category_data in categories:
            category = Category(
                name=category_data['name'],
                description=category_data['description']
            )
            db.session.add(category)
        
        # Сохраняем изменения
        db.session.commit()
        
        # Создаем первую запись в логах
        UserActionLog.log_action(
            admin,
            'init_database',
            'system',
            None,
            None,
            None,
            'Инициализация базы данных'
        )
        
        print('База данных успешно инициализирована')
        print('Создан пользователь admin с паролем admin')
        print('Созданы роли:')
        print('- admin (все права)')
        print('- user (добавление и редактирование версий)')
        print('Созданы категории:')
        for category in categories:
            print(f'- {category["name"]}')

if __name__ == '__main__':
    init_db() 