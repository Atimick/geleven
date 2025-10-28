import discord
import os
from datetime import datetime
from discord import app_commands, Interaction, ChannelType
from discord.ext import commands
from zoneinfo import ZoneInfo
from .id_check import is_admin
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .id_check import is_admin, DB_PATH

Engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

class LogCommandUsage(Base):
    """Mô hình SQLAlchemy cho bảng logs việc sử dụng các lệnh Admin."""
    __tablename__ = 'command_usage_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    guild_id = Column(String) # ID Server
    guild_name = Column(String) # Tên Server
    channel_id = Column(String)
    command_name = Column(String)
    user_id = Column(String)
    user_name = Column(String)

Base.metadata.create_all(Engine)

class PurgeChat(commands.Cog): # CLASS MỚI: PurgeChat
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
            session.commit() # Ghi vào bot_data.db
            
        except Exception as db_error:
            session.rollback() # Hoàn tác nếu có lỗi
            # Có thể log lỗi ra console để debug, nhưng không gửi cho người dùng Discord
            print(f"Lỗi khi ghi logs SQLAlchemy: {db_error}") 
        finally:
            session.close()

    @app_commands.command(name="purgechat", description="Xóa tin nhắn trong kênh chat, bao gồm cả kênh voice chat. (Admin Only)")
    @app_commands.check(is_admin) # CHỈ ADMIN ID CỨNG MỚI ĐƯỢC DÙNG
    async def purgechat(self, interaction: Interaction):
        """
        Xóa tất cả tin nhắn trong kênh hiện tại ngược về quá khứ 14 ngày,
        không xóa tin nhắn đã ghim và tin nhắn gửi sau khi lệnh được gọi.
        """
        if not is_admin(interaction):
            return await interaction.response.send_message("❌ Bạn không có quyền **Admin** để dùng lệnh này.", ephemeral=True)
            
        self.log_command_usage(interaction.user, "purgechat", interaction)

        target_channel = interaction.channel
        
        # ... (Phần kiểm tra kênh và quyền giữ nguyên)
        if not isinstance(target_channel, (discord.TextChannel, discord.VoiceChannel)):
            await interaction.response.send_message(
                "❌ Lệnh này chỉ có thể được sử dụng trong các kênh chat hoặc kênh voice có chat.",
                ephemeral=True
            )
            return

        if isinstance(target_channel, discord.VoiceChannel):
            if not target_channel.permissions_for(interaction.guild.me).manage_messages:
                 await interaction.response.send_message(
                    "❌ Bot cần quyền **Quản lý tin nhắn** trong kênh voice này.",
                    ephemeral=True
                )
                 return
            pass 

        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            deleted_messages = await target_channel.purge(
                limit=None,
                before=interaction.created_at,
                check=lambda m: not m.pinned
            )
            
            await interaction.followup.send(
                f"🧹 Đã dọn dẹp thành công **{len(deleted_messages)}** tin nhắn.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot không có quyền **Quản lý tin nhắn** trong kênh này.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Đã xảy ra lỗi không mong muốn: `{e}`",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(PurgeChat(bot))