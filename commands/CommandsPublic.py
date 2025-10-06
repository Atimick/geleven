import discord
import os
import yt_dlp
import asyncio
import json
import aiohttp
import json
import textwrap
import secrets
import openpyxl
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta

from .id_check import LOG_FOLDER
    
class PubOne(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def log_command_usage(self, user, command_name, channel_id):
        os.makedirs(LOG_FOLDER, exist_ok=True)
        file_path = os.path.join(LOG_FOLDER, "command_log.xlsx")


        if not os.path.exists(file_path):
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Command Usage"
            ws.append(["User", "User ID", "Command", "Channel ID", "Timestamp"])
            wb.save(file_path)

        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        ws.append([
            user.display_name,
            str(user.id),
            command_name,
            str(channel_id),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        wb.save(file_path)
        
    @app_commands.command(name="dnd", description="Nhận thông tin DnD qua Direct Messages")
    @app_commands.describe(choice="Chọn bộ dữ liệu DnD")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Valentine", value="valentine"),
        app_commands.Choice(name="Atimick", value="atimick")
    ])
    async def dnd_command(self, interaction: discord.Interaction, choice: app_commands.Choice[str]):
        # Chọn file dựa theo option
        if choice.value == "valentine":
            file_name = "DnD Characters Info.json"
        elif choice.value == "atimick":
            file_name = "DnD AMO Guide.json"
        else:
            return await interaction.response.send_message("❌ Lựa chọn không hợp lệ.", ephemeral=True)

        file_path = os.path.join(os.path.dirname(__file__), file_name)

        # Log command
        self.log_command_usage(interaction.user, "dnd", interaction.channel.id)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            embeds = [discord.Embed.from_dict(e) for e in data.get("embeds", [])]

            for e in embeds:
                await interaction.user.send(embed=e)

            await interaction.response.send_message(f"📩 Đã gửi thông tin **{choice.name}** qua DM!", ephemeral=True)

        except FileNotFoundError:
            await interaction.response.send_message(f"❌ Không tìm thấy file `{file_name}`.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Không thể gửi DM, bạn hãy bật tin nhắn riêng.", ephemeral=True)

    @app_commands.command(name="am", description="📌 Hiển thị thông tin về bot Geleven")
    async def about_me(self, interaction: discord.Interaction):
        bot_user = interaction.client.user
        uptime_seconds = (datetime.utcnow() - self.bot.launch_time).total_seconds()
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))

        embed = discord.Embed(
            title=f"🤖 Thông tin về {bot_user.name}",
            description="Bot hỗ trợ quản lý máy chủ và các công cụ tiện ích.",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=bot_user.avatar.url if bot_user.avatar else None)

        embed.add_field(name="👑 Creator", value="atimick", inline=True)
        embed.add_field(name="🕒 Time Active", value=uptime_str, inline=True)
        embed.add_field(name="🌐 Server Active", value=f"{len(interaction.client.guilds)} servers", inline=False)

        embed.add_field(
            name="📎 Lệnh liên quan",
            value="• `/adm` – Dành cho Admin\n• `/user` – Lệnh công khai cho tất cả mọi người",
            inline=False
        )

        embed.set_footer(text="Được tạo bởi Ati", icon_url=bot_user.avatar.url if bot_user.avatar else None)
        embed.timestamp = datetime.utcnow()

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nitro", description="Xem danh sách thành viên đang Boost server")
    async def nitro(self, interaction: discord.Interaction):
        self.log_command_usage(interaction.user, "nitro", interaction.channel_id)

        boosters = []
        async for member in interaction.guild.fetch_members(limit=None):
            if member.premium_since:
                days = (datetime.now(tz=member.premium_since.tzinfo) - member.premium_since).days
                boosters.append((member.display_name, member.name, days, member.premium_since.strftime("%d/%m/%Y")))

        if not boosters:
            return await interaction.response.send_message("Không có ai đang Boost server.")

        embed = discord.Embed(
            title=f"📦 Danh sách Boosters - {interaction.guild.name}",
            description=f"Tổng cộng: {len(boosters)} thành viên đang Boost",
            color=discord.Color.purple()
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        embed.set_footer(
            text=f"Được yêu cầu bởi {interaction.user.name}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )

        for dn, un, d, dt in boosters:
            embed.add_field(
                name=f"{dn} | {un}",
                value=f"**Thời gian bắt đầu Boost:** {dt}\n**Tổng thời gian đã Boost:** {d} ngày",
                inline=False
            )

        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="user", description="Hiện danh sách các lệnh công khai (Public)")
    async def public_help_slash(self, interaction: discord.Interaction):
        self.log_command_usage(interaction.user, "user", interaction.channel.id)

        embed = discord.Embed(
            title="📘 Danh sách các lệnh Public",
            description="Dành cho mọi người",
            color=discord.Color.teal()
        )
        embed.add_field(name="`/user`", value="Hiện danh sách các lệnh Public", inline=False)
        embed.add_field(name="`/nitro`", value="Hiện danh sách những người đang Boost server", inline=False)
        embed.add_field(name="`/cleanpost`", value="Xoá tin nhắn trong Post được chỉ định - Hiện tại: DnD Roll", inline=False)
        embed.set_footer(text=f"Yêu cầu bởi {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cleanpost", description="Xoá tất cả tin nhắn chưa ghim trong một thread cụ thể")
    async def clean_post_slash(self, interaction: discord.Interaction):
        self.log_command_usage(interaction.user, "cleanpost", interaction.channel.id)

        allowed_thread_id = 1407873740368253050
        channel = interaction.channel

        if channel.id != allowed_thread_id:
            return await interaction.response.send_message(
                "⚠️ Lệnh này chỉ được dùng trong một thread cụ thể do Ati đặt.", ephemeral=True
            )

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return await interaction.response.send_message(
                "⚠️ Lệnh này chỉ dùng trong text hoặc thread.", ephemeral=True
            )

        await interaction.response.defer(thinking=True, ephemeral=True)

        deleted = 0
        failed = 0

        # Dùng session của bot để xóa thủ công qua HTTP -> kiểm soát rate limit
        session: aiohttp.ClientSession = self.bot.http._HTTPClient__session
        headers = {
            "Authorization": f"Bot {self.bot.http.token}"
        }

        try:
            async for msg in channel.history(limit=None, oldest_first=False):
                if msg.pinned:
                    continue

                while True:
                    async with session.delete(
                        f"https://discord.com/api/v10/channels/{channel.id}/messages/{msg.id}",
                        headers=headers
                    ) as resp:
                        if resp.status == 204:
                            deleted += 1
                            break
                        elif resp.status == 429:  # rate limit
                            data = await resp.json()
                            retry_after = data.get("retry_after", 1)
                            await asyncio.sleep(retry_after + 0.05)  # thêm buffer
                        else:
                            failed += 1
                            break

        except discord.Forbidden:
            return await interaction.followup.send("❌ Bot không có quyền xoá tin nhắn.")

        await interaction.followup.send(
            f"✅ Đã xoá `{deleted}` tin nhắn chưa ghim.\n❗ Không thể xoá `{failed}` tin nhắn do lỗi hoặc quyền hạn.",
            ephemeral=True
        )

    @app_commands.command(name="whereami", description="Check channel ID")
    async def whereami(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Bạn đang ở channel: `{interaction.channel.name}`\nID: `{interaction.channel.id}`\nType: `{type(interaction.channel)}`",
            ephemeral=True
        )
        
async def setup(bot):
    cog = PubOne(bot)
    await bot.add_cog(cog)
