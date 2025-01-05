@echo off

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python не найден. Пожалуйста, установите Python 3.11 или выше
    exit /b 1
)

REM Создание виртуального окружения
echo Создание виртуального окружения...
python -m venv venv

REM Активация виртуального окружения
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo Установка зависимостей...
pip install -r requirements.txt

REM Создание .env файла если его нет
if not exist .env (
    echo Создание .env файла...
    copy .env.example .env
)

REM Создание необходимых директорий
echo Создание директорий...
if not exist uploads mkdir uploads
if not exist instance mkdir instance

REM Инициализация базы данных
echo Инициализация базы данных...
python init_db.py

echo Установка завершена!
echo Для запуска приложения выполните:
echo venv\Scripts\activate
echo python main.py

pause 