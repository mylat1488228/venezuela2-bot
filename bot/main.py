import os
import asyncio
import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction
import asyncpg
import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))
ADMIN_USERS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
DATABASE_URL = os.getenv("DATABASE_URL")

intents = nextcord.Intents.all()
intents.members = True
intents.presences = True
intents.message_content = True

class VenezuelaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            owner_ids=set(ADMIN_USERS)
        )
        self.guild_id = GUILD_ID
        self.db_pool = None
        
    async def setup_hook(self):
        print("🔄 Подключение к базе данных...")
        print(f"DATABASE_URL: {DATABASE_URL[:20]}... (проверка)")
        
        if not DATABASE_URL:
            print("❌ ОШИБКА: DATABASE_URL не найден! Добавьте переменную в Railway.")
            return
            
        try:
            self.db_pool = await asyncpg.create_pool(DATABASE_URL)
            await self.init_database()
            print("✅ База данных подключена")
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            print("⚠️ Бот работает БЕЗ базы данных (ограниченный функционал)")
        
        # Загружаем модули
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
                print(f"✅ {cog} загружен")
            except Exception as e:
                print(f"❌ Ошибка {cog}: {e}")
        
        # Синхронизация команд
        if GUILD_ID:
            guild = nextcord.Object(id=GUILD_ID)
            await self.tree.sync(guild=guild)
            print(f"🔄 Команды синхронизированы для {GUILD_ID}")
        
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
            print("✅ Таблицы созданы")
    
    async def on_ready(self):
        print(f"🚀 Бот {self.user} запущен!")
        await self.change_presence(
            activity=nextcord.Activity(
                type=nextcord.ActivityType.watching,
                name="за сервером ʙᴇɴᴇᴢᴜᴇʟᴀ 2"
            )
        )
    
    async def on_message(self, message):
        """Обработка сообщений с проверкой БД"""
        if message.author.bot or not message.guild:
            return
            
        if message.guild.id == self.guild_id:
            # Если БД не подключена - пропускаем XP начисление
            if not self.db_pool:
                return
                
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
                        return
                    
                    current_xp = result['xp']
                    current_level = result['level']
                    new_level = int((current_xp / 100) ** 0.5) + 1
                    
                    if new_level > current_level:
                        await conn.execute('''
                            UPDATE users SET level = $1 WHERE user_id = $2
                        ''', new_level, message.author.id)
                        
                        role_name = f"Уровень {new_level}"
                        role = nextcord.utils.get(message.guild.roles, name=role_name)
                        if not role:
                            try:
                                role = await message.guild.create_role(name=role_name, color=0x3498db)
                            except:
                                pass
                        
                        if role:
                            await message.author.add_roles(role)
                            await message.channel.send(
                                f"🎊 {message.author.mention} достиг уровня **{new_level}**!"
                            )
            except Exception as e:
                print(f"Ошибка в on_message: {e}")
        
        await self.process_commands(message)
    
    async def log_event(self, event_type, user_id, target_id=None, content=None, channel_id=None):
        """Логирование (если БД доступна)"""
        if not self.db_pool:
            return
            
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO logs (event_type, user_id, target_id, content, channel_id)
                    VALUES ($1, $2, $3, $4, $5)
                ''', event_type, user_id, target_id, content, channel_id)
        except:
            pass

bot = VenezuelaBot()

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
