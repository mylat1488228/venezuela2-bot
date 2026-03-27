import nextcord
from nextcord.ext import commands
import random
import asyncio

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # Анти-спам
    
    async def get_balance(self, user_id):
        """Получает баланс пользователя"""
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow('SELECT money FROM users WHERE user_id = $1', user_id)
            return row['money'] if row else 1000
    
    async def update_balance(self, user_id, amount):
        """Обновляет баланс (+ или -)"""
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute('''
                UPDATE users SET money = money + $1 WHERE user_id = $2
            ''', amount, user_id)
    
    @nextcord.slash_command(name="balance", description="Проверить баланс")
    async def balance(self, interaction: nextcord.Interaction, user: nextcord.Member = None):
        """Показывает баланс"""
        target = user or interaction.user
        
        balance = await self.get_balance(target.id)
        
        embed = nextcord.Embed(
            title="💰 Баланс",
            description=f"{target.mention}: **{balance:,}** монет",
            color=0xf1c40f
        )
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(name="daily", description="Ежедневная награда")
    async def daily(self, interaction: nextcord.Interaction):
        """Выдает ежедневную награду (раз в 24 часа)"""
        # Здесь можно добавить проверку cooldown через Redis или БД
        reward = random.randint(100, 500)
        await self.update_balance(interaction.user.id, reward)
        
        embed = nextcord.Embed(
            title="🎁 Ежедневная награда",
            description=f"Вы получили **{reward}** монет!",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(name="duel", description="Вызвать на дуэль")
    async def duel(self, interaction: nextcord.Interaction, opponent: nextcord.Member, amount: int):
        """Дуэль на деньги"""
        if opponent.id == interaction.user.id:
            return await interaction.response.send_message("❌ Нельзя дуэль с собой!", ephemeral=True)
        
        if amount <= 0:
            return await interaction.response.send_message("❌ Сумма должна быть > 0!", ephemeral=True)
        
        # Проверяем баланс
        user_balance = await self.get_balance(interaction.user.id)
        if user_balance < amount:
            return await interaction.response.send_message("❌ У вас недостаточно средств!", ephemeral=True)
        
        opp_balance = await self.get_balance(opponent.id)
        if opp_balance < amount:
            return await interaction.response.send_message("❌ У противника недостаточно средств!", ephemeral=True)
        
        embed = nextcord.Embed(
            title="⚔️ Дуэль!",
            description=f"{opponent.mention}, вас вызывает {interaction.user.mention} на **{amount}** монет!",
            color=0xe74c3c
        )
        embed.add_field(name="Статус", value="⏳ Ожидание ответа...", inline=False)
        
        view = DuelView(self.bot, interaction.user, opponent, amount)
        await interaction.response.send_message(embed=embed, view=view)
    
    @nextcord.slash_command(name="roulette", description="Рулетка")
    async def roulette(self, interaction: nextcord.Interaction, amount: int, 
                      color: str = SlashOption(choices=["red", "black", "green"])):
        """Казино-рулетка"""
        if amount <= 0:
            return await interaction.response.send_message("❌ Ставка > 0!", ephemeral=True)
        
        balance = await self.get_balance(interaction.user.id)
        if balance < amount:
            return await interaction.response.send_message("❌ Недостаточно монет!", ephemeral=True)
        
        # Вращаем рулетку: 0-36
        result = random.randint(0, 36)
        
        if result == 0:
            result_color = "green"
            multiplier = 14
        elif result <= 18:
            result_color = "red"
            multiplier = 2
        else:
            result_color = "black"
            multiplier = 2
        
        if color == result_color:
            winnings = amount * multiplier
            await self.update_balance(interaction.user.id, winnings - amount)  # -ставка +выигрыш
            embed = nextcord.Embed(
                title="🎰 Выигрыш!",
                description=f"Выпало **{result} {result_color}**!\nВы выиграли **{winnings}** монет!",
                color=0x00ff00
            )
        else:
            await self.update_balance(interaction.user.id, -amount)
            embed = nextcord.Embed(
                title="🎰 Проигрыш",
                description=f"Выпало **{result} {result_color}**!\nВы проиграли **{amount}** монет!",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed)
    
    @nextcord.slash_command(name="leaderboard", description="Топ богачей")
    async def leaderboard(self, interaction: nextcord.Interaction):
        """Показывает топ 10 по балансу"""
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, money FROM users ORDER BY money DESC LIMIT 10
            ''')
        
        embed = nextcord.Embed(title="🏆 Топ богачей", color=0xf1c40f)
        
        for i, row in enumerate(rows, 1):
            user = self.bot.get_user(row['user_id'])
            name = user.name if user else "Неизвестно"
            embed.add_field(
                name=f"{i}. {name}",
                value=f"{row['money']:,} монет",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

class DuelView(nextcord.ui.View):
    def __init__(self, bot, challenger, opponent, amount):
        super().__init__(timeout=60)  # 60 секунд на ответ
        self.bot = bot
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
    
    @nextcord.ui.button(label="Принять", style=nextcord.ButtonStyle.green, emoji="✅")
    async def accept(self, button, interaction):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("❌ Это не для вас!", ephemeral=True)
        
        # Проверяем баланс еще раз
        cog = self.bot.get_cog('Economy')
        
        # Выбираем победителя
        winner = random.choice([self.challenger, self.opponent])
        loser = self.opponent if winner == self.challenger else self.challenger
        
        # Переводим деньги
        await cog.update_balance(winner.id, self.amount)
        await cog.update_balance(loser.id, -self.amount)
        
        embed = nextcord.Embed(
            title="⚔️ Дуэль завершена!",
            description=f"🏆 {winner.mention} победил!\n💰 Забрал **{self.amount * 2}** монет!",
            color=0x00ff00
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    @nextcord.ui.button(label="Отказаться", style=nextcord.ButtonStyle.red, emoji="❌")
    async def decline(self, button, interaction):
        if interaction.user.id != self.opponent.id:
            return await interaction.response.send_message("❌ Это не для вас!", ephemeral=True)
        
        await interaction.response.edit_message(
            content="❌ Дуэль отклонена!", 
            embed=None, 
            view=None
        )
        self.stop()

def setup(bot):
    bot.add_cog(Economy(bot))