FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc postgresql-client && rm -rf /var/lib/apt/lists/*

COPY bot/requirements.txt .
RUN pip install fastapi uvicorn nextcord asyncpg python-dotenv

COPY . .
RUN mkdir -p web/templates

# ВАЖНО: Сначала сайт (чтобы Railway увидел порт), потом бот
CMD (sleep 5 && python bot/main.py) & python -m uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000}
