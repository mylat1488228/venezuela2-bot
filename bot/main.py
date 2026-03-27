import os
import asyncio
import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction
import asyncpg
import datetime
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Получаем настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ADMIN_USERS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
DATABASE_URL = os.getenv("DATABASE_URL")

# Настраиваем интенты (разрешения бота)
intents = nextcord.Intents.all()
intents.members = True  # Важно для отслеживания входа/выхода
intents.presences = True  # Статусы пользователей
intents.message_content = True  # Чтение сообщений

class VenezuelaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,  # Отключаем стандартную помощь
            owner_ids=set(ADMIN_USERS)
        )
        self.guild_id = GUILD_ID
        self.db_pool = None  # Здесь будет пул соединений с БД
        
    async def setup_hook(self):
        """Вызывается при запуске бота"""
        print("🔄 Подключение к базе данных...")
        
        # Подключаемся к PostgreSQL
        self.db_pool = await asyncpg.create_pool(DATABASE_URL)
        
        # Создаем таблицы если их нет
        await self.init_database()
        
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
                print(f"❌ Ошибка загрузки {cog}: {e}")
        
        # Синхронизируем slash-команды с Discord
        guild = nextcord.Object(id=self.guild_id)
        await self.tree.sync(guild=guild)
        print("🔄 Команды синхронизированы")
        
    async def init_database(self):
        """Создание таблиц в БД"""
        async with self.db_pool.acquire() as conn:
            # Таблица пользователей (XP, уровни, баланс)
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
            
            # Таблица тикетов
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
            
            # Таблица объявлений рынка
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS market_ads (
                    ad_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    server_type VARCHAR(10),  -- FT или HV
                    title TEXT,
                    description TEXT,
                    price TEXT,
                    image_url TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица приватных каналов
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
            
            # Таблица репортов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    report_id SERIAL PRIMARY KEY,
                    reporter_id BIGINT,
                    target_name VARCHAR(100),
                    reason TEXT,
                    server_type VARCHAR(10),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_by BIGINT,
                    resolution TEXT
                )
            ''')
            
            # Таблица заказов дефа
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS def_orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    nickname VARCHAR(100),
                    coords VARCHAR(50),
                    server_type VARCHAR(10),
                    payment TEXT,
                    details TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    executor_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица логов
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
            
            print("✅ База данных инициализирована")
    
    async def on_ready(self):
        """Вызывается когда бот полностью готов"""
        print(f"🚀 Бот {self.user} успешно запущен!")
        print(f"📝 Обслуживается сервер: {self.guild_id}")
        
        # Устанавливаем статус
        await self.change_presence(
            activity=nextcord.Activity(
                type=nextcord.ActivityType.watching,
                name="за сервером ʙᴇɴᴇᴢᴜᴇʟᴀ 2"
            )
        )
        
        # Запускаем фоновые задачи
        self.update_stats.start()
    
    @tasks.loop(minutes=5)
    async def update_stats(self):
        """Обновление статистики каждые 5 минут"""
        guild = self.get_guild(self.guild_id)
        if guild:
            online = sum(1 for m in guild.members if m.status != nextcord.Status.offline)
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO server_stats (timestamp, online_count, total_members)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (timestamp) DO NOTHING
                ''', datetime.datetime.now(), online, guild.member_count)
    
    async def on_member_join(self, member):
        """Приветствие новых участников"""
        if member.guild.id != self.guild_id:
            return
            
        # Ищем канал приветствий
        welcome_channel = nextcord.utils.get(member.guild.text_channels, name="приветствия")
        
        if welcome_channel:
            embed = nextcord.Embed(
                title="🎉 Добро пожаловать в ʙᴇɴᴇᴢᴜᴇʟᴀ 2!",
                description=f"{member.mention} присоединился к нам!",
                color=0x00ff00,
                timestamp=datetime.datetime.now()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
            
            await welcome_channel.send(embed=embed)
        
        # Добавляем пользователя в БД
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
            ''', member.id, member.name)
        
        # Логируем
        await self.log_event('member_join', member.id, None, f"Присоединился {member.name}")
    
    async def on_member_remove(self, member):
        """Прощание с участниками"""
        if member.guild.id != self.guild_id:
            return
            
        goodbye_channel = nextcord.utils.get(member.guild.text_channels, name="прощания")
        if goodbye_channel:
            embed = nextcord.Embed(
                title="👋 Пока!",
                description=f"{member.name} покинул сервер",
                color=0xff0000
            )
            await goodbye_channel.send(embed=embed)
        
        await self.log_event('member_leave', member.id, None, f"Покинул {member.name}")
    
    async def on_message(self, message):
        """Обработка сообщений (XP и статистика)"""
        if message.author.bot or not message.guild:
            return
            
        if message.guild.id == self.guild_id:
            # Начисление XP (1 XP за каждые 10 символов, макс 50)
            xp_gain = min(len(message.content) // 10, 50) + 1
            
            async with self.db_pool.acquire() as conn:
                # Обновляем XP и сообщения
                result = await conn.fetchrow('''
                    UPDATE users 
                    SET xp = xp + $1, 
                        messages = messages + 1,
                        last_active = $2
                    WHERE user_id = $3
                    RETURNING xp, level
                ''', xp_gain, datetime.datetime.now(), message.author.id)
                
                # Если пользователя нет в БД, добавляем
                if not result:
                    await conn.execute('''
                        INSERT INTO users (user_id, username, xp, messages)
                        VALUES ($1, $2, $3, 1)
                    ''', message.author.id, message.author.name, xp_gain)
                    return
                
                # Проверка повышения уровня
                current_xp = result['xp']
                current_level = result['level']
                new_level = int((current_xp / 100) ** 0.5) + 1
                
                if new_level > current_level:
                    await conn.execute('''
                        UPDATE users SET level = $1 WHERE user_id = $2
                    ''', new_level, message.author.id)
                    
                    # Выдаем роль за уровень
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
                            f"🎊 {message.author.mention} достиг уровня **{new_level}**! Поздравляем!"
                        )
        
        await self.process_commands(message)
    
    async def log_event(self, event_type, user_id, target_id=None, content=None, channel_id=None):
        """Универсальная функция логирования"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO logs (event_type, user_id, target_id, content, channel_id)
                VALUES ($1, $2, $3, $4, $5)
            ''', event_type, user_id, target_id, content, channel_id)

# Создаем экземпляр бота
bot = VenezuelaBot()

# Запускаем бота
if __name__ == "__main__":
    bot.run(BOT_TOKEN)