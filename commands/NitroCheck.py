import discord
import os
from discord.ext import commands
from discord import app_commands, Interaction, Embed, File
from datetime import datetime, timedelta, timezone 
from zoneinfo import ZoneInfo
from .id_check import BOOST_LOG_PATH, DB_PATH
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import openpyxl

# ✅ START SQLALCHEMY SETUP
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
    
Base.metadata.create_all(Engine) 

class CheckNitro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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

    @app_commands.command(name="checknitro", description="Kiểm tra danh sách thành viên đang Boost server (Admin Only)")
    @app_commands.default_permissions(manage_guild=True) # Chỉ người có quyền Quản lý Server mới dùng được
    async def check_nitro(self, interaction: Interaction):
        self.log_command_usage(interaction.user, "checknitro", interaction)
        
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        guild = interaction.guild
        if not guild:
            return await interaction.followup.send("Lệnh này chỉ dùng được trong server.", ephemeral=True)
        boosters = []
        for member in guild.members:
            if member.premium_since:
                boost_utc = member.premium_since.replace(tzinfo=timezone.utc)
                boost_vn = boost_utc.astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
                
                # Tính số ngày Boost
                days = (datetime.now(timezone.utc) - boost_utc).days
                
                boosters.append((member, days, boost_utc, boost_vn))
        
        if not boosters:
            await interaction.followup.send("⚠️ Không có ai đang Boost server.", ephemeral=True)
            return

        # 1. TẠO FILE EXCEL (Phần export data, giữ nguyên logic Excel)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Boosters"
        headers = ["Display Name", "Username", "User ID", "Boost Start (UTC)", "Boost Start (VN)", "Boost Days"]
        ws.append(headers)

        for m, d, utc, vn in boosters:
            ws.append([m.display_name, m.name, str(m.id), utc.strftime('%d/%m/%Y %H:%M:%S'), vn.strftime('%d/%m/%Y %H:%M:%S'), d])

        # Đảm bảo thư mục log tồn tại và lưu file vào đường dẫn BOOST_LOG_PATH
        os.makedirs(os.path.dirname(BOOST_LOG_PATH), exist_ok=True)
        wb.save(BOOST_LOG_PATH)
        
        # 2. Gửi kết quả
        embed = Embed(
            title="💎 Danh sách Boosters",
            description=f"✅ Hiện có **{len(boosters)}** thành viên đang Boost server.\n📄 Chi tiết đã được xuất ra file Excel đính kèm.",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Server Boost Level: {guild.premium_tier}. Total Boosts: {guild.premium_subscription_count}")
        
        file = File(BOOST_LOG_PATH)
        await interaction.followup.send(embed=embed, file=file)
        
        # Xóa file sau khi gửi (tùy chọn để dọn dẹp)
        os.remove(BOOST_LOG_PATH)


async def setup(bot):
    await bot.add_cog(CheckNitro(bot))