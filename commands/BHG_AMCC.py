import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
import requests
import openpyxl
import os
from datetime import datetime

from .id_check import is_admin, is_mod, APPS_SCRIPT_URL, SECRET_TOKEN, LOG_FILE_PATH

class MemberManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_bhg", description="Tăng chỉ số cho thành viên")
    @app_commands.describe(
        member="Thành viên cần cập nhật",
        yellow_coin="Số Yellow Coin cần cộng thêm",
        red_coin="Số Red Coin cần cộng thêm",
        hp="Số HP cần cộng thêm"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def add_bhg(self, interaction: Interaction, member: discord.Member, yellow_coin: int = 0, red_coin: int = 0, hp: int = 0):
     
        # Kiểm tra quyền của người dùng ngay tại đây
        if not is_admin(interaction) and not is_mod(interaction):
            await interaction.response.send_message("❌ Ati không cấp quyền cho lệnh này", ephemeral=True)
            return

        # Nếu người dùng có quyền, defer để báo cho Discord rằng bot đang xử lý
        await interaction.response.defer(ephemeral=True)
        
        if member.bot:
            await interaction.followup.send("❌ Không thể cập nhật chỉ số cho bot.")
            return

        # --- Bắt đầu phần code ghi logs vào tệp XLSX ---
        try:
            if not os.path.exists(LOG_FILE_PATH):
                workbook = openpyxl.Workbook()
                sheet = workbook.active
                headers = ['Thời gian', 'Người dùng', 'ID Người dùng', 'Thành viên bị ảnh hưởng', 'ID Thành viên', 'Yellow Coin', 'Red Coin', 'HP']
                sheet.append(headers)
            else:
                workbook = openpyxl.load_workbook(LOG_FILE_PATH)
                sheet = workbook.active

            data_row = [
                datetime.now(),
                str(interaction.user),
                str(interaction.user.id),
                str(member),
                str(member.id),
                yellow_coin,
                red_coin,
                hp
            ]

            sheet.append(data_row)
            workbook.save(LOG_FILE_PATH)

        except Exception as file_error:
            print(f"Lỗi khi ghi logs vào tệp Excel: {file_error}")
        # --- Kết thúc phần code ghi logs ---

        params = {
            'userID': str(member.id),
            'coin': yellow_coin,
            'red': red_coin,
            'hp': hp,
            'token': SECRET_TOKEN
        }

        try:
            response = requests.get(APPS_SCRIPT_URL, params=params)
            response.raise_for_status()
            result_text = response.text

            await interaction.followup.send(
                f"✅ Lệnh đã được thực thi:\n```{result_text}```"
            )
        except requests.exceptions.RequestException as e:
            await interaction.followup.send(
                f"❌ Đã xảy ra lỗi khi kết nối với máy chủ: ```{e}```"
            )

async def setup(bot):
    await bot.add_cog(MemberManagement(bot))