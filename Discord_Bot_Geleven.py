import discord
import shutil
import sys
import os
import requests
from discord import app_commands
from commands.id_check import is_admin, is_allowed, is_ati_admin
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from zoneinfo import ZoneInfo
from commands.CommandsAM import setup as setup_am
from commands.CommandsPublic import setup as setup_pub
from commands.CommandsPublicMusic import setup as setup_music
from commands.MessageForwarder import setup as setup_forwarder
from commands.Public_Roll_Dice import setup as setup_roll
from commands.BHG_AMCC import setup as setup_member_management
from commands.TicketSystem import setup as setup_ticket
from commands.NitroCheck import setup as setup_nitro
from commands.DnDCheck import setup as setup_dnd
from commands.CleanPost import setup as setup_cleanpost
from commands.MassDeleteKick import setup as setup_mdk 
from commands.MassDeleteChannel import setup as setup_mdc 
from commands.PurgeChat import setup as setup_purgechat
from commands.ExportChannels import setup as setup_exportchannels
from commands.ExportMembers import setup as setup_exportmembers
from commands.FakeJoin import setup as setup_voice_master
from commands.CheckServerList import setup as setup_check_server_list
from commands.UserInfo import setup as setup_userinfo
from commands.ExtensionManager import setup as setup_ext_manager

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

now_vn = datetime.now(timezone(timedelta(hours=7)))
#bot = commands.Bot(command_prefix=commands.when_mentioned_or(), intents=intents, help_command=None)
bot = commands.Bot(command_prefix="g ", intents=discord.Intents.all(), help_command=None)
bot.slash_synced = False 

def print_startup_console(bot):
    import shutil
    width = shutil.get_terminal_size().columns
    LINE_LENGTH = min(width, 80) 
    line = "═" * LINE_LENGTH # Dùng ký tự '═' cho giống style cũ
    header_text = "GELEVEN BOT"
    print(f"\033[95m\n{line}\033[0m")
    print(f"\033[96m{header_text.center(LINE_LENGTH)}\033[0m")
    print(f"\033[95m{line}\033[0m")
    bot_online = f"✅ Logged in as: {bot.user} (ID: {bot.user.id})"
    print(f"\033[92m{bot_online.ljust(LINE_LENGTH)}\033[0m")
    if bot.slash_synced:
        slash_status = "✅ Slash Commands: Synced successfully!"
        print(f"\033[94m{slash_status.ljust(LINE_LENGTH)}\033[0m")
    else:
        slash_status = "⚠️ Slash Commands: Not yet synced!"
        print(f"\033[93m{slash_status.ljust(LINE_LENGTH)}\033[0m")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\033[90mStartup Time (Local): {now}\033[0m")
    print(f"\033[95m{line}\033[0m")
    print("\n")
    
@bot.event
async def on_ready():
    print_startup_console(bot)

# ✅ ĐẢM BẢO SYNC LỆNH SLASH
async def setup_hook():
    bot.launch_time = datetime.utcnow()
    await setup_am(bot)
    await setup_pub(bot)
    #await setup_music(bot)
    await setup_forwarder(bot)
    await setup_roll(bot)  
    await setup_member_management(bot)
    await setup_ticket(bot)
    await setup_nitro(bot)
    await setup_dnd(bot)
    await setup_cleanpost(bot)
    await setup_mdk(bot)
    await setup_mdc(bot)
    await setup_purgechat(bot)
    await setup_exportchannels(bot)
    await setup_exportmembers(bot)
    await setup_voice_master(bot)
    await setup_check_server_list(bot)
    await setup_userinfo(bot)
    await setup_ext_manager(bot)
    await bot.tree.sync()
    bot.slash_synced = True

bot.setup_hook = setup_hook
bot.run(TOKEN)