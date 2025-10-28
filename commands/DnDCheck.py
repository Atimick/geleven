import discord
import os
import json
# import openpyxl # Đã loại bỏ
from discord.ext import commands
from discord import app_commands, Interaction
from datetime import datetime
from zoneinfo import ZoneInfo
# Đã thay LOG_FOLDER bằng DB_PATH
from .id_check import DB_PATH 

# ✅ START SQLALCHEMY SETUP
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
# ✅ END SQLALCHEMY SETUP

class DnDCog(commands.Cog):
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

    @app_commands.command(name="dnd", description="Gửi thông tin nhân vật DnD qua DM.")
    async def dnd_command(self, interaction: discord.Interaction):
        
        # ✅ Cập nhật call log để truyền đối tượng interaction
        self.log_command_usage(interaction.user, "dnd", interaction)

        file_name = "DnD Characters Info.json"
        
        # Đường dẫn file json (giữ nguyên logic tìm file)
        file_path = os.path.join(os.path.dirname(__file__), file_name)

        try:
            await interaction.response.defer(thinking=True, ephemeral=True) 

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            embeds = [discord.Embed.from_dict(e) for e in data.get("embeds", [])]

            if not embeds:
                 await interaction.followup.send("❌ File JSON không chứa Embed nào.", ephemeral=True)
                 return

            for e in embeds:
                # Gửi embed qua DM
                await interaction.user.send(embed=e)

            await interaction.followup.send(f"📩 Đã gửi thông tin **Valentine** qua DM! (Tổng cộng {len(embeds)} tin nhắn).", ephemeral=True)

        except FileNotFoundError:
            await interaction.followup.send(f"❌ Không tìm thấy file `{file_name}`. Hãy đảm bảo file nằm cùng thư mục.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Không thể gửi DM, bạn hãy bật tin nhắn riêng hoặc Bot không có quyền gửi DM.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Đã xảy ra lỗi không mong muốn: `{e}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(DnDCog(bot))