#!/bin/bash

# Проверка и создание необходимых директорий
mkdir -p /app/instance
mkdir -p /app/uploads

# Установка правильных прав доступа
chmod 777 /app/instance
chmod 777 /app/uploads

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