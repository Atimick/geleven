import discord
import os
import aiohttp
import asyncio
from discord.ext import commands
from discord import app_commands, Interaction
from datetime import datetime
from .id_check import is_allowed, DB_PATH 
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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
    
# ✅ ĐÃ SỬA: Tạo bảng ở cấp độ module
Base.metadata.create_all(Engine) 

class ManagementCommands(commands.Cog):
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
            print(f"Lỗi khi ghi logs SQLAlchemy cho /cleanpost: {db_error}") 
        finally:
            session.close()

    @app_commands.command(name="cleanpost", description="Xoá tất cả tin nhắn chưa ghim trong một thread cụ thể (Allowed Users Only)")
    @app_commands.check(is_allowed) 
    async def clean_post_slash(self, interaction: discord.Interaction):
        
        if not is_allowed(interaction):
            return await interaction.response.send_message("❌ Bạn không có quyền **Manage Server/Admin** để dùng lệnh này.", ephemeral=True)
            
        self.log_command_usage(interaction.user, "cleanpost", interaction)

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
                        elif resp.status == 429:
                            data = await resp.json()
                            retry_after = data.get("retry_after", 1)
                            await asyncio.sleep(retry_after + 0.05)
                        else:
                            failed += 1
                            break

        except discord.Forbidden:
            return await interaction.followup.send("❌ Bot không có quyền xoá tin nhắn.")
        except Exception as e:
            return await interaction.followup.send(f"❌ Đã xảy ra lỗi không mong muốn trong quá trình xóa: `{e}`", ephemeral=True)


        await interaction.followup.send(
            f"✅ Đã xoá `{deleted}` tin nhắn chưa ghim.\n❗ Không thể xoá `{failed}` tin nhắn do lỗi hoặc quyền hạn.",
            ephemeral=True
        )

async def setup(bot):
    cog = ManagementCommands(bot)
    await bot.add_cog(cog)