#!/bin/bash

# Создаем директорию для бэкапов если её нет
mkdir -p backups

# Текущая дата для имени файла
DATE=$(date +%Y%m%d_%H%M%S)

# Бэкап базы данных
echo "Creating database backup..."
docker-compose exec -T db pg_dump -U postgres apk_store > backups/db_backup_$DATE.sql

# Бэкап загруженных файлов
echo "Creating uploads backup..."
tar -czf backups/uploads_backup_$DATE.tar.gz uploads/

echo "Backup completed:"
echo "Database: backups/db_backup_$DATE.sql"
echo "Uploads: backups/uploads_backup_$DATE.tar.gz" 