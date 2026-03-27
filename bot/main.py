import os
import asyncio
import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction
import asyncpg
import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем настройки с проверками
BOT_TOKEN = os.getenv("BOT_TOKEN")
guild_id_str = os.getenv("GUILD_ID", "0")
try:
    GUILD_ID = int(guild_id_str)
except (ValueError, TypeError):
    GUILD_ID = 0
    print(f"⚠️ Предупреждение: GUILD_ID не задан или неверен: {guild_id_str}")

ADMIN_USERS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_USERS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    except ValueError:
        print("⚠️ Предупреждение: ADMIN_IDS имеет неверный формат")

DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан! Добавьте в Railway Variables")

if not DATABASE_URL:
    print("⚠️ DATABASE_URL не задан, база данных не будет работать")

# Определяем intents (ОБЯЗАТЕЛЬНО ДО КЛАССА!)
intents = nextcord.Intents.all()
intents.members = True
intents.presences = True
intents.message_content = True

class VenezuelaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,  # Теперь intents определен выше
            help_command=None,
            owner_ids=set(ADMIN_USERS)
        )
        self.guild_id = GUILD_ID
        self.db_pool = None
        
    async def setup_hook(self):
        """Вызывается при запуске бота"""
        print("🔄 Подключение к базе данных...")
        
        if DATABASE_URL:
            try:
                self.db_pool = await asyncpg.create_pool(DATABASE_URL)
                await self.init_database()
                print("✅ База данных подключена")
            except Exception as e:
                print(f"❌ Ошибка подключения к БД: {e}")
                self.db_pool = None
        else:
            print("⚠️ DATABASE_URL не найден, работаем без БД")
        
        # Загружаем модули (cogs)
        cogs = [
            'cogs.verification',
            'cogs.minecraft', 
            'cogs.music',
            'cogs.economy',
            'cogs.tickets',
            'cogs.levels',
            'cogs.moderation'
        ]
        
        for cog in cogs:
            try:
                self.load_extension(cog)
                print(f"✅ Модуль {cog} загружен")
            except Exception as e:
                print(f"❌ Ошибка {cog}: {e}")
        
        # Синхронизируем slash-команды
        if GUILD_ID:
            guild = nextcord.Object(id=GUILD_ID)
            await self.tree.sync(guild=guild)
            print(f"🔄 Команды синхронизированы для сервера {GUILD_ID}")
        else:
            print("⚠️ GUILD_ID не задан, команды не синхронизированы!")
        
    async def init_database(self):
        """Создание таблиц в БД"""
        if not self.db_pool:
            return
            
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    money INTEGER DEFAULT 1000,
                    voice_time INTEGER DEFAULT 0,
                    messages INTEGER DEFAULT 0,
                    verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    channel_id BIGINT UNIQUE,
                    category VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    transcript TEXT
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS market_ads (
                    ad_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    server_type VARCHAR(10),
                    title TEXT,
                    description TEXT,
                    price TEXT,
                    image_url TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS private_channels (
                    channel_id BIGINT PRIMARY KEY,
                    owner_id BIGINT,
                    channel_name VARCHAR(100),
                    allowed_users BIGINT[],
                    is_open BOOLEAN DEFAULT FALSE,
                    max_users INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    report_id SERIAL PRIMARY KEY,
                    reporter_id BIGINT,
                    target_name VARCHAR(100),
                    reason TEXT,
                    server_type VARCHAR(10),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    log_id SERIAL PRIMARY KEY,
                    event_type VARCHAR(50),
                    user_id BIGINT,
                    target_id BIGINT,
                    content TEXT,
                    channel_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            print("✅ Таблицы БД созданы")
    
    async def on_ready(self):
        """Бот готов"""
        print(f"🚀 Бот {self.user} запущен!")
        print(f"📡 Обслуживается сервер: {self.guild_id}")
        
        await self.change_presence(
            activity=nextcord.Activity(
                type=nextcord.ActivityType.watching,
                name="за сервером ʙᴇɴᴇᴢᴜᴇʟᴀ 2"
            )
        )
    
    async def on_message(self, message):
        """Обработка сообщений"""
        if message.author.bot or not message.guild:
            return
            
        if message.guild.id == self.guild_id and self.db_pool:
            try:
                xp_gain = min(len(message.content) // 10, 50) + 1
                
                async with self.db_pool.acquire() as conn:
                    result = await conn.fetchrow('''
                        UPDATE users 
                        SET xp = xp + $1, 
                            messages = messages + 1,
                            last_active = $2
                        WHERE user_id = $3
                        RETURNING xp, level
                    ''', xp_gain, datetime.datetime.now(), message.author.id)
                    
                    if not result:
                        await conn.execute('''
                            INSERT INTO users (user_id, username, xp, messages)
                            VALUES ($1, $2, $3, 1)
                        ''', message.author.id, message.author.name, xp_gain)
                        
            except Exception as e:
                print(f"Ошибка обработки сообщения: {e}")
        
        await self.process_commands(message)

# Создаем и запускаем бота
bot = VenezuelaBot()

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
