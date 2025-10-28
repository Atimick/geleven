import discord
import os
from datetime import datetime
from discord import app_commands, Interaction
from discord.ext import commands
# ✅ Import DB_PATH thay vì LOG_FOLDER
from .id_check import is_allowed, DB_PATH 
import re
# ✅ Import SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# START SQLALCHEMY SETUP
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

# Khai báo Cog
class MassDeleteChannel(commands.Cog):
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

    @app_commands.command(name="mdc", description="Xóa hàng loạt kênh từ file đính kèm (Allowed Users Only)")
    @app_commands.describe(file="File chứa danh sách Channel ID, mỗi ID một dòng.")
    @app_commands.check(is_allowed) # Yêu cầu quyền cứng (is_allowed)
    @app_commands.default_permissions(manage_channels=True)
    async def mass_delete_channel(self, interaction: Interaction, file: discord.Attachment):
        
        # ✅ GHI LOGS
        self.log_command_usage(interaction.user, "mdc", interaction)

        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bot cần quyền **Quản lý kênh** để thực hiện lệnh này.", ephemeral=True)
            return

        # Chỉ chấp nhận file text
        if not file.filename.endswith(('.txt', '.list', '.ids')):
            await interaction.response.send_message("❌ Vui lòng đính kèm file text (.txt, .list, .ids) chứa Channel ID.", ephemeral=True)
            return
        
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            # Tải nội dung file
            content = await file.read()
            content_str = content.decode('utf-8')
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi đọc file: `{e}`", ephemeral=True)
            return

        # Lấy Channel ID (chỉ giữ lại số)
        channel_ids_str = re.findall(r'\d+', content_str)
        channel_ids = [int(cid) for cid in channel_ids_str]

        if not channel_ids:
            await interaction.followup.send("❌ File không chứa ID hợp lệ để xóa! (Chỉ chấp nhận số ID).", ephemeral=True)
            return

        deleted = []
        failed = []

        for cid in channel_ids:
            # Lấy kênh (get_channel có thể trả về None nếu không tìm thấy)
            channel = interaction.guild.get_channel(cid)
            if channel:
                # Kiểm tra Bot có quyền quản lý kênh không (quyền delete channel)
                if not channel.permissions_for(interaction.guild.me).manage_channels:
                    failed.append((f"{channel.name} ({channel.id})", "Bot thiếu quyền Quản lý kênh"))
                    continue

                # Tránh xóa kênh hiện tại (kênh mà lệnh được gọi)
                if channel.id == interaction.channel_id:
                    failed.append((f"{channel.name} ({channel.id})", "Không thể xóa kênh hiện tại"))
                    continue
                    
                try:
                    await channel.delete(reason=f"MDC File (Thanh lý bởi {interaction.user.name})")
                    deleted.append(f"#{channel.name} ({channel.id})")
                except Exception as e:
                    failed.append((f"#{channel.name} ({channel.id})", str(e)))
            else:
                failed.append((str(cid), "Không tìm thấy trong server"))

        # Tạo tin nhắn phản hồi
        msg = ""
        if deleted:
            msg += f"✅ Đã thanh lý **{len(deleted)}** kênh:\n" + "\n".join(deleted[:10])
            if len(deleted) > 10:
                msg += f"\n*... và {len(deleted) - 10} kênh khác.*"

        if failed:
            if msg:
                msg += "\n\n"
            msg += f"❌ Lỗi khi xử lý **{len(failed)}** kênh:\n"
            msg += "\n".join(f"{name} ({reason})" for name, reason in failed[:10])
            if len(failed) > 10:
                msg += f"\n*... và {len(failed) - 10} kênh khác.*"

        if not msg:
            msg = "⚠️ Không có kênh nào được xử lý."
            
        # Giới hạn tin nhắn Discord
        if len(msg) > 2000:
            msg = msg[:1950] + "\n... (Tin nhắn quá dài, đã cắt bớt)"

        await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MassDeleteChannel(bot))