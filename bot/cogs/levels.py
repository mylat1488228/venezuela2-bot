import nextcord
from nextcord.ext import commands

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @nextcord.slash_command(name="profile", description="Показать профиль")
    async def profile(self, interaction: nextcord.Interaction, user: nextcord.Member = None):
        """Показывает красивый профиль пользователя"""
        target = user or interaction.user
        
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT xp, level, money, messages, voice_time, verified, created_at
                FROM users WHERE user_id = $1
            ''', target.id)
        
        if not row:
            return await interaction.response.send_message("❌ Пользователь не найден в базе!", ephemeral=True)
        
        # Рассчитываем прогресс до следующего уровня
        current_xp = row['xp']
        current_level = row['level']
        xp_needed = (current_level ** 2) * 100
        progress = (current_xp / xp_needed) * 100
        
        embed = nextcord.Embed(
            title=f"👤 Профиль {target.name}",
            color=0x9b59b6,
            timestamp=nextcord.utils.utcnow()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Основная статистика
        embed.add_field(name="📊 Уровень", value=f"**{current_level}**", inline=True)
        embed.add_field(name="⭐ XP", value=f"**{current_xp}** / {xp_needed}", inline=True)
        embed.add_field(name="💰 Баланс", value=f"**{row['money']:,}**", inline=True)
        
        # Дополнительная статистика
        embed.add_field(name="💬 Сообщений", value=f"{row['messages']:,}", inline=True)
        embed.add_field(name="🎙️ В голосовых", value=f"{row['voice_time']} ч.", inline=True)
        embed.add_field(name="✅ Верификация", value="Да" if row['verified'] else "Нет", inline=True)
        
        # Прогресс-бар уровня
        bar_length = 20
        filled = int((progress / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        embed.add_field(
            name="Прогресс",
            value=f"`{bar}` {progress:.1f}%",
            inline=False
        )
        
        embed.set_footer(text=f"ID: {target.id}")
        
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(name="top", description="Топ пользователей по уровню")
    async def top(self, interaction: nextcord.Interaction):
        """Показывает топ 10 по XP"""
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, level, xp FROM users ORDER BY xp DESC LIMIT 10
            ''')
        
        embed = nextcord.Embed(title="🏆 Топ пользователей", color=0xf1c40f)
        
        for i, row in enumerate(rows, 1):
            user = self.bot.get_user(row['user_id'])
            name = user.name if user else "Неизвестно"
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "▫️")
            
            embed.add_field(
                name=f"{medal} #{i} {name}",
                value=f"Уровень {row['level']} | {row['xp']} XP",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

def setup(bot):
    bot.add_cog(Levels(bot))