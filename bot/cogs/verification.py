import nextcord
from nextcord.ext import commands
import random
import string
import asyncio

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verification_codes = {}  # Временное хранилище кодов
        self.attempts = {}  # Попытки ввода
    
    @nextcord.slash_command(name="setup_verification", description="Создать канал верификации (только для админов)")
    @commands.is_owner()
    async def setup_verification(self, interaction: Interaction):
        """Создает сообщение с кнопкой верификации"""
        embed = nextcord.Embed(
            title="✅ Верификация",
            description="Для доступа к серверу нажмите кнопку ниже и введите код.",
            color=0x3498db
        )
        embed.add_field(
            name="Инструкция",
            value="1. Нажмите кнопку\n2. Запомните код\n3. Введите его в появившемся окне",
            inline=False
        )
        
        view = VerificationView(self.bot)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ Система верификации установлена!", ephemeral=True)

class VerificationView(nextcord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @nextcord.ui.button(
        label="Верифицироваться", 
        style=nextcord.ButtonStyle.green, 
        custom_id="verification_button",
        emoji="✅"
    )
    async def verify_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Генерируем код (6 символов: буквы + цифры)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Сохраняем код для пользователя
        self.bot.cogs['Verification'].verification_codes[interaction.user.id] = code
        self.bot.cogs['Verification'].attempts[interaction.user.id] = 0
        
        # Показываем модальное окно
        modal = VerificationModal(code)
        await interaction.response.send_modal(modal)

class VerificationModal(nextcord.ui.Modal):
    def __init__(self, correct_code):
        super().__init__("Подтверждение")
        self.correct_code = correct_code
        
        self.code_input = nextcord.ui.TextInput(
            label=f"Введите код: {correct_code}",  # Показываем код прямо тут для простоты
            placeholder="XXXXXX",
            min_length=6,
            max_length=6,
            required=True
        )
        self.add_item(self.code_input)
    
    async def callback(self, interaction: nextcord.Interaction):
        cog = interaction.client.cogs['Verification']
        user_id = interaction.user.id
        
        # Проверяем количество попыток
        cog.attempts[user_id] = cog.attempts.get(user_id, 0) + 1
        
        if cog.attempts[user_id] > 3:
            await interaction.response.send_message(
                "❌ Слишком много попыток! Попробуйте через 10 минут.", 
                ephemeral=True
            )
            return
        
        # Проверяем код
        if self.code_input.value.upper() == self.correct_code:
            # Выдаем роль Verified
            role = nextcord.utils.get(interaction.guild.roles, name="Verified")
            
            if not role:
                # Если роли нет, создаем её
                try:
                    role = await interaction.guild.create_role(
                        name="Verified",
                        color=0x00ff00,
                        reason="Автосоздание системой верификации"
                    )
                except Exception as e:
                    await interaction.response.send_message(
                        f"❌ Ошибка создания роли: {e}", 
                        ephemeral=True
                    )
                    return
            
            # Выдаем роль
            await interaction.user.add_roles(role)
            
            # Обновляем БД
            async with interaction.client.db_pool.acquire() as conn:
                await conn.execute('''
                    UPDATE users SET verified = TRUE WHERE user_id = $1
                ''', user_id)
            
            # Удаляем код из памяти
            if user_id in cog.verification_codes:
                del cog.verification_codes[user_id]
            
            await interaction.response.send_message(
                "✅ Вы успешно верифицированы! Добро пожаловать!", 
                ephemeral=True
            )
            
            # Логируем
            await interaction.client.log_event('verification', user_id, content="Успешная верификация")
        else:
            remaining = 3 - cog.attempts[user_id]
            await interaction.response.send_message(
                f"❌ Неверный код! Осталось попыток: {remaining}", 
                ephemeral=True
            )

def setup(bot):
    bot.add_cog(Verification(bot))