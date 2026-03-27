import nextcord
from nextcord.ext import commands
import io

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @nextcord.slash_command(name="report", description="Пожаловаться на игрока")
    async def report(self, interaction: nextcord.Interaction, 
                    player: str, 
                    reason: str, 
                    server: str = SlashOption(choices=["FT", "HV"]),
                    description: str = None):
        """Отправляет репорт на игрока"""
        
        # Ищем или создаем канал репортов
        report_channel = nextcord.utils.get(interaction.guild.text_channels, name="репорты")
        if not report_channel:
            report_channel = await interaction.guild.create_text_channel(
                "репорты",
                overwrites={
                    interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
                    interaction.guild.me: nextcord.PermissionOverwrite(read_messages=True)
                }
            )
        
        embed = nextcord.Embed(
            title="🚨 Новый репорт",
            color=0xe74c3c,
            timestamp=nextcord.utils.utcnow()
        )
        embed.add_field(name="👤 Нарушитель", value=player, inline=True)
        embed.add_field(name="🎮 Сервер", value=server, inline=True)
        embed.add_field(name="📌 Причина", value=reason, inline=False)
        if description:
            embed.add_field(name="📝 Описание", value=description, inline=False)
        embed.add_field(name="📢 Отправитель", value=interaction.user.mention, inline=False)
        
        msg = await report_channel.send(embed=embed)
        
        # Сохраняем в БД
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO reports (reporter_id, target_name, reason, server_type)
                VALUES ($1, $2, $3, $4)
            ''', interaction.user.id, player, f"{reason}\n{description or ''}", server)
        
        await interaction.response.send_message(
            "✅ Репорт отправлен! Администраторы рассмотрят его в ближайшее время.",
            ephemeral=True
        )
    
    @nextcord.slash_command(name="ticket", description="Создать тикет")
    async def ticket(self, interaction: nextcord.Interaction, 
                    topic: str = SlashOption(choices=["Помощь", "Жалоба", "Покупка", "Другое"])):
        """Создает приватный тикет-канал"""
        
        # Проверяем, нет ли уже открытого тикета
        async with self.bot.db_pool.acquire() as conn:
            existing = await conn.fetchrow('''
                SELECT channel_id FROM tickets 
                WHERE user_id = $1 AND status = 'open'
            ''', interaction.user.id)
            
            if existing:
                return await interaction.response.send_message(
                    f"❌ У вас уже есть открытый тикет! <#{existing['channel_id']}>",
                    ephemeral=True
                )
        
        # Создаем канал
        overwrites = {
            interaction.guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
            interaction.user: nextcord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: nextcord.PermissionOverwrite(read_messages=True, manage_channels=True)
        }
        
        # Добавляем админов
        for admin_id in self.bot.owner_ids:
            admin = interaction.guild.get_member(admin_id)
            if admin:
                overwrites[admin] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        category = nextcord.utils.get(interaction.guild.categories, name="Тикеты")
        if not category:
            category = await interaction.guild.create_category("Тикеты")
        
        channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        # Сохраняем в БД
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO tickets (user_id, channel_id, category)
                VALUES ($1, $2, $3)
            ''', interaction.user.id, channel.id, topic)
        
        # Отправляем сообщение в канал тикета
        embed = nextcord.Embed(
            title=f"🎫 Тикет #{channel.name}",
            description=f"Тема: **{topic}**\nОжидайте ответа администратора...",
            color=0x3498db
        )
        
        view = TicketView(self.bot)
        await channel.send(f"{interaction.user.mention}", embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Тикет создан: {channel.mention}",
            ephemeral=True
        )

class TicketView(nextcord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @nextcord.ui.button(label="Закрыть тикет", style=nextcord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, button, interaction):
        """Закрывает тикет и сохраняет лог"""
        channel = interaction.channel
        
        # Собираем историю сообщений
        messages = []
        async for msg in channel.history(limit=None, oldest_first=True):
            time = msg.created_at.strftime("%Y-%m-%d %H:%M")
            messages.append(f"[{time}] {msg.author.name}: {msg.content}")
        
        transcript = "\n".join(messages)
        
        # Обновляем БД
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE tickets 
                SET status = 'closed', closed_at = NOW(), transcript = $1
                WHERE channel_id = $2
            ''', transcript, channel.id)
        
        # Отправляем лог в архив
        archive = nextcord.utils.get(interaction.guild.text_channels, name="архив-тикетов")
        if not archive:
            archive = await interaction.guild.create_text_channel("архив-тикетов")
        
        file = io.BytesIO(transcript.encode())
        await archive.send(
            f"📁 Тикет {channel.name} закрыт {interaction.user.mention}",
            file=nextcord.File(file, f"{channel.name}.txt")
        )
        
        await channel.delete()

def setup(bot):
    bot.add_cog(Tickets(bot))