#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Определяем пути к директориям
DATA_DIR="./pgdata"
UPLOADS_DIR="./uploads"
BACKUPS_DIR="./backups"
LOGS_DIR="./logs"

# Создаем необходимые директории
mkdir -p "$DATA_DIR" "$UPLOADS_DIR" "$BACKUPS_DIR" "$LOGS_DIR"

# Определяем текущий лог файл
CURRENT_LOG="$LOGS_DIR/$(date +%Y%m%d_%H).log"

# Функция для логирования
write_log() {
    local level=$1
    local message=$2
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    local log_message="[$timestamp] $level: $message"
    
    # Проверяем, нужно ли создать новый лог файл
    local new_log="$LOGS_DIR/$(date +%Y%m%d_%H).log"
    if [ "$new_log" != "$CURRENT_LOG" ]; then
        CURRENT_LOG="$new_log"
    fi
    
    # Записываем в лог файл
    echo "$log_message" >> "$CURRENT_LOG"
    
    # Выводим в консоль с цветом
    case $level in
        "INFO")
            echo -e "${GREEN}$log_message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}$log_message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}$log_message${NC}"
            ;;
        *)
            echo "$log_message"
            ;;
    esac
}

# Функции для разных уровней логирования
log() {
    write_log "INFO" "$1"
}

error() {
    write_log "ERROR" "$1"
}

warning() {
    write_log "WARNING" "$1"
}

# Очистка старых логов (оставляем последние 24 часа)
cleanup_logs() {
    find "$LOGS_DIR" -name "*.log" -type f -mtime +1 -delete
}

# Текущая дата для имени файла
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DB="$BACKUPS_DIR/db_backup_$DATE.sql"
BACKUP_FILES="$BACKUPS_DIR/uploads_backup_$DATE.tar.gz"

# Функция для создания бэкапа
create_backup() {
    log "Creating backup..."
    
    # Проверяем существование базы данных
    log "Checking database existence..."
    if ! docker-compose exec -T db psql -U postgres -lqt | cut -d \| -f 1 | grep -qw app_db; then
        warning "Database 'app_db' does not exist, skipping database backup"
        CREATE_DB=true
    else
        # Бэкап базы данных
        log "Creating database backup..."
        if docker-compose exec -T db pg_dump -U postgres app_db > "$BACKUP_DB"; then
            log "Database backup created: $BACKUP_DB"
        else
            error "Failed to create database backup"
            return 1
        fi
    fi
    
    # Проверяем существование директории uploads
    if [ -d "$UPLOADS_DIR" ] && [ "$(ls -A $UPLOADS_DIR 2>/dev/null)" ]; then
        # Бэкап загруженных файлов
        log "Creating uploads backup..."
        if tar -czf "$BACKUP_FILES" -C "$UPLOADS_DIR" .; then
            log "Uploads backup created: $BACKUP_FILES"
        else
            error "Failed to create uploads backup"
            return 1
        fi
    else
        warning "Uploads directory is empty or does not exist, skipping files backup"
        mkdir -p "$UPLOADS_DIR"
    fi
    
    log "Backup completed successfully"
    return 0
}

# Функция для инициализации базы данных
init_database() {
    log "Initializing database..."
    
    # Создаем базу данных если она не существует
    if ! docker-compose exec -T db psql -U postgres -lqt | cut -d \| -f 1 | grep -qw app_db; then
        log "Creating database 'app_db'..."
        if ! docker-compose exec -T db psql -U postgres -c "CREATE DATABASE app_db;"; then
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
    
    # Проверяем наличие файлов бэкапа
    if [ ! -f "$db_backup" ] && [ ! -f "$files_backup" ]; then
        warning "No backup files found, skipping restore"
        return 0
    fi
    
    log "Restoring from backup..."
    
    # Восстановление базы данных
    if [ -f "$db_backup" ]; then
        log "Restoring database..."
        # Проверяем существование базы данных
        if ! docker-compose exec -T db psql -U postgres -lqt | cut -d \| -f 1 | grep -qw app_db; then
            log "Creating database 'app_db'..."
            if ! docker-compose exec -T db psql -U postgres -c "CREATE DATABASE app_db;"; then
                error "Failed to create database"
                return 1
            fi
        fi
        
        if docker-compose exec -T db psql -U postgres -d app_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
           docker-compose exec -T db psql -U postgres app_db < "$db_backup"; then
            log "Database restored successfully"
        else
            error "Failed to restore database"
            return 1
        fi
    else
        warning "No database backup found, skipping database restore"
    fi
    
    # Восстановление файлов
    if [ -f "$files_backup" ]; then
        log "Restoring uploads..."
        if rm -rf "$UPLOADS_DIR"/* && tar -xzf "$files_backup" -C "$UPLOADS_DIR"; then
            log "Files restored successfully"
        else
            error "Failed to restore files"
            return 1
        fi
    else
        warning "No files backup found, skipping files restore"
    fi
    
    log "Restore completed successfully"
    return 0
}

# Функция для инициализации Flask-Migrate
init_flask_migrate() {
    log "Initializing Flask-Migrate..."
    
    # Проверяем наличие директории migrations
    if [ ! -d "migrations" ]; then
        log "Creating migrations directory..."
        mkdir -p migrations
    fi
    
    # Инициализируем миграции внутри контейнера
    docker-compose exec -T web bash -c '
        export FLASK_APP=migrations.py
        if [ ! -f "migrations/alembic.ini" ]; then
            flask db init
        fi
        flask db migrate -m "Initial migration"
        flask db upgrade
    '
    
    return $?
}

# Функция для применения миграций
apply_migrations() {
    log "Applying database migrations..."
    
    # Проверяем существование директории migrations
    if [ ! -d "migrations" ]; then
        log "Migrations directory not found, initializing Flask-Migrate..."
        if ! init_flask_migrate; then
            return 1
        fi
        return 0
    fi
    
    # Применяем существующие миграции внутри контейнера
    docker-compose exec -T web bash -c '
        export FLASK_APP=migrations.py
        flask db upgrade
    '
    
    return $?
}

# Основной процесс обновления
main() {
    log "Starting update process..."
    
    # Очистка старых логов
    cleanup_logs
    
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
    
    # Всегда восстанавливаем данные из резервной копии
    log "Restoring data from backup..."
    if ! restore_backup "$BACKUP_DB" "$BACKUP_FILES"; then
        error "Failed to restore data from backup"
        exit 1
    fi
    
    # Применяем миграции
    if ! apply_migrations; then
        error "Failed to apply migrations"
        exit 1
    fi
    
    log "Update completed successfully!"
    
    # Очистка старых бэкапов (оставляем последние 5)
    log "Cleaning up old backups..."
    ls -t "$BACKUPS_DIR/db_backup_*" 2>/dev/null | tail -n +6 | xargs -r rm
    ls -t "$BACKUPS_DIR/uploads_backup_*" 2>/dev/null | tail -n +6 | xargs -r rm
}

# Запускаем основной процесс
main
