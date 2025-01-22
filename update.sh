#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Создаем директорию для бэкапов если её нет
mkdir -v backups

# Текущая дата для имени файла
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DB="backups/db_backup_$DATE.sql"
BACKUP_FILES="backups/uploads_backup_$DATE.tar.gz"

# Функция для создания бэкапа
create_backup() {
    log "Creating backup..."
    
    # Проверяем существование базы данных
    log "Checking database existence..."
    if ! docker-compose exec -T db psql -U postgres -lqt | cut -d \| -f 1 | grep -qw apk_store; then
        warning "Database 'apk_store' does not exist, skipping database backup"
        CREATE_DB=true
    else
        # Бэкап базы данных
        log "Creating database backup..."
        if docker-compose exec -T db pg_dump -U postgres apk_store > "$BACKUP_DB"; then
            log "Database backup created: $BACKUP_DB"
        else
            error "Failed to create database backup"
            return 1
        fi
    fi
    
    # Проверяем существование директории uploads
    if [ -d "uploads" ] && [ "$(ls -A uploads 2>/dev/null)" ]; then
        # Бэкап загруженных файлов
        log "Creating uploads backup..."
        if tar -czf "$BACKUP_FILES" uploads/; then
            log "Uploads backup created: $BACKUP_FILES"
        else
            error "Failed to create uploads backup"
            return 1
        fi
    else
        warning "Uploads directory is empty or does not exist, skipping files backup"
        mkdir -p uploads
    fi
    
    log "Backup completed successfully"
    return 0
}

# Функция для инициализации базы данных
init_database() {
    log "Initializing database..."
    
    # Создаем базу данных если она не существует
    if ! docker-compose exec -T db psql -U postgres -lqt | cut -d \| -f 1 | grep -qw apk_store; then
        log "Creating database 'apk_store'..."
        if ! docker-compose exec -T db psql -U postgres -c "CREATE DATABASE apk_store;"; then
            error "Failed to create database"
            return 1
        fi
    fi
    
    return 0
}

# Функция для восстановления из бэкапа
restore_backup() {
    local db_backup=$1
    local files_backup=$2
    
    log "Restoring from backup..."
    
    # Восстановление базы данных
    log "Restoring database..."
    if docker-compose exec -T db psql -U postgres -d apk_store -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
       docker-compose exec -T db psql -U postgres apk_store < "$db_backup"; then
        log "Database restored successfully"
    else
        error "Failed to restore database"
        return 1
    fi
    
    # Восстановление файлов
    log "Restoring uploads..."
    if rm -rf uploads/* && tar -xzf "$files_backup" -C .; then
        log "Files restored successfully"
    else
        error "Failed to restore files"
        return 1
    fi
    
    log "Restore completed successfully"
    return 0
}

# Основной процесс обновления
main() {
    log "Starting update process..."
    
    # Создаем бэкап перед обновлением
    if ! create_backup; then
        error "Backup failed, aborting update"
        exit 1
    fi
    
    # Получаем последние изменения из git
    log "Pulling latest changes from git..."
    if ! git pull; then
        error "Failed to pull changes from git"
        warning "Attempting to restore from backup..."
        restore_backup "$BACKUP_DB" "$BACKUP_FILES"
        exit 1
    fi
    
    # Останавливаем контейнеры
    log "Stopping containers..."
    if ! docker-compose down; then
        error "Failed to stop containers"
        warning "Attempting to restore from backup..."
        restore_backup "$BACKUP_DB" "$BACKUP_FILES"
        exit 1
    fi
    
    # Пересобираем образы
    log "Rebuilding containers..."
    if ! docker-compose build; then
        error "Failed to build containers"
        warning "Attempting to restore from backup..."
        restore_backup "$BACKUP_DB" "$BACKUP_FILES"
        exit 1
    fi
    
    # Запускаем контейнеры
    log "Starting containers..."
    if ! docker-compose up -d; then
        error "Failed to start containers"
        warning "Attempting to restore from backup..."
        restore_backup "$BACKUP_DB" "$BACKUP_FILES"
        exit 1
    fi
    
    # Ждем, пока база данных запустится
    log "Waiting for database to start..."
    sleep 10
    
    # Инициализируем базу данных если нужно
    if ! init_database; then
        error "Failed to initialize database"
        warning "Attempting to restore from backup..."
        restore_backup "$BACKUP_DB" "$BACKUP_FILES"
        exit 1
    fi
    
    # Применяем миграции базы данных
    log "Applying database migrations..."
    if ! docker-compose exec -T web flask db upgrade; then
        error "Failed to apply migrations"
        warning "Attempting to restore from backup..."
        restore_backup "$BACKUP_DB" "$BACKUP_FILES"
        exit 1
    fi
    
    log "Update completed successfully!"
    
    # Очистка старых бэкапов (оставляем последние 5)
    log "Cleaning up old backups..."
    ls -t backups/db_backup_* 2>/dev/null | tail -n +6 | xargs -r rm
    ls -t backups/uploads_backup_* 2>/dev/null | tail -n +6 | xargs -r rm
}

# Запускаем основной процесс
main
