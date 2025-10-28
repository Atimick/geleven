import discord
import os
import yt_dlp
import asyncio
import json
import aiohttp
import textwrap
import secrets
import socket
import requests
from zoneinfo import ZoneInfo
from .id_check import is_admin, is_ati_admin, DB_PATH
from discord.ext import commands
from discord import app_commands, Interaction 
from datetime import datetime, timedelta

# START SQLALCHEMY SETUP
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

class LogCommandUsage(Base):
    """Mô hình SQLAlchemy cho bảng logs việc sử dụng các lệnh quản lý chung và Public."""
    __tablename__ = 'command_usage_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    guild_id = Column(String) 
    guild_name = Column(String) 
    channel_id = Column(String)
    command_name = Column(String)
    user_id = Column(String)
    user_name = Column(String)
    
# Tạo bảng nếu chưa tồn tại
Base.metadata.create_all(Engine) 
# END SQLALCHEMY SETUP

class PubOne(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # HÀM GHI LOGS (Dùng SQLAlchemy)
    def log_command_usage(self, user: discord.User, command_name: str, interaction: Interaction):
        session = Session() 
        try:
            guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
            guild_name = interaction.guild.name if interaction.guild else "DM"
            
            new_log = LogCommandUsage(
                guild_id=guild_id,
                guild_name=guild_name,
                channel_id=str(interaction.channel_id),
                command_name=command_name,
                user_id=str(user.id),
                user_name=str(user)
            )
            
            session.add(new_log)
            session.commit()
            
        except Exception as db_error:
            session.rollback() 
            print(f"Lỗi khi ghi logs SQLAlchemy cho {command_name}: {db_error}") 
        finally:
            session.close()

    @app_commands.command(name="status", description="Kiểm tra trạng thái và thông tin của Bot (Admin có thể xem thêm IP).")
    async def status(self, interaction: Interaction):

        # GHI LOGS
        self.log_command_usage(interaction.user, "status", interaction)

        await interaction.response.defer(thinking=True) # Defer ngay lập tức

        # 1. Tính toán Latency
        latency = round(self.bot.latency * 1000)

        # 2. Tính toán HTTP Ping
        # Gửi request GET đến API Discord để đo latency HTTP
        start_time = datetime.now()
        async with aiohttp.ClientSession() as session:
            try:
                # Gửi request GET đơn giản đến Discord API để đo thời gian phản hồi
                # Không cần headers hay data
                async with session.get("https://discord.com/api/v10/gateway") as resp:
                    pass # Chỉ cần đo thời gian phản hồi
            except Exception:
                pass

        http_latency = round((datetime.now() - start_time).total_seconds() * 1000)
        
        # 3. Lấy Public IP (Chỉ Admin)
        public_ip = None
        if is_admin(interaction):
            try:
                # Dùng Google DNS để tránh bị rate limit hoặc lỗi
                response = requests.get("https://domains.google.com/checkip")
                if response.status_code == 200:
                    # Lấy IP từ phản hồi, thường là dạng {"ip": "xxx.xxx.xxx.xxx"}
                    try:
                        public_ip_data = response.json()
                        public_ip = public_ip_data.get("ip")
                    except requests.exceptions.JSONDecodeError:
                        public_ip = response.text.strip() # Nếu không phải JSON

            except Exception as e:
                print(f"Lỗi khi lấy public IP: {e}")
                public_ip = "Lỗi khi lấy IP"


        # 4. Tính Uptime và thời gian VN
        bot = self.bot # Giả sử bot có launch_time
        now_utc = datetime.utcnow()
        uptime_delta = now_utc - bot.launch_time # Phải đảm bảo bot.launch_time được set trong on_ready
        uptime_str = str(timedelta(seconds=int(uptime_delta.total_seconds())))

        # 5. Tạo Embed
        embed = discord.Embed(
            title="🏓 Geleven Bot Status",
            description="Thông tin hoạt động và kết nối của bot:",
            color=discord.Color.green()
        )
        embed.add_field(name="🌐 WebSocket Latency", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="📡 HTTP Ping", value=f"`{http_latency}ms`", inline=True)
        embed.add_field(name="🕒 Uptime", value=f"`{uptime_str}`", inline=True)

        if is_admin(interaction) and public_ip:
            embed.add_field(name="🌍 Server IP (Public)", value=f"`{public_ip}`", inline=False) 
        else:
            embed.add_field(name="🌍 Server IP (Public)", value="`[Chỉ Admin thấy]`", inline=False) 


        # Lấy thời gian VN
        now_vn = now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        embed.set_footer(text=f"Thời gian hiện tại (VN): {now_vn.strftime('%Y-%m-%d %H:%M:%S')}")
        
        await interaction.followup.send(embed=embed)


    # Lệnh /ping (Public)
    @app_commands.command(name="ping", description="Kiểm tra độ trễ (latency) của Bot.")
    async def ping(self, interaction: Interaction):
        
        # GHI LOGS
        self.log_command_usage(interaction.user, "ping", interaction)

        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! Độ trễ hiện tại là: `{latency}ms`", ephemeral=True)

async def setup(bot):
    # Gán thời điểm khởi động nếu chưa có (dùng cho /botstatus)
    if not hasattr(bot, 'launch_time'):
        bot.launch_time = datetime.utcnow()
    await bot.add_cog(PubOne(bot))