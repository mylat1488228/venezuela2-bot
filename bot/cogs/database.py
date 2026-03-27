import asyncpg
import os

async def create_pool():
    """Создает пул соединений с PostgreSQL"""
    return await asyncpg.create_pool(
        os.getenv("DATABASE_URL"),
        min_size=5,
        max_size=20
    )