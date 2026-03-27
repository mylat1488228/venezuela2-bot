import nextcord
from nextcord.ext import commands
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.anti_raid = {}  # Отслеживание подозрительной активности
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Anti-raid защита"""
        if member.guild.id != self.bot.guild_id:
            return
        
        # Проверяем на массовый вход
        guild = member.guild
        recent_joins = sum(1 for m in guild.members 
                          if (nextcord.utils.utcnow() - m.joined_at).seconds < 60)
        
        if recent_joins > 10:  # Если больше 10 человек за минуту
            # Включаем режим карантина
            await self.enable_lockdown(guild)
    
    async def enable_lockdown(self, guild):
        """Включает защиту от рейда"""
        # Отключаем возможность писать для @everyone
        for channel in guild.text_channels:
            await channel.set_permissions(
                guild.default_role,
                send_messages=False,
                reason="Anti-raid protection"
            )
        
        # Отправляем предупреждение админам
        admin_channel = nextcord.utils.get(guild.text_channels, name="mod-logs")
        if admin_channel:
            await admin_channel.send("🚨 **ВНИМАНИЕ!** Обнаружен массовый вход пользователей! Включен режим защиты.")
    
    @nextcord.slash_command(name="lockdown", description="Заблокировать чат (только админы)")
    @commands.has_permissions(administrator=True)
    async def lockdown(self, interaction: nextcord.Interaction, 
                      channel: nextcord.TextChannel = None,
                      reason: str = "Технические работы"):
        """Блокирует канал"""
        target = channel or interaction.channel
        
        await target.set_permissions(
            interaction.guild.default_role,
            send_messages=False,
            reason=reason
        )
        
        await interaction.response.send_message(f"🔒 Канал {target.mention} заблокирован!")
    
    @nextcord.slash_command(name="unlock", description="Разблокировать чат")
    @commands.has_permissions(administrator=True)
    async def unlock(self, interaction: nextcord.Interaction, 
                    channel: nextcord.TextChannel = None):
        """Разблокирует канал"""
        target = channel or interaction.channel
        
        await target.set_permissions(
            interaction.guild.default_role,
            send_messages=None,  # Сброс к дефолту
        )
        
        await interaction.response.send_message(f"🔓 Канал {target.mention} разблокирован!")

def setup(bot):
    bot.add_cog(Moderation(bot))