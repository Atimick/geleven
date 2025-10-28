import discord
from discord import app_commands
from discord.ext import commands
from commands.id_check import is_allowed # <--- ĐÃ THAY ĐỔI TỪ is_admin SANG is_allowed

voice_clients = {}

class VoiceMasterCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Lệnh Slash /fake_join ---
    
    @app_commands.command(name="fake_join", description="Khiến bot tham gia kênh thoại và giữ kênh không bị xóa (Chỉ người có quyền Quản lý Server).")
    # Lệnh chỉ hiển thị cho người có quyền Administrator hoặc người dùng cụ thể (Admin cứng)
    @app_commands.default_permissions(administrator=True) 
    @app_commands.check(is_allowed) # <--- ĐÃ THAY ĐỔI: Sử dụng is_allowed để cho phép Admin cứng HOẶC người có quyền Manage Server
    async def fake_join_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Defer để xử lý

        # 1. Kiểm tra Guild
        if interaction.guild is None:
            await interaction.followup.send("Lệnh này chỉ có thể được sử dụng trong Server.", ephemeral=True)
            return
        
        # 2. Kiểm tra người dùng có đang ở kênh thoại nào không
        if interaction.user.voice is None or interaction.user.voice.channel is None:
            await interaction.followup.send(
                "Bạn phải tham gia **một kênh thoại** trước để sử dụng lệnh này. ❌",
                ephemeral=True
            )
            return

        target_channel = interaction.user.voice.channel
        guild_id = interaction.guild.id

        # 3. Kiểm tra và ngắt kết nối khỏi kênh thoại cũ (nếu có)
        current_voice_client = voice_clients.get(guild_id)
        
        if current_voice_client and current_voice_client.is_connected():
            # Bot đã ở kênh hiện tại
            if current_voice_client.channel.id == target_channel.id:
                await interaction.followup.send(
                    f"Bot đã ở trong kênh **{target_channel.name}** rồi. 🤖",
                    ephemeral=True
                )
                return
            
            # Ngắt kết nối khỏi kênh cũ
            await current_voice_client.disconnect()
            del voice_clients[guild_id] 


        # 4. Kết nối vào kênh thoại mới
        try:
            # Tham gia kênh thoại. self_deaf=True để bot không cần nghe/phát, chỉ "treo"
            new_voice_client = await target_channel.connect(self_deaf=True) 
            voice_clients[guild_id] = new_voice_client

            # Trả lời tương tác ban đầu
            await interaction.followup.send(
                f"Bot đã tham gia kênh thoại **{target_channel.name}** và đang 'treo' ở đó. Kênh sẽ được giữ lại. ✅",
                ephemeral=False 
            )
        except discord.errors.ClientException as e:
            await interaction.followup.send(
                f"Bot đang bận hoặc đã kết nối ở đâu đó. Lỗi: `{e}`",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Đã xảy ra lỗi khi cố gắng tham gia kênh thoại: `{e}`",
                ephemeral=True
            )

    # --- Lệnh Slash /fake_leave ---

    @app_commands.command(name="fake_leave", description="Rút bot ra khỏi kênh thoại đang treo.")
    @app_commands.default_permissions(administrator=True) 
    @app_commands.check(is_allowed) # <--- ĐÃ THAY ĐỔI: Sử dụng is_allowed
    async def fake_leave_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            await interaction.followup.send("Lệnh này chỉ có thể được sử dụng trong Server.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        current_voice_client = voice_clients.get(guild_id)

        if current_voice_client and current_voice_client.is_connected():
            channel_name = current_voice_client.channel.name
            await current_voice_client.disconnect()
            del voice_clients[guild_id]
            
            await interaction.followup.send(
                f"Bot đã ngắt kết nối khỏi kênh **{channel_name}**. Kênh đó hiện có thể bị Voice Master xóa đi. 👋",
                ephemeral=False
            )
        else:
            await interaction.followup.send(
                "Bot hiện không ở trong bất kỳ kênh thoại nào trong Server này.",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceMasterCommands(bot))