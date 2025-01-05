#!/bin/bash

# Ожидание создания директории instance
until [ -d "/app/instance" ]; do
  echo "Waiting for instance directory..."
  sleep 1
done

# Инициализация базы данных, если она еще не существует
if [ ! -f "/app/instance/app.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi

# Установка правильных прав для директорий
chown -R nobody:nobody /app/uploads
chmod -R 755 /app/uploads

# Запуск gunicorn
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --timeout 600 \
    --access-logfile - \
    --error-logfile - \
    "main:app" 