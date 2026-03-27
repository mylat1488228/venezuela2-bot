FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
RUN apt-get update && apt-get install -y gcc postgresql-client && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY bot/requirements.txt .
RUN pip install fastapi uvicorn nextcord asyncpg python-dotenv

# Копируем весь код
COPY . .

# Создаем папки
RUN mkdir -p web/templates

# КОМАНДА ЗАПУСКА: сначала бот в фоне, потом сайт на переднем плане
CMD python bot/main.py & python -m uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000}
