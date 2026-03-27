import nextcord
from nextcord.ext import commands
from nextcord import SlashOption

class Minecraft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @nextcord.slash_command(name="setup_market", description="Создать систему рынка")
    @commands.has_permissions(administrator=True)
    async def setup_market(self, interaction: nextcord.Interaction):
        """Создает 3 канала: рынок-фт, рынок-хв, создать-рекламу"""
        guild = interaction.guild
        
        # Создаем категорию
        category = await guild.create_category("🏪 РЫНОК")
        
        # Создаем каналы
        ft_channel = await guild.create_text_channel(
            "🏪-рынок-ft", 
            category=category,
            topic="Объявления Funtime"
        )
        hv_channel = await guild.create_text_channel(
            "🏪-рынок-hv", 
            category=category,
            topic="Объявления Holyworld"
        )
        ads_channel = await guild.create_text_channel(
            "📢-создать-рекламу",
            category=category
        )
        
        # Сообщение с кнопками
        embed = nextcord.Embed(
            title="🏪 Создание рекламы",
            description="Выберите сервер для размещения объявления",
            color=0xf1c40f
        )
        embed.add_field(
            name="Funtime",
            value="Обычный сервер с приватами",
            inline=True
        )
        embed.add_field(
            name="Holyworld",
            value="Анархия без приватов",
            inline=True
        )
        
        view = MarketView(self.bot, ft_channel.id, hv_channel.id)
        await ads_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Рынок создан!\n"
            f"FT: {ft_channel.mention}\n"
            f"HV: {hv_channel.mention}\n"
            f"Создание: {ads_channel.mention}",
            ephemeral=True
        )
    
    @nextcord.slash_command(name="setup_def", description="Создать канал заказа дефа")
    @commands.has_permissions(administrator=True)
    async def setup_def(self, interaction: nextcord.Interaction):
        """Создает канал для заказа защиты"""
        channel = await interaction.guild.create_text_channel("🛡️-заказ-дефа")
        
        embed = nextcord.Embed(
            title="🛡️ Заказ защиты (Деф)",
            description="Нажмите кнопку для создания заявки на защиту территории",
            color=0xe74c3c
        )
        embed.add_field(
            name="Что такое деф?",
            value="Защита вашей базы от рейдеров опытными игроками",
            inline=False
        )
        
        view = DefView(self.bot)
        await channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Канал создан: {channel.mention}",
            ephemeral=True
        )
    
    @nextcord.slash_command(name="setup_private", description="Настроить систему приваток")
    @commands.has_permissions(administrator=True)
    async def setup_private(self, interaction: nextcord.Interaction):
        """Создает канал для создания приватных голосовых"""
        # Создаем категорию для приваток
        category = await interaction.guild.create_category("🔒 Приватные каналы")
        
        # Канал для создания
        create_channel = await interaction.guild.create_text_channel(
            "🔒-создать-приватку",
            category=category
        )
        
        embed = nextcord.Embed(
            title="🔒 Приватные голосовые каналы",
            description="Нажмите кнопку для создания своего канала",
            color=0x9b59b6
        )
        
        view = PrivateView(self.bot)
        await create_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Система создана: {create_channel.mention}",
            ephemeral=True
        )

