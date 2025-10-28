import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands
import requests
import os
from datetime import datetime
from .id_check import is_bhg_manager, APPS_SCRIPT_URL, SECRET_TOKEN
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .id_check import DB_PATH

Engine = create_engine(DB_PATH)
Base = declarative_base()
Session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

class LogBHG(Base):
    """Mô hình SQLAlchemy cho bảng logs của lệnh /add_bhg."""
    __tablename__ = 'bhg_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    manager_name = Column(String)
    manager_id = Column(String)
    member_name = Column(String)
    member_id = Column(String)
    yellow_coin = Column(Integer)
    red_coin = Column(Integer)
    hp = Column(Integer)

Base.metadata.create_all(Engine)

class MemberManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_bhg", description="Tăng chỉ số cho thành viên (BHG Managers Only)")
    @app_commands.describe(
        member="Thành viên cần cập nhật",
        yellow_coin="Số Yellow Coin cần cộng thêm",
        red_coin="Số Red Coin cần cộng thêm",
        hp="Số HP cần cộng thêm"
    )
    # THÊM DECORATOR CHECK
    @app_commands.check(is_bhg_manager) 
    # BỎ @app_commands.default_permissions(manage_guild=True) để chỉ dùng ID cứng
    async def add_bhg(self, interaction: Interaction, member: discord.Member, yellow_coin: int = 0, red_coin: int = 0, hp: int = 0):
     
        # SỬA TRIỆT ĐỂ: Chỉ kiểm tra quyền bằng is_bhg_manager (ID thủ công)
        if not is_bhg_manager(interaction): 
            await interaction.response.send_message("❌ Lệnh này chỉ dành cho những người quản lý BHG có ID được cấp quyền thủ công.", ephemeral=True)
            return

        # Nếu người dùng có quyền, defer để báo cho Discord rằng bot đang xử lý
        await interaction.response.defer(ephemeral=True)
        
        if member.bot:
            await interaction.followup.send("❌ Không thể cập nhật chỉ số cho Bot.", ephemeral=True)
            return

        # --- Bắt đầu phần code ghi logs vào tệp XLSX ---
        session = Session() # Mở một phiên làm việc
        try:
            # Tạo đối tượng logs mới
            new_log = LogBHG(
                manager_name=str(interaction.user),
                manager_id=str(interaction.user.id),
                member_name=str(member),
                member_id=str(member.id),
                yellow_coin=yellow_coin,
                red_coin=red_coin,
                hp=hp
            )
            session.add(new_log)
            session.commit() # Ghi dữ liệu vào tệp bot_data.db

        except Exception as db_error:
            session.rollback() # Hoàn tác nếu có lỗi
            print(f"Lỗi khi ghi logs vào SQLite: {db_error}")
            await interaction.followup.send(f"⚠️ Cảnh báo: Lỗi khi lưu logs vào DB: `{db_error}`", ephemeral=True)
        finally:
            session.close()
        # --- Kết thúc phần code ghi logs ---

        params = {
            'userID': str(member.id),
            'coin': yellow_coin,
            'red': red_coin,
            'hp': hp,
            'token': SECRET_TOKEN
        }

        try:
            response = requests.get(APPS_SCRIPT_URL, params=params)
            response.raise_for_status()
            result_text = response.text

            await interaction.followup.send(
                f"✅ Lệnh đã được thực thi:\n```{result_text}```"
            )
        except requests.exceptions.RequestException as e:
            await interaction.followup.send(
                f"❌ Đã xảy ra lỗi khi kết nối với máy chủ: ```{e}```"
            )
            
async def setup(bot):
    await bot.add_cog(MemberManagement(bot))