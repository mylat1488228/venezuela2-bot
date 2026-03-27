import nextcord
from nextcord.ext import commands
import yt_dlp
import asyncio

# Настройки для скачивания музыки
ytdl_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

ytdl = yt_dlp.YoutubeDL(ytdl_options)

class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(nextcord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # Очереди для каждого сервера
    
    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]
    
    @nextcord.slash_command(name="play", description="Включить музыку")
    async def play(self, interaction: nextcord.Interaction, query: str):
        """Включает музыку с YouTube"""
        if not interaction.user.voice:
            return await interaction.response.send_message(
                "❌ Вы должны быть в голосовом канале!", 
                ephemeral=True
            )
        
        channel = interaction.user.voice.channel
        
        # Подключаемся к каналу
        if not interaction.guild.voice_client:
            await channel.connect()
        else:
            await interaction.guild.voice_client.move_to(channel)
        
        await interaction.response.defer()  # Даем время на обработку
        
        try:
            # Ищем по ссылке или по названию
            if not query.startswith('http'):
                query = f"ytsearch:{query}"
            
            player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            queue = self.get_queue(interaction.guild.id)
            
            if interaction.guild.voice_client.is_playing():
                queue.append(player)
                await interaction.followup.send(f"🎵 Добавлено в очередь: **{player.title}**")
            else:
                self.play_next(interaction, player)
                await interaction.followup.send(f"🎵 Сейчас играет: **{player.title}**")
                
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка: {str(e)}")
    
    def play_next(self, interaction, player=None):
        """Воспроизводит следующий трек"""
        if player:
            interaction.guild.voice_client.play(
                player, 
                after=lambda e: self.play_next(interaction) if not e else print(f"Ошибка: {e}")
            )
        else:
            queue = self.get_queue(interaction.guild.id)
            if queue:
                next_player = queue.pop(0)
                interaction.guild.voice_client.play(
                    next_player,
                    after=lambda e: self.play_next(interaction) if not e else print(f"Ошибка: {e}")
                )
    
    @nextcord.slash_command(name="skip", description="Пропустить трек")
    async def skip(self, interaction: nextcord.Interaction):
        """Пропускает текущий трек"""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Трек пропущен!")
        else:
            await interaction.response.send_message("❌ Ничего не играет!", ephemeral=True)
    
    @nextcord.slash_command(name="stop", description="Остановить музыку")
    async def stop(self, interaction: nextcord.Interaction):
        """Останавливает воспроизведение"""
        if interaction.guild.voice_client:
            self.queues[interaction.guild.id] = []
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("⏹️ Воспроизведение остановлено!")
        else:
            await interaction.response.send_message("❌ Бот не в голосовом канале!", ephemeral=True)
    
    @nextcord.slash_command(name="queue", description="Показать очередь")
    async def queue(self, interaction: nextcord.Interaction):
        """Показывает очередь треков"""
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            return await interaction.response.send_message("📭 Очередь пуста!", ephemeral=True)
        
        embed = nextcord.Embed(title="📋 Очередь", color=0x3498db)
        for i, track in enumerate(queue[:10], 1):  # Показываем первые 10
            embed.add_field(name=f"{i}.", value=track.title, inline=False)
        
        if len(queue) > 10:
            embed.set_footer(text=f"И еще {len(queue) - 10} треков...")
        
        await interaction.response.send_message(embed=embed)

def setup(bot):
    bot.add_cog(Music(bot))