class MarketView(nextcord.ui.View):
    def __init__(self, bot, ft_id, hv_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.ft_id = ft_id
        self.hv_id = hv_id
    
    @nextcord.ui.button(
        label="Funtime", 
        style=nextcord.ButtonStyle.green,
        custom_id="market_ft",
        emoji="🟢"
    )
    async def ft_button(self, button, interaction):
        modal = AdModal("FT", self.ft_id)
        await interaction.response.send_modal(modal)
    
    @nextcord.ui.button(
        label="Holyworld", 
        style=nextcord.ButtonStyle.blurple,
        custom_id="market_hv",
        emoji="🔵"
    )
    async def hv_button(self, button, interaction):
        modal = AdModal("HV", self.hv_id)
        await interaction.response.send_modal(modal)

class AdModal(nextcord.ui.Modal):
    def __init__(self, server_type, channel_id):
        super().__init__(f"Реклама {server_type}")
        self.server_type = server_type
        self.channel_id = channel_id
        
        self.title_input = nextcord.ui.TextInput(
            label="Название",
            placeholder="Например: Продам алмазы",
            max_length=100,
            required=True
        )
        
        self.desc_input = nextcord.ui.TextInput(
            label="Описание",
            placeholder="Опишите товар подробно",
            style=nextcord.TextInputStyle.paragraph,
            required=True
        )
        
        self.price_input = nextcord.ui.TextInput(
            label="Цена",
            placeholder="Например: 1000$ или обмен на золото",
            max_length=50,
            required=True
        )
        
        self.img_input = nextcord.ui.TextInput(
            label="URL изображения (необязательно)",
            placeholder="https://...",
            required=False
        )
        
        for item in [self.title_input, self.desc_input, self.price_input, self.img_input]:
            self.add_item(item)
    
    async def callback(self, interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        
        embed = nextcord.Embed(
            title=f"🏪 {self.title_input.value}",
            description=self.desc_input.value,
            color=0x2ecc71 if self.server_type == "FT" else 0x3498db,
            timestamp=nextcord.utils.utcnow()
        )
        embed.add_field(name="💰 Цена", value=self.price_input.value, inline=True)
        embed.add_field(name="👤 Продавец", value=interaction.user.mention, inline=True)
        embed.add_field(name="🎮 Сервер", value=self.server_type, inline=True)
        embed.set_footer(text=f"ID объявления: {interaction.user.id}")
        
        if self.img_input.value:
            embed.set_image(url=self.img_input.value)
        
        await channel.send(embed=embed)
        
        # Сохраняем в БД
        async with interaction.client.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO market_ads (user_id, server_type, title, description, price, image_url)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', interaction.user.id, self.server_type, self.title_input.value,
                self.desc_input.value, self.price_input.value, self.img_input.value or None)
        
        await interaction.response.send_message(
            "✅ Объявление размещено!", 
            ephemeral=True
        )

class DefView(nextcord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @nextcord.ui.button(
        label="Заказать деф",
        style=nextcord.ButtonStyle.red,
        custom_id="order_def",
        emoji="🛡️"
    )
    async def def_button(self, button, interaction):
        modal = DefModal()
        await interaction.response.send_modal(modal)

class DefModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__("Заказ защиты")
        
        self.nick = nextcord.ui.TextInput(
            label="Ваш никнейм в игре",
            max_length=32,
            required=True
        )
        
        self.coords = nextcord.ui.TextInput(
            label="Координаты базы",
            placeholder="X Y Z",
            required=True
        )
        
        self.server = nextcord.ui.TextInput(
            label="Сервер",
            placeholder="FT или HV",
            max_length=10,
            required=True
        )
        
        self.payment = nextcord.ui.TextInput(
            label="Оплата",
            placeholder="Что готовы заплатить?",
            required=True
        )
        
        self.details = nextcord.ui.TextInput(
            label="Подробности",
            style=nextcord.TextInputStyle.paragraph,
            placeholder="Время, количество защитников и т.д.",
            required=False
        )
        
        for item in [self.nick, self.coords, self.server, self.payment, self.details]:
            self.add_item(item)
    
    async def callback(self, interaction):
        # Создаем канал для заявок если нет
        admin_channel = nextcord.utils.get(interaction.guild.text_channels, name="деф-заявки")
        if not admin_channel:
            admin_channel = await interaction.guild.create_text_channel(
                "деф-заявки",
                topic="Заявки на защиту территории"
            )
        
        embed = nextcord.Embed(
            title="🛡️ Новый заказ дефа",
            color=0xe74c3c,
            timestamp=nextcord.utils.utcnow()
        )
        embed.add_field(name="👤 Ник", value=self.nick.value, inline=True)
        embed.add_field(name="📍 Координаты", value=self.coords.value, inline=True)
        embed.add_field(name="🎮 Сервер", value=self.server.value, inline=True)
        embed.add_field(name="💰 Оплата", value=self.payment.value, inline=False)
        if self.details.value:
            embed.add_field(name="📝 Детали", value=self.details.value, inline=False)
        embed.set_footer(text=f"Заказал: {interaction.user}")
        
        await admin_channel.send(embed=embed)
        
        # Сохраняем в БД
        async with interaction.client.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO def_orders (user_id, nickname, coords, server_type, payment, details)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', interaction.user.id, self.nick.value, self.coords.value,
                self.server.value, self.payment.value, self.details.value or None)
        
        await interaction.response.send_message(
            "✅ Заявка отправлена администраторам!", 
            ephemeral=True
        )

class PrivateView(nextcord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @nextcord.ui.button(
        label="Создать приватку",
        style=nextcord.ButtonStyle.green,
        custom_id="create_private",
        emoji="🔒"
    )
    async def create_button(self, button, interaction):
        # Ищем или создаем категорию
        category = nextcord.utils.get(interaction.guild.categories, name="Приватные каналы")
        if not category:
            category = await interaction.guild.create_category("Приватные каналы")
        
        # Создаем голосовой канал
        channel = await interaction.guild.create_voice_channel(
            name=f"🔒 {interaction.user.name}",
            category=category,
            user_limit=5
        )
        
        # Устанавливаем права
        await channel.set_permissions(interaction.user, manage_channels=True, connect=True, speak=True)
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        
        # Сохраняем в БД
        async with interaction.client.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO private_channels (channel_id, owner_id, channel_name)
                VALUES ($1, $2, $3)
            ''', channel.id, interaction.user.id, channel.name)
        
        await interaction.response.send_message(
            f"✅ Создан канал {channel.mention}!\n"
            f"Управление:\n"
            f"`/private_add @user` - добавить друга\n"
            f"`/private_remove @user` - удалить\n"
            f"`/private_open` - открыть для всех\n"
            f"`/private_close` - закрыть\n"
            f"`/private_limit 10` - лимит слотов",
            ephemeral=True
        )

def setup(bot):
    bot.add_cog(Minecraft(bot))