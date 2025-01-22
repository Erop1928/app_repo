#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <database_backup.sql> <uploads_backup.tar.gz>"
    exit 1
fi

DB_BACKUP=$1
UPLOADS_BACKUP=$2

if [ ! -f "$DB_BACKUP" ]; then
    echo "Database backup file not found: $DB_BACKUP"
    exit 1
fi

if [ ! -f "$UPLOADS_BACKUP" ]; then
    echo "Uploads backup file not found: $UPLOADS_BACKUP"
    exit 1
fi

# Восстановление базы данных
echo "Restoring database..."
docker-compose exec -T db psql -U postgres -d apk_store -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker-compose exec -T db psql -U postgres apk_store < "$DB_BACKUP"

# Восстановление файлов
echo "Restoring uploads..."
rm -rf uploads/*
tar -xzf "$UPLOADS_BACKUP" -C .

echo "Restore completed!" 