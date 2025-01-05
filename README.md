# APK Repository

Веб-сервис для хранения и управления APK файлами с поддержкой версионирования, категорий и API.

## Возможности

- Управление приложениями и версиями
- Категоризация приложений
- Drag-and-drop загрузка файлов
- Пакетная загрузка версий
- Управление пользователями и ролями
- REST API с Basic Auth
- Одноразовые ссылки для скачивания
- Журналирование действий пользователей
- Поддержка Nginx и Gunicorn для production-окружения

## Требования

- Python 3.11+ (для локальной установки)
- pip (для локальной установки)
- virtualenv (опционально, для локальной установки)
- Docker и Docker Compose (для запуска в контейнере)

## Локальная установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd apk-repository
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env:
```bash
cp .env.example .env
```

5. Отредактируйте .env под свои нужды:
```
FLASK_APP=main.py
FLASK_ENV=development
SECRET_KEY=your-super-secret-key
DATABASE_URL=sqlite:///app.db
LOGS_DATABASE_URL=sqlite:///logs.db
HOST_URL=http://localhost:5000
```

6. Инициализируйте базу данных:
```bash
python init_db.py
```

7. Запустите приложение:
```bash
python main.py
```

Приложение будет доступно по адресу: http://localhost:5000

## Запуск в Docker

### Быстрое развертывание (рекомендуется)

Для быстрого развертывания на сервере используйте скрипт deploy.sh:

```bash
chmod +x deploy.sh
./deploy.sh
```

Скрипт автоматически:
- Установит Docker и Docker Compose, если они отсутствуют
- Создаст необходимые директории
- Сгенерирует случайный SECRET_KEY
- Настроит HOST_URL
- Запустит контейнеры

### Ручная установка

1. Создайте необходимые директории:
```bash
mkdir -p uploads instance
```

2. Создайте файл .env:
```bash
cp .env.example .env
```

3. Отредактируйте .env, указав нужные значения переменных окружения.

4. Соберите и запустите контейнеры:
```bash
docker-compose up -d
```

Приложение будет доступно по адресу: http://localhost

### Управление контейнерами

- Просмотр логов:
```bash
docker-compose logs -f
```

- Остановка контейнеров:
```bash
docker-compose down
```

- Пересборка после изменений:
```bash
docker-compose build
docker-compose up -d
```

## Production-окружение

В production-окружении приложение работает через:
- Gunicorn (WSGI-сервер)
- Nginx (обратный прокси-сервер)

Преимущества такой конфигурации:
- Эффективная обработка статических файлов через Nginx
- Балансировка нагрузки через несколько воркеров Gunicorn
- Поддержка HTTPS (настраивается в nginx.conf)
- Улучшенная безопасность
- Оптимизированная производительность

### Настройка SSL/HTTPS

Для настройки HTTPS:

1. Получите SSL-сертификат (например, через Let's Encrypt)
2. Добавьте в nginx.conf:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # ... остальные настройки ...
}
```

3. Обновите HOST_URL в .env на https://your-domain.com

## Первый вход

После установки будет создан пользователь с правами администратора:
- Логин: admin
- Пароль: admin

Рекомендуется сменить пароль после первого входа.

## Структура проекта

```
.
├── app/                    # Основной код приложения
│   ├── templates/         # HTML шаблоны
│   ├── static/           # Статические файлы (CSS, JS)
│   ├── __init__.py      # Инициализация приложения
│   ├── models.py        # Модели данных
│   ├── forms.py         # Формы
│   ├── routes.py        # Маршруты веб-интерфейса
│   └── api.py           # REST API
├── instance/             # Данные приложения (БД)
├── uploads/             # Загруженные файлы
├── requirements.txt     # Зависимости Python
├── config.py           # Конфигурация
├── main.py            # Точка входа
├── init_db.py        # Скрипт инициализации БД
├── Dockerfile        # Конфигурация Docker
└── docker-compose.yml # Конфигурация Docker Compose
```

## API

Подробная документация по API доступна в файле [API.md](API.md)

## Разработка

### Структура базы данных

- **User**: Пользователи системы
- **Role**: Роли и разрешения
- **Category**: Категории приложений
- **Application**: Приложения
- **ApkVersion**: Версии приложений
- **VersionFlag**: Флаги версий
- **UserActionLog**: Журнал действий
- **OneTimeDownloadLink**: Одноразовые ссылки

### Права доступа

- **admin**: Полный доступ ко всем функциям
- **user**: Загрузка и редактирование версий

## Безопасность

- Все пароли хешируются
- Используется CSRF защита форм
- API использует Basic Auth
- Одноразовые ссылки имеют ограниченный срок действия
- Ведется журнал всех действий пользователей

## Лицензия

MIT 