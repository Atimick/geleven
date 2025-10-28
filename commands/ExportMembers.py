import discord
from discord.ext import commands
from discord import app_commands, Interaction, File, Embed
import openpyxl
import os

# Import is_allowed để kiểm tra quyền Manage Server
from .id_check import is_allowed

class ExportMembers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def log_command_usage(self, user, command_name, channel_id):
        # LƯU Ý: Đây là hàm log cơ bản, bạn có thể thay bằng hàm log vào Excel nếu cần
        print(f"[LOG] {user} ({user.id}) dùng lệnh {command_name} ở kênh {channel_id}")

    @app_commands.command(name="exportmembers", description="Xuất danh sách thành viên thành file Excel (Manage Server Only)")
    @app_commands.check(is_allowed) # CHỈ CẦN MANAGE SERVER
    async def export_members(self, interaction: Interaction):
        if not is_allowed(interaction):
            return await interaction.response.send_message("❌ Bạn không có quyền **Manage Server/Admin** để dùng lệnh này.", ephemeral=True)

        self.log_command_usage(interaction.user, "exportmembers", interaction.channel_id)
        
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            # Lấy danh sách thành viên
            members = interaction.guild.members
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Members"
            ws.append(["Display Name", "Username", "User ID", "Created Date", "Joined Date"])

            for member in members:
                if not member.bot: # Bỏ qua bot
                    ws.append([
                        member.display_name,
                        member.name,
                        str(member.id),
                        member.created_at.strftime("%Y-%m-%d"),
                        member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "N/A"
                    ])

            # LƯU Ý: File này dùng thư mục 'exports' tương đối, không dùng LOG_FOLDER hardcode
            os.makedirs("exports", exist_ok=True)
            file_path = os.path.join("exports", f"members_{interaction.guild.id}.xlsx")
            wb.save(file_path)

            embed = Embed(
                title="📦 Danh sách thành viên đã xuất",
                description=f"Máy chủ: **{interaction.guild.name}**\\n"
                            f"Tổng thành viên (không tính bot): **{len([m for m in members if not m.bot])}**",
                color=discord.Color.green()
            )
            embed.set_footer(text="Dữ liệu được tạo tự động bởi Geleven Bot")
            embed.timestamp = interaction.created_at

            await interaction.followup.send(embed=embed, file=File(file_path), ephemeral=True)
            os.remove(file_path)

        except discord.Forbidden:
            await interaction.followup.send("❌ Bot không có đủ quyền để xem danh sách thành viên.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Xuất thất bại: `{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ExportMembers(bot))