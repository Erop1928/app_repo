#!/bin/bash

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 не найден. Пожалуйста, установите Python 3.11 или выше"
    exit 1
fi

# Создание виртуального окружения
echo "Создание виртуального окружения..."
python3 -m venv venv

# Активация виртуального окружения
echo "Активация виртуального окружения..."
source venv/bin/activate

# Установка зависимостей
echo "Установка зависимостей..."
pip install -r requirements.txt

# Создание .env файла если его нет
if [ ! -f ".env" ]; then
    echo "Создание .env файла..."
    cp .env.example .env
fi

# Создание необходимых директорий
echo "Создание директорий..."
mkdir -p uploads instance

# Инициализация базы данных
echo "Инициализация базы данных..."
python init_db.py

echo "Установка завершена!"
echo "Для запуска приложения выполните:"
echo "source venv/bin/activate"
echo "python main.py" 