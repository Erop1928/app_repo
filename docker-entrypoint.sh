#!/bin/bash

# Проверка и создание необходимых директорий
mkdir -p /app/instance
mkdir -p /app/uploads

# Установка правильных прав доступа
chown -R app:app /app/instance
chown -R app:app /app/uploads
chmod 755 /app/instance
chmod 755 /app/uploads

# Переключение на пользователя app для всех последующих операций
exec gosu app bash -c '
# Инициализация базы данных, если она еще не существует
if [ ! -f "/app/instance/app.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi

# Запуск gunicorn
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --timeout 600 \
    --access-logfile - \
    --error-logfile - \
    "main:app"
' 