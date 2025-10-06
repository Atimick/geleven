import discord
import os
import aiohttp
import socket
import shutil
import sys
import requests
from discord import app_commands
from commands.id_check import is_admin, is_mod, is_allowed, is_ati_admin
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from zoneinfo import ZoneInfo
from commands.CommandsAM import setup as setup_am
from commands.CommandsPublic import setup as setup_pub
from commands.Moderator import setup as setup_ModCommands
from commands.CommandsPublicMusic import setup as setup_music
from commands.MessageForwarder import setup as setup_forwarder
from commands.Public_Roll_Dice import setup as setup_roll
from commands.BHG_AMCC import setup as setup_member_management

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
# === CÁC ĐƯỜNG DẪN LOG ===
LOG_FOLDER = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs"
BOOST_LOG_PATH = "C:/Users/nguye/Downloads/DC_Bot_Geleven/Geleven_Logs_Nitro/boosters_log.xlsx"
EXPORT_FOLDER = "C:/Users/nguye/Downloads/DC_Bot_Geleven/exports"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

now_vn = datetime.now(timezone(timedelta(hours=7)))
#bot = commands.Bot(command_prefix=commands.when_mentioned_or(), intents=intents, help_command=None)
bot = commands.Bot(command_prefix="g ", intents=discord.Intents.all(), help_command=None)
bot.slash_synced = False  # Đánh dấu việc Slash đã sync chưa

def print_startup_console(bot):
    import shutil
    width = shutil.get_terminal_size().columns
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Header
    line = "═" * (width)
    print(f"\033[95m{line}\033[0m")
    header_text = "Geleven Bot Console Startup"
    print(f"\033[96m║{header_text.center(width - 2)}║\033[0m")
    print(f"\033[95m{line}\033[0m")

    # Bot Info
    bot_online = "✅ BOT ONLINE"
    print(f"\033[92m║ {bot_online.ljust(width - 3)}║\033[0m")
    login_info = f"ℹ️  Logged in as {bot.user} (ID: {bot.user.id})"
    print(f"\033[96m║ {login_info.ljust(width - 3)}║\033[0m")

    # Guild Info
    guilds = bot.guilds
    total_members = sum(g.member_count for g in guilds)
    unique_users = len(set(bot.get_all_members()))
    guild_info = f"🌐 Servers: {len(guilds)} | Total Members: {total_members} | Unique Users: {unique_users}"
    print(f"\033[96m║ {guild_info.ljust(width - 3)}║\033[0m")
    print(f"\033[96m║{''.ljust(width - 2)}║\033[0m")

    # Paths
    command_log = f"📂 Command logs: {os.path.join(LOG_FOLDER, 'command_log.xlsx')}"
    print(f"\033[94m║ {command_log.ljust(width - 3)}║\033[0m")
    boost_log = f"📂 Boost logs: {BOOST_LOG_PATH}"
    print(f"\033[94m║ {boost_log.ljust(width - 3)}║\033[0m")
    export_folder = f"📂 Export folder: {EXPORT_FOLDER}/members_<server_id>.xlsx"
    print(f"\033[94m║ {export_folder.ljust(width - 3)}║\033[0m")
    print(f"\033[95m{line}\033[0m")

    # Slash Commands
    if bot.slash_synced:
        slash_synced = "✅ Slash commands đã đồng bộ với Discord"
        print(f"\033[92m║ {slash_synced.ljust(width - 3)}║\033[0m")
    print(f"\033[95m{line}\033[0m")
    
    # Startup Time
    startup_time = f"Startup Time: {now}"
    print(f"\033[90m║ {startup_time.ljust(width - 3)}║\033[0m")
    print(f"\033[95m{line}\033[0m")

@bot.event
async def on_ready():
    print_startup_console(bot)

# ✅ ĐẢM BẢO SYNC LỆNH SLASH
async def setup_hook():
    bot.launch_time = datetime.utcnow()
    await setup_am(bot)
    await setup_pub(bot)
    #await setup_music(bot)
    await setup_ModCommands(bot)
    await setup_forwarder(bot)
    await setup_roll(bot)  
    await setup_member_management(bot)
    await bot.tree.sync()
    bot.slash_synced = True

bot.setup_hook = setup_hook

@bot.tree.command(name="ping", description="Kiểm tra độ trễ, uptime, IP server, v.v.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)

    start_time = datetime.utcnow()
    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/v10") as resp:
            pass
    http_latency = round((datetime.utcnow() - start_time).total_seconds() * 1000)

    # Server IP local
    try:
        hostname = socket.gethostname()
        server_ip = socket.gethostbyname(hostname)
    except Exception:
        server_ip = "Không xác định"

    # Nếu là admin => lấy thêm IP Public
    public_ip = None
    if is_admin(interaction):
        try:
            response = requests.get("https://api.ipify.org")
            if response.status_code == 200:
                public_ip = response.text
        except Exception:
            public_ip = "Không xác định"

    now_utc = datetime.utcnow()
    now_vn = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    uptime_delta = now_utc - bot.launch_time
    uptime_str = str(timedelta(seconds=int(uptime_delta.total_seconds())))

    embed = discord.Embed(
        title="🏓 Geleven Bot Status",
        description="Thông tin hoạt động và kết nối của bot:",
        color=discord.Color.green()
    )
    embed.add_field(name="🌐 WebSocket Latency", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="📡 HTTP Ping", value=f"`{http_latency}ms`", inline=True)
    embed.add_field(name="🕒 Uptime", value=f"`{uptime_str}`", inline=True)
    embed.add_field(name="🖥️ Server IP (Local)", value=f"`{server_ip}`", inline=False)

    if public_ip:
        embed.add_field(name="🌍 Server IP (Public)", value=f"`{public_ip}`", inline=False)

    embed.set_footer(text=f"Geleven • Cập nhật: {now_vn.strftime('%H:%M:%S | %d-%m-%Y')} (VN)")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="reload", description="Tải lại một module lệnh đã sửa (Chỉ Admin).")
@app_commands.describe(extension="Load Modules")
async def reload_extension(interaction: discord.Interaction, extension: str):
    # Dùng hàm is_ati_admin đã định nghĩa để kiểm tra quyền hạn
    if not is_ati_admin(interaction): # <-- THAY is_admin BẰNG is_ati_admin
        await interaction.response.send_message("❌ Bạn không có quyền **Admin** để sử dụng lệnh này tại server này.", ephemeral=True)
        return

    extension_path = f"commands.{extension}" 
    
    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
        if extension_path in bot.extensions:
            # Nếu module đã được tải, thì unload và load lại
            await bot.unload_extension(extension_path)
            await bot.load_extension(extension_path)
            
            # Cần đồng bộ lại lệnh Slash TREE sau khi thay đổi lệnh
            await bot.tree.sync() 

            # Cần xử lý lại MusicQueue cho đa Guild nếu module nhạc được reload
            if extension == "CommandsPublicMusic":
                pass # Hiện tại không cần sửa gì thêm ở đây nếu đã dùng get_music_queue

            await interaction.followup.send(f"✅ Đã tải lại module **`{extension}.py`** thành công.", ephemeral=True)
        else:
            # Nếu module chưa được tải, thì load lần đầu
            await bot.load_extension(extension_path)
            await bot.tree.sync()
            await interaction.followup.send(f"✅ Đã tải module **`{extension}.py`** (lần đầu) thành công.", ephemeral=True)
            
    except commands.ExtensionNotFound:
        await interaction.followup.send(f"❌ Không tìm thấy module: `{extension}.py` (Đảm bảo tên đúng, ví dụ: CommandsPublicMusic)", ephemeral=True)
    except commands.ExtensionNotLoaded:
        # Trường hợp này hiếm, nhưng đề phòng
        await interaction.followup.send(f"❌ Module `{extension}.py` chưa được tải. Đang thử tải lại...", ephemeral=True)
        try:
            await bot.load_extension(extension_path)
            await bot.tree.sync()
            await interaction.followup.send(f"✅ Đã tải module **`{extension}.py`** thành công.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi khi tải lại: `{e}`", ephemeral=True)
    except Exception as e:
        # e.original chứa lỗi thực tế nếu là ExtensionFailed
        error_msg = getattr(e, 'original', e)
        await interaction.followup.send(f"❌ Lỗi khi tải/tải lại module `{extension}.py`:\n```python\n{error_msg}\n```", ephemeral=False)
            
bot.run(TOKEN)