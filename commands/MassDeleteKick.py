import discord
import os
from datetime import datetime
from discord import app_commands, Interaction
from discord.ext import commands
# ✅ Import DB_PATH thay vì LOG_FOLDER
from .id_check import is_allowed, is_admin, DB_PATH
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

class MassDeleteKick(commands.Cog): 
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

    @app_commands.command(name="mdk", description="Kick hàng loạt thành viên từ file đính kèm (Allowed Users Only)")
    @app_commands.describe(file="File chứa danh sách User ID, mỗi ID một dòng.")
    @app_commands.check(is_allowed) # Yêu cầu quyền cứng (is_allowed)
    @app_commands.default_permissions(kick_members=True)
    async def mass_delete_kick(self, interaction: Interaction, file: discord.Attachment):
        
        # ✅ GHI LOGS
        self.log_command_usage(interaction.user, "mdk", interaction)

        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.response.send_message("❌ Bot cần quyền **Kick thành viên** để thực hiện lệnh này.", ephemeral=True)
            return

        # Chỉ chấp nhận file text
        if not file.filename.endswith(('.txt', '.list', '.ids')):
            await interaction.response.send_message("❌ Vui lòng đính kèm file text (.txt, .list, .ids) chứa User ID.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=True)
        
        try:
            # Tải nội dung file
            content = await file.read()
            content_str = content.decode('utf-8')
        except Exception as e:
            await interaction.followup.send(f"❌ Lỗi đọc file: `{e}`", ephemeral=True)
            return

        # Lấy User ID (loại bỏ khoảng trắng, dòng trống và chỉ giữ lại số)
        user_ids_str = re.findall(r'\d+', content_str)
        user_ids = [int(uid) for uid in user_ids_str]

        if not user_ids:
            await interaction.followup.send("❌ File không chứa ID hợp lệ để kick! (Chỉ chấp nhận số ID).", ephemeral=True)
            return

        kicked = []
        failed = []

        for uid in user_ids:
            member = interaction.guild.get_member(uid)
            if member:
                # Tránh kick Admin (ID cứng) và chính bot. 
                # Dùng is_admin cứng ở đây để bảo vệ các Admin đã hardcode ID.
                # Cần tạo discord.Object để truyền vào is_admin nếu không có interaction
                # Tuy nhiên, cách tốt hơn là kiểm tra roles hoặc permissions. Ở đây giữ nguyên is_admin(discord.Object) của code cũ
                # Nhưng do is_admin yêu cầu Interaction, ta dùng cách kiểm tra ID trực tiếp như sau:
                
                # Kiểm tra Bot và Admin cứng
                # LƯU Ý: is_admin(interaction) là kiểm tra người gọi lệnh.
                # Nếu muốn kiểm tra member có phải admin không, ta phải dùng cách khác.
                # Tạm thời giữ nguyên logic is_admin(discord.Object(id=member.id)) nếu nó hoạt động trước đây.
                
                # Sửa lại: Dùng permissions_for để kiểm tra quyền Admin của member
                # member_is_admin = member.guild_permissions.administrator
                
                # Giữ nguyên logic bảo vệ Admin ID cứng như code cũ:
                if member.id == interaction.client.user.id:
                     failed.append((f"{member.display_name} ({member.id})", "Không thể kick Bot"))
                     continue
                
                # Nếu bạn dùng is_admin(discord.Object(id=member.id)) nó sẽ báo lỗi vì is_admin cần Interaction.
                # Tốt nhất: Chỉ kick nếu member không phải là Bot và không có quyền Admin
                if member.guild_permissions.administrator:
                    failed.append((f"{member.display_name} ({member.id})", "Không thể kick Admin"))
                    continue
                
                try:
                    await member.kick(reason="Thanh lý hàng (mass kick by allowed user)")
                    kicked.append(f"{member.display_name} ({member.id})")
                except Exception as e:
                    failed.append((f"{member.display_name} ({member.id})", str(e)))
            else:
                failed.append((str(uid), "Không tìm thấy trong server"))
        
        # Tạo tin nhắn phản hồi
        msg = ""
        if kicked:
            msg += f"✅ Đã thanh lý **{len(kicked)}** hàng:\n" + "\n".join(kicked[:10])
            if len(kicked) > 10:
                msg += f"\n*... và {len(kicked) - 10} thành viên khác.*"
                
        if failed:
            if msg:
                msg += "\n\n"
            msg += f"❌ Lỗi khi xử lý **{len(failed)}** hàng:\n"
            msg += "\n".join(f"{name} ({reason})" for name, reason in failed[:10])
            if len(failed) > 10:
                msg += f"\n*... và {len(failed) - 10} thành viên khác.*"
        
        if not msg:
            msg = "⚠️ Không có thành viên nào được xử lý."
            
        # Giới hạn tin nhắn Discord
        if len(msg) > 2000:
            msg = msg[:1950] + "\n... (Tin nhắn quá dài, đã cắt bớt)"

        await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MassDeleteKick(bot))