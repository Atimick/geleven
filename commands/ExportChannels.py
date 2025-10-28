import discord
from discord.ext import commands
from discord import app_commands, Interaction, File, Embed
import openpyxl
import os
from .id_check import is_allowed

class ExportChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def log_command_usage(self, user, command_name, channel_id):
        print(f"[LOG] {user} ({user.id}) dùng lệnh {command_name} ở kênh {channel_id}")

    @app_commands.command(name="exportchannels", description="Xuất danh sách kênh và category thành file Excel (Manage Server Only)")
    @app_commands.check(is_allowed)
    async def export_channels(self, interaction: Interaction):
        if not is_allowed(interaction):
            return await interaction.response.send_message("❌ Bạn không có quyền **Manage Server/Admin** để dùng lệnh này.", ephemeral=True)
            
        self.log_command_usage(interaction.user, "exportchannels", interaction.channel_id)
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        try:
            guild = interaction.guild
            if not guild:
                return await interaction.followup.send("Lệnh này chỉ có thể dùng trong server.", ephemeral=True)

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Channels"
            ws.append(["Category", "Channel Name", "Channel ID", "Type", "Position"])

            channels = sorted(guild.channels, key=lambda c: (c.position, c.name))
            
            for channel in channels:
                category_name = channel.category.name if channel.category else "Không có Category"
                channel_type = str(channel.type).split('.')[-1].capitalize()
                
                if channel.type == discord.ChannelType.category:
                    continue
                    
                ws.append([
                    category_name,
                    channel.name,
                    str(channel.id),
                    channel_type,
                    channel.position
                ])

            os.makedirs("exports", exist_ok=True)
            file_path = os.path.join("exports", f"channels_{guild.id}.xlsx")
            wb.save(file_path)

            embed = Embed(
                title="📦 Danh sách Kênh đã xuất",
                description=f"Máy chủ: **{guild.name}**\\n"
                            f"Tổng kênh: **{len([c for c in guild.channels if c.type != discord.ChannelType.category])}**",
                color=discord.Color.green()
            )
            embed.set_footer(text="Dữ liệu được tạo tự động bởi Geleven Bot")
            embed.timestamp = interaction.created_at

            await interaction.followup.send(embed=embed, file=File(file_path), ephemeral=True)
            os.remove(file_path)

        except discord.Forbidden:
            await interaction.followup.send("❌ Bot không có đủ quyền để xem danh sách kênh.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Xuất thất bại: `{e}`", ephemeral=True)
            
async def setup(bot):
    await bot.add_cog(ExportChannels(bot))