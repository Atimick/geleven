import discord
from discord import app_commands, Interaction
from discord.ext import commands
from datetime import datetime
from .id_check import is_admin, DB_PATH

# ✅ START SQLALCHEMY SETUP
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

class LogCommandUsage(Base):
    """Mô hình SQLAlchemy cho bảng logs việc sử dụng các lệnh Admin/Quản trị."""
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

class ExtensionManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ HÀM GHI LOGS MỚI (Dùng SQLAlchemy)
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

    # Lệnh /load
    @app_commands.command(name="load", description="Tải module (chỉ Admin)")
    @app_commands.check(is_admin)
    @app_commands.describe(extension="Tên module (Ex: CommandsAM)")
    async def load_extension(self, interaction: Interaction, extension: str):
        
        self.log_command_usage(interaction.user, f"load {extension}", interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)
        extension_path = f"commands.{extension}"
        try:
            await self.bot.load_extension(extension_path)
            await self.bot.tree.sync()
            await interaction.followup.send(f"✅ Done. Module **`{extension}.py`** loaded.", ephemeral=True)
        except commands.ExtensionAlreadyLoaded:
            await interaction.followup.send(f"⚠️ Module **`{extension}.py`** đã được tải. Hãy dùng `/reload`.", ephemeral=True)
        except commands.ExtensionNotFound:
            await interaction.followup.send(f"❌ Module `{extension}.py` không tồn tại.", ephemeral=True)
        except Exception as e:
            error_msg = getattr(e, 'original', e)
            await interaction.followup.send(f"❌ Lỗi khi tải: `{error_msg}`", ephemeral=True)


    # Lệnh /unload
    @app_commands.command(name="unload", description="Gỡ module (chỉ Admin)")
    @app_commands.check(is_admin)
    @app_commands.describe(extension="Tên module (Ex: CommandsAM)")
    async def unload_extension(self, interaction: Interaction, extension: str):
        
        self.log_command_usage(interaction.user, f"unload {extension}", interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)
        extension_path = f"commands.{extension}"
        try:
            await self.bot.unload_extension(extension_path)
            await self.bot.tree.sync()
            await interaction.followup.send(f"✅ Done. Module **`{extension}.py`** unloaded.", ephemeral=True)
        except commands.ExtensionNotLoaded:
            await interaction.followup.send(f"⚠️ Module **`{extension}.py`** chưa được tải.", ephemeral=True)
        except Exception as e:
            error_msg = getattr(e, 'original', e)
            await interaction.followup.send(f"❌ Lỗi khi gỡ: `{error_msg}`", ephemeral=True)

    # Lệnh /reload
    @app_commands.command(name="reload", description="Tải lại module (chỉ Admin)")
    @app_commands.check(is_admin)
    @app_commands.describe(extension="Tên module (Ex: CommandsAM)")
    async def reload_extension(self, interaction: Interaction, extension: str):
        
        self.log_command_usage(interaction.user, f"reload {extension}", interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)
        extension_path = f"commands.{extension}"
        try:
            await self.bot.reload_extension(extension_path)
            await self.bot.tree.sync() 
            await interaction.followup.send(f"✅ Module **`{extension}.py`** reloaded.", ephemeral=True)
        except commands.ExtensionNotLoaded:
            await interaction.followup.send(f"⚠️ Module **`{extension}.py`** is not loaded. Trying to load it...", ephemeral=True)
            try:
                await self.bot.load_extension(extension_path)
                await self.bot.tree.sync()
                await interaction.followup.send(f"✅ Module **`{extension}.py`** loaded after reload attempt.", ephemeral=True)
            except Exception as e:
                error_msg = getattr(e, 'original', e)
                await interaction.followup.send(f"❌ Lỗi khi tải lại: `{error_msg}`", ephemeral=True)
        except commands.ExtensionNotFound:
            await interaction.followup.send(f"❌ Module `{extension}.py` not found.", ephemeral=True)
        except Exception as e:
            error_msg = getattr(e, 'original', e)
            await interaction.followup.send(f"❌ Lỗi khi tải lại: `{error_msg}`", ephemeral=True)
            

    # Lệnh /sync
    @app_commands.command(name="sync", description="Đồng bộ lệnh (chỉ Admin)")
    @app_commands.check(is_admin)
    async def sync_commands(self, interaction: Interaction):
        
        self.log_command_usage(interaction.user, "sync", interaction)
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            await self.bot.tree.sync()
            await interaction.followup.send("✅ Đã đồng bộ lệnh Slash thành công.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi khi đồng bộ lệnh: `{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ExtensionManager(bot